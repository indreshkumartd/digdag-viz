"""Graph rendering for Digdag workflows using Graphviz."""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from graphviz import Digraph
import json

from .parser import find_workflow_name, schedule_info, is_task_key, task_operator
from .exceptions import GraphRenderError
from .logger import get_logger
from .sql_pages import read_and_generate_sql_page

logger = get_logger(__name__)


# Node styling configuration
NODE_SHAPES = {
    "default": "box",
    "group": "box",  # was folder
    "if>": "diamond",
    "call>": "box",  # was component
    "require>": "box", # was oval
    "loop>": "box", # was circle
    "http>": "box",
    "mail>": "box",
    "_do": "note",
    "_error": "Mcircle",
    "root": "box",
}

# Border colors (from didaggraph_v2)
NODE_COLORS = {
    "default": "#4A4A4A",   # Gray
    "group": "#9013FE",     # Purple
    "root": "#8B572A",      # Brown
    "if>": "#BD10E0",       # Magenta
    "call>": "#9013FE",     # Purple
    "require>": "#9013FE",  # Purple
    "loop>": "#50E3C2",     # Teal
    "for_each>": "#50E3C2", # Teal
    "sh>": "#7ED321",       # Green
    "td>": "#4A90E2",       # Blue
    "echo>": "#9B9B9B",     # Light Gray
    "py>": "#F5A623",       # Orange
    "rb>": "#D0021B",       # Red
    "http_call>": "#417505",# Dark Green
    "http>": "#417505",     # Dark Green
    "mail>": "#D0021B",     # Crimson
    "_export": "#F8E71C",   # Yellow
    "_parallel": "#9013FE", # Purple
    "_do": "#7ED321",       # Green
    "_error": "#D0021B",    # Red
}

OPERATOR_ICONS = {
    "td>": "📊",
    "sh>": "💻",
    "py>": "🐍",
    "echo>": "📢",
    "call>": "📞",
    "require>": "🔗",
    "loop>": "🔄",
    "for_each>": "🔄",
    "if>": "❓",
    "mail>": "📧",
    "http>": "🌐",
    "_error": "⚠️",
    "root": "📦",
}

NODE_PENWIDTHS = {
    "default": "1.0",
    "group": "1.0",
    "call>": "3.0",
    "require>": "3.0",
    "td>": "1.5",
    "echo>": "1.9",
    "_export": "2.0",
}

SQL_FILE_EXTENSIONS = (".sql", ".sql.j2")


def _looks_like_file_path(value: str) -> bool:
    """Heuristic check for file-like query strings."""
    if not value:
        return False
    if any(ch.isspace() for ch in value):
        return False
    lower = value.lower()
    if lower.endswith(SQL_FILE_EXTENSIONS):
        return True
    return "/" in value or "\\" in value


def _resolve_sql_path(
    query_str: str,
    workflow_dir: Path,
    project_root: Optional[Path]
) -> Tuple[Optional[Path], bool]:
    """Resolve SQL path from workflow and project roots."""
    raw_path = Path(query_str)
    if raw_path.is_absolute():
        return raw_path, True

    roots = [workflow_dir]
    if project_root and project_root not in roots:
        roots.append(project_root)

    for root in roots:
        candidate = root / query_str
        if candidate.exists():
            return candidate, True

    if _looks_like_file_path(query_str):
        return roots[0] / query_str, True

    return None, False


def style_for(op: Optional[str], custom_colors: Optional[Dict[str, str]] = None) -> Tuple[str, str, str]:
    """Get shape, color, and penwidth for an operator.
    
    Args:
        op: Operator name (e.g., 'td>', 'sh>')
        custom_colors: Optional custom color mappings
    
    Returns:
        Tuple of (shape, color, penwidth)
    """
    colors = {**NODE_COLORS, **(custom_colors or {})}
    
    if not op:
        return (NODE_SHAPES["default"], colors["default"], NODE_PENWIDTHS["default"])
    
    shape = NODE_SHAPES.get(op, NODE_SHAPES["default"])
    color = colors.get(op, colors["default"])
    penwidth = NODE_PENWIDTHS.get(op, NODE_PENWIDTHS["default"])
    
    return (shape, color, penwidth)


def add_node(
    g: Digraph,
    node_id: str,
    label: str,
    op: Optional[str],
    custom_colors: Optional[Dict[str, str]] = None
):
    """Add a node to the graph with appropriate styling.
    
    Args:
        g: Graphviz Digraph instance
        node_id: Unique node identifier
        label: Node label text
        op: Operator type
        custom_colors: Optional custom color mappings
    """
    shape, color, penwidth = style_for(op, custom_colors)
    # Style: rounded (not filled), colored border
    g.node(node_id, label=label, shape=shape, style="rounded", color=color, penwidth=penwidth, fontname="Helvetica")


def normalized_id(prefix_stack: List[str], name: str) -> str:
    """Create unique node ID from prefix stack and name.
    
    Args:
        prefix_stack: List of parent task names
        name: Current task name
    
    Returns:
        Unique node identifier
    """
    parts = [*prefix_stack, name]
    return "/".join(parts)


def render_tasks(
    g: Digraph,
    doc: Dict[str, Any],
    parent_stack: List[str],
    tasks: List[Tuple[str, Dict[str, Any]]],
    custom_colors: Optional[Dict[str, str]] = None,
    max_depth: Optional[int] = None,
    current_depth: int = 0,
    parent_is_parallel: bool = False
) -> List[str]:
    """Recursively render tasks and their relationships.
    
    Args:
        parent_is_parallel: If True, tasks are parallel siblings and should not be connected sequentially
    
    Returns:
        List of node IDs representing the "last" nodes (completion points) of this task group
    """
    # Check depth limit
    if max_depth is not None and current_depth >= max_depth:
        logger.debug(f"Reached max depth {max_depth}, skipping deeper tasks")
        return []
    
    # Track completion points from previous sibling (sequential) or all siblings (parallel)
    prev_last_nodes: List[str] = []
    all_parallel_last_nodes: List[str] = []  # Accumulate when parent_is_parallel
    
    for (tkey, tbody) in tasks:
        tname = tkey[1:]  # Remove + prefix
        node_id = normalized_id(parent_stack, tkey)
        op_pair = task_operator(tbody if isinstance(tbody, dict) else {})
        op = op_pair[0] if op_pair else None

        # Build a readable label
        op_suffix = f"\\n[{op}]" if op else ""
        label = f"{tname}{op_suffix}"

        add_node(g, node_id, label, op, custom_colors)

        # Connect from previous sibling's completion points (ONLY if not parallel)
        if prev_last_nodes and not parent_is_parallel:
            for last_node in prev_last_nodes:
                g.edge(last_node, node_id)
        
        # If parent is parallel, connect each child to the parent instead
        if parent_is_parallel and len(parent_stack) > 0:
            parent_id = normalized_id(parent_stack[:-1], parent_stack[-1])
            g.edge(parent_id, node_id)

        # Operator-specific edges/labels
        if isinstance(tbody, dict):
            # require> and call> are handled via URLs in interactive mode
            # No need to create separate visual nodes for them

            # loop> / for_each> / for_range> annotate
            for loopish in ("loop>", "for_each>", "for_range>"):
                if loopish in tbody:
                    g.edge(node_id, node_id, label=loopish, style="dotted", dir="none")

            # retry / _error handlers visually as side-notes
            if "retry" in tbody:
                g.edge(node_id, node_id, label=f"retry={tbody['retry']}", style="dotted", dir="none")
            
            if "_error" in tbody:
                add_node(g, f"{node_id}__error", f"{tname} error handler", "_error", custom_colors)
                g.edge(node_id, f"{node_id}__error", style="dashed", label="_error")

            # Check if THIS task has _parallel for its children
            is_parallel = tbody.get("_parallel", False)

            # Recurse into children (+ subtasks)
            child_tasks = [(k, v) for k, v in tbody.items() if is_task_key(k)]
            if child_tasks:
                child_last_nodes = render_tasks(
                    g, doc, parent_stack + [tkey], child_tasks,
                    custom_colors, max_depth, current_depth + 1,
                    parent_is_parallel=is_parallel
                )
                # This task completes when all its children complete
                current_task_last_nodes = child_last_nodes
            else:
                # Leaf task - it completes itself
                current_task_last_nodes = [node_id]
        else:
            # Non-dict task body (edge case)
            current_task_last_nodes = [node_id]
        
        # Update tracking based on whether we're in parallel mode
        if parent_is_parallel:
            # Accumulate ALL children's last nodes
            all_parallel_last_nodes.extend(current_task_last_nodes)
        else:
            # Sequential: next sibling connects from this task's completion
            prev_last_nodes = current_task_last_nodes
    
    # Return appropriate last nodes
    if parent_is_parallel:
        return all_parallel_last_nodes
    else:
        return prev_last_nodes


def build_graph(
    doc: Dict[str, Any],
    file_path: Path,
    outdir: Path,
    graph_format: str = "svg",
    direction: str = "LR",
    custom_colors: Optional[Dict[str, str]] = None,
    max_depth: Optional[int] = None
) -> str:
    """Build and render workflow graph."""
    try:
        wf_name = find_workflow_name(doc, file_path)
        cron, tz = schedule_info(doc)
        
        # Build title with schedule info
        title = wf_name
        if cron:
            title += f"  (schedule: {cron}{' '+tz if tz else ''})"

        logger.debug(f"Building graph for workflow: {wf_name}")
        
        # Create graph with RED edges by default
        g = Digraph(comment=f"{wf_name}", format=graph_format, graph_attr={'rankdir': direction, 'labelloc': 't', 'fontsize': '20', 'label': title, 'fontname': 'Helvetica'}, node_attr={'fontname': 'Helvetica', 'fontsize': '11'}, edge_attr={'color': 'red'})
        g.attr("edge", color="red")  # Default edge color

        # Root "workflow" node
        root_id = f"{wf_name}__root"
        add_node(g, root_id, wf_name, "root", custom_colors)

        # Collect top-level tasks in order
        top_tasks = [(k, v) for k, v in doc.items() if is_task_key(k)]
        render_tasks(g, doc, [wf_name], top_tasks, custom_colors, max_depth)

        # Connect root to first task
        if top_tasks:
            first_id = normalized_id([wf_name], top_tasks[0][0])
            g.edge(root_id, first_id)

        # Write file
        outdir.mkdir(parents=True, exist_ok=True)
        output_path = outdir / f"{file_path.stem}"
        
        logger.debug(f"Rendering graph to {output_path}.{graph_format}")
        g.render(output_path, cleanup=True)
        
        return f"{file_path.stem}.{graph_format}"
        
    except Exception as e:
        raise GraphRenderError(f"Failed to render graph for {file_path}: {e}")


def build_interactive_graph(
    doc: Dict[str, Any],
    file_path: Path,
    outdir: Path,
    direction: str = "LR",
    custom_colors: Optional[Dict[str, str]] = None,
    max_depth: Optional[int] = None,
    project_root: Optional[Path] = None
) -> Tuple[str, str]:
    """Build interactive workflow graph with inline SVG."""
    try:
        wf_name = find_workflow_name(doc, file_path)
        cron, tz = schedule_info(doc)
        
        # Build title with schedule info
        title = wf_name
        if cron:
            title += f"  (schedule: {cron}{' '+tz if tz else ''})"

        logger.debug(f"Building interactive graph for workflow: {wf_name}")
        
        # Create TWO graphs: one for SVG, one for imagemap (legacy logic kept but we only use SVG now)
        map_name = file_path.stem
        
        # SVG graph with RED edges
        g_svg = Digraph(name=map_name, format="svg", graph_attr={'rankdir': direction, 'labelloc': 't', 'fontsize': '20', 'label': title, 'fontname': 'Helvetica'}, node_attr={'fontname': 'Helvetica', 'fontsize': '11'}, edge_attr={'color': 'red'})
        g_svg.attr(target="_top")  # Keep links in same tab
        
        # Imagemap graph (legacy, kept for structure parity if needed)
        g_map = Digraph(name=map_name, format="cmapx", graph_attr={'rankdir': direction, 'labelloc': 't', 'fontsize': '20', 'label': title, 'fontname': 'Helvetica'}, node_attr={'fontname': 'Helvetica', 'fontsize': '11'}, edge_attr={'color': 'red'})
        g_map.attr(target="_top")

        # Root "workflow" node
        root_id = f"{wf_name}__root"
        # Root node styling
        shape, color, penwidth = style_for("root", custom_colors)
        
        # Add root to both
        g_svg.node(root_id, wf_name, shape=shape, style="rounded", color=color, penwidth=penwidth, URL="../../index.html", tooltip="Back to index")
        g_map.node(root_id, wf_name, shape=shape, style="rounded", color=color, penwidth=penwidth, URL="../../index.html", tooltip="Back to index")

        # Collect top-level tasks
        top_tasks = [(k, v) for k, v in doc.items() if is_task_key(k)]
        
        # Collect task definitions for sidebar
        task_defs = {}
        
        render_tasks_with_links(
            g_svg, g_map, doc, [wf_name], top_tasks,
            custom_colors, max_depth, 0,
            file_path, outdir, project_root,
            task_defs=task_defs,
            initial_prev_nodes=[root_id]
        )

        # Handle root-level special directive blocks (_error, _do, _else_do)
        # These need special handling because they don't start with +
        special_directives = []
        
        # Check for _error block
        if "_error" in doc and isinstance(doc["_error"], dict):
            special_directives.append(("_error", doc["_error"], "#D0021B", "[ERROR]"))
        
        # Check for _do block (inside if>, for_each>, etc.)
        if "_do" in doc and isinstance(doc["_do"], dict):
            special_directives.append(("_do", doc["_do"], "#7ED321", "[DO]"))
        
        # Check for _else_do block (inside if>)
        if "_else_do" in doc and isinstance(doc["_else_do"], dict):
            special_directives.append(("_else_do", doc["_else_do"], "#F5A623", "[ELSE]"))
        
        # Render each special directive block
        for directive_name, directive_body, color, icon in special_directives:
            directive_id = normalized_id([wf_name], directive_name)
            directive_label = f"{wf_name}\\n{directive_name}"
            directive_shape = NODE_SHAPES.get(directive_name, "box")
            
            # Create the directive node
            g_svg.node(directive_id, label=f"{icon} {directive_label}",
                      shape=directive_shape, color=color, style="filled",
                      fillcolor=f"{color}20", fontname="Inter")  # 20 = 12% opacity in hex
            g_map.node(directive_id, label=f"{icon} {directive_label}",
                      shape=directive_shape, color=color, style="filled",
                      fillcolor=f"{color}20", fontname="Inter")
            
            # Connect root to directive with dashed line
            g_svg.edge(root_id, directive_id, style="dashed", label=directive_name, color=color)
            g_map.edge(root_id, directive_id, style="dashed", label=directive_name, color=color)
            
            # Recursively render directive's child tasks
            directive_child_tasks = [(k, v) for k, v in directive_body.items() if is_task_key(k)]
            if directive_child_tasks:
                render_tasks_with_links(
                    g_svg, g_map, doc, [wf_name, directive_name],
                    directive_child_tasks, custom_colors, max_depth, 1,
                    file_path, outdir, project_root,
                    task_defs=task_defs,
                    initial_prev_nodes=[directive_id]
                )


        # Write SVG

        # Write SVG
        # Write SVG
        outdir.mkdir(parents=True, exist_ok=True)
        svg_path = outdir / f"{file_path.stem}"
        g_svg.render(svg_path, cleanup=True)
        
        svg_filename = f"{file_path.stem}.svg"
        
        # Read the generated SVG content
        svg_file = outdir / svg_filename
        svg_content = svg_file.read_text(encoding='utf-8')
        
        # Clean up SVG content
        svg_start = svg_content.find('<svg')
        if svg_start >= 0:
            svg_content = svg_content[svg_start:]
            
        return (svg_filename, svg_content, task_defs)
        
    except Exception as e:
        raise GraphRenderError(f"Failed to render interactive graph for {file_path}: {e}")

        
    except Exception as e:
        raise GraphRenderError(f"Failed to render interactive graph for {file_path}: {e}")


def render_tasks_with_links(
    g_svg: Digraph,
    g_map: Digraph,
    doc: Dict[str, Any],
    parent_stack: List[str],
    tasks: List[Tuple[str, Dict[str, Any]]],
    custom_colors: Optional[Dict[str, str]],
    max_depth: Optional[int],
    current_depth: int,
    file_path: Path,
    outdir: Path,
    project_root: Optional[Path],
    parent_is_parallel: bool = False,
    task_defs: Optional[Dict[str, Any]] = None,
    initial_prev_nodes: Optional[List[str]] = None
) -> List[str]:
    """Render tasks recursively with links for interactive map."""
    if max_depth is not None and current_depth >= max_depth:
        logger.debug(f"Reached max depth {max_depth}, skipping deeper tasks")
        return []
    
    # Track completion points from previous sibling (sequential) or all siblings (parallel)
    prev_last_nodes: List[str] = list(initial_prev_nodes) if initial_prev_nodes else []
    all_parallel_last_nodes: List[str] = []  # Accumulate when parent_is_parallel
    
    for (tkey, tbody) in tasks:
        tname = tkey.replace("+", "")
        node_id = normalized_id(parent_stack, tname)
        
        # Store definition if tracking
        if task_defs is not None and isinstance(tbody, dict):
            task_defs[node_id] = tbody
        
        # Determine operator
        op_pair = task_operator(tbody if isinstance(tbody, dict) else {})
        op = op_pair[0] if op_pair else None

        # Add icon to label
        icon = OPERATOR_ICONS.get(op, "") if op else ""
        if op == "root": icon = OPERATOR_ICONS.get("root", "")
        
        label_text = f"{icon} {tname}" if icon else tname
        label = f"{label_text}\\n[{op}]" if op else label_text
        
        shape, color, penwidth = style_for(op, custom_colors)
        
        # Default URL and tooltip
        url = "#"
        tooltip = f"Task: {tname}"
        
        # Handle special operators
        if op == "call>":
            target = tbody.get("call>")
            if target:
                url = f"{target}.html"
                tooltip = f"Call workflow: {target}"
        elif op == "require>":
            target = tbody.get("require>")
            if target:
                url = f"{target}.html"
                tooltip = f"Require workflow: {target}"
        elif op == "td>":
            # Link to SQL query page
            query_val = tbody.get("td>")
            if query_val:
                # Handle both string and dict formats
                # String: td>: queries/my_query.sql
                # Dict: td>: {query: queries/my_query.sql, database: mydb}
                query_str = None
                inline_sql = None
                if isinstance(query_val, str):
                    query_str = query_val
                elif isinstance(query_val, dict):
                    query_str = query_val.get("query") or query_val.get("sql")
                    inline_sql = query_val.get("data")

                inline_sql_text = inline_sql if isinstance(inline_sql, str) else None

                if query_str and isinstance(query_str, str):
                    sql_path, is_file = _resolve_sql_path(
                        query_str,
                        file_path.parent,
                        project_root
                    )
                    project_name = project_root.name if project_root else file_path.parent.name
                    if is_file and sql_path:
                        rel_path = read_and_generate_sql_page(
                            sql_path,
                            query_str,
                            project_name,
                            outdir
                        )
                        url = rel_path
                        tooltip = f"View SQL: {query_str}"
                        inline_sql_text = None
                    elif inline_sql_text is None:
                        inline_sql_text = query_str

                if inline_sql_text:
                    # Inline query
                    # Create a safe filename for the inline query
                    import hashlib
                    query_hash = hashlib.md5(inline_sql_text.encode('utf-8')).hexdigest()[:8]
                    inline_name = f"inline_{tname}_{query_hash}.sql"
                    
                    # Write inline SQL to temp file
                    queries_dir = outdir / "queries"
                    queries_dir.mkdir(parents=True, exist_ok=True)
                    inline_sql_path = queries_dir / inline_name
                    inline_sql_path.write_text(inline_sql_text, encoding='utf-8')
                    
                    project_name = project_root.name if project_root else file_path.parent.name
                    rel_path = read_and_generate_sql_page(
                        inline_sql_path,
                        f"inline: {tname}",
                        project_name,
                        outdir
                    )
                    url = rel_path
                    tooltip = "View Inline SQL"

        # Check if this is a parallel group container
        is_parallel_group = False
        if isinstance(tbody, dict):
            is_parallel_group = tbody.get("_parallel", False)

        # Skip node creation entirely for parallel group containers
        # The children will be rendered in the cluster and connect from prev_last_nodes
        if not is_parallel_group:
            # Add URL to task_defs for sidebar
            if task_defs is not None and node_id in task_defs:
                task_defs[node_id]['_url'] = url

            # Add node to SVG graph
            g_svg.node(node_id, label, shape=shape, style="rounded,filled", color=color, penwidth=penwidth, fillcolor="white", URL=url, tooltip=tooltip, id=node_id)
            g_map.node(node_id, label, shape=shape, style="rounded,filled", color=color, penwidth=penwidth, fillcolor="white", URL=url, tooltip=tooltip)

            # Connect from previous nodes
            # Special case: if we have initial_prev_nodes, these are entry points from upstream
            # and should connect even if we're in a parallel group
            if prev_last_nodes:
                if not parent_is_parallel or (parent_is_parallel and initial_prev_nodes):
                    for last_node in prev_last_nodes:
                        g_svg.edge(last_node, node_id)
                        g_map.edge(last_node, node_id)
        
        # Current task's last nodes (default to itself)
        current_task_last_nodes: List[str] = []

        if isinstance(tbody, dict):
            # Operator-specific edges
            for loopish in ("loop>", "for_each>", "for_range>"):
                if loopish in tbody:
                    g_svg.edge(node_id, node_id, label=loopish, style="dotted", dir="none")
                    g_map.edge(node_id, node_id, label=loopish, style="dotted", dir="none")

            if "retry" in tbody:
                # Add a self-loop or similar to indicate retry
                # For now, just a dotted edge to self
                g_svg.edge(node_id, node_id, label="retry", style="dotted")
                g_map.edge(node_id, node_id, label="retry", style="dotted")
            
            # Handle special directive blocks (_error, _do, _else_do) AFTER regular tasks
            # These need special handling because they don't start with +
            special_directives = []
            
            # Check for _error block
            if "_error" in tbody and isinstance(tbody["_error"], dict):
                special_directives.append(("_error", tbody["_error"], "#D0021B", "[ERROR]"))
            
            # Check for _do block (inside if>, for_each>, etc.)
            if "_do" in tbody and isinstance(tbody["_do"], dict):
                special_directives.append(("_do", tbody["_do"], "#7ED321", "[DO]"))
            
            # Check for _else_do block (inside if>)
            if "_else_do" in tbody and isinstance(tbody["_else_do"], dict):
                special_directives.append(("_else_do", tbody["_else_do"], "#F5A623", "[ELSE]"))
            
            # Render each special directive block
            for directive_name, directive_body, color, icon in special_directives:
                directive_id = normalized_id(parent_stack + [tkey], directive_name)
                directive_label = f"{tname}\\n{directive_name}"
                directive_shape = NODE_SHAPES.get(directive_name, "box")
                
                # Create the directive node
                g_svg.node(directive_id, label=f"{icon} {directive_label}",
                          shape=directive_shape, color=color, style="filled",
                          fillcolor=f"{color}20", fontname="Inter")  # 20 = 12% opacity in hex
                g_map.node(directive_id, label=f"{icon} {directive_label}",
                          shape=directive_shape, color=color, style="filled",
                          fillcolor=f"{color}20", fontname="Inter")
                
                # Connect parent task to directive with dashed line
                g_svg.edge(node_id, directive_id, style="dashed", label=directive_name, color=color)
                g_map.edge(node_id, directive_id, style="dashed", label=directive_name, color=color)
                
                # Recursively render directive's child tasks
                directive_child_tasks = [(k, v) for k, v in directive_body.items() if is_task_key(k)]
                if directive_child_tasks:
                    render_tasks_with_links(
                        g_svg, g_map, doc, parent_stack + [tkey, directive_name],
                        directive_child_tasks, custom_colors, max_depth, current_depth + 1,
                        file_path, outdir, project_root,
                        task_defs=task_defs,
                        initial_prev_nodes=[directive_id]
                    )

            is_parallel = tbody.get("_parallel", False)

            # Recurse
            child_tasks = [(k, v) for k, v in tbody.items() if is_task_key(k)]
            if child_tasks:
                # Determine what the children should connect from
                if is_parallel_group:
                    # Parallel group: children connect from OUR previous nodes
                    nodes_to_connect_from = prev_last_nodes
                else:
                    # Sequential group: children connect from US
                    nodes_to_connect_from = [node_id]

                if is_parallel:
                    # Create a cluster for parallel tasks
                    cluster_name = f"cluster_{node_id}"
                    
                    # IMPORTANT: Create entry edges BEFORE entering cluster context
                    # This prevents external nodes (like root) from being pulled into the cluster
                    if is_parallel_group and nodes_to_connect_from:
                        # Connect from upstream nodes to each parallel child
                        for child_key, child_body in child_tasks:
                            child_node_id = normalized_id(parent_stack + [tkey], child_key.replace("+", ""))
                            for upstream_node in nodes_to_connect_from:
                                g_svg.edge(upstream_node, child_node_id)
                                g_map.edge(upstream_node, child_node_id)
                    
                    with g_svg.subgraph(name=cluster_name) as c:
                        c.attr(style='dashed', color='#aaaaaa', label='parallel', fontcolor='#aaaaaa', fontsize='10')
                        
                        # Pass None for initial_prev_nodes since we already created the entry edges
                        child_last_nodes = render_tasks_with_links(
                            c, g_map, doc, parent_stack + [tkey], child_tasks,
                            custom_colors, max_depth, current_depth + 1,
                            file_path, outdir, project_root,
                            parent_is_parallel=is_parallel,
                            task_defs=task_defs,
                            initial_prev_nodes=None if is_parallel_group else nodes_to_connect_from
                        )
                else:
                    child_last_nodes = render_tasks_with_links(
                        g_svg, g_map, doc, parent_stack + [tkey], child_tasks,
                        custom_colors, max_depth, current_depth + 1,
                        file_path, outdir, project_root,
                        parent_is_parallel=is_parallel,
                        task_defs=task_defs,
                        initial_prev_nodes=nodes_to_connect_from
                    )
                # This task completes when all its children complete
                current_task_last_nodes = child_last_nodes
            else:
                # Leaf task - it completes itself
                current_task_last_nodes = [node_id]
        else:
            # Non-dict task body (edge case)
            current_task_last_nodes = [node_id]
        
        # Update tracking based on whether we're in parallel mode
        if parent_is_parallel:
            # Accumulate ALL children's last nodes
            all_parallel_last_nodes.extend(current_task_last_nodes)
        else:
            # Sequential: next sibling connects from this task's completion
            prev_last_nodes = current_task_last_nodes
    
    # Return appropriate last nodes
    if parent_is_parallel:
        return all_parallel_last_nodes
    else:
        return prev_last_nodes
