"""
Data lineage extraction for Digdag workflows.

This module extracts table-level dependencies from SQL queries,
handling Jinja templates and building cross-workflow lineage graphs.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp
from jinja2 import Template, Environment, UndefinedError

logger = logging.getLogger(__name__)


@dataclass
class TableReference:
    """Represents a table reference in SQL"""
    name: str
    database: Optional[str] = None
    schema: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """Get fully qualified table name"""
        parts = []
        if self.database:
            parts.append(self.database)
        if self.schema:
            parts.append(self.schema)
        parts.append(self.name)
        return '.'.join(parts)
    
    def __hash__(self):
        return hash(self.full_name)
    
    def __eq__(self, other):
        return self.full_name == other.full_name


@dataclass
class SQLLineage:
    """Lineage information extracted from a SQL query"""
    sources: List[TableReference] = field(default_factory=list)
    targets: List[TableReference] = field(default_factory=list)
    resolved: bool = True
    template_variables: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class TaskLineage:
    """Lineage for a single workflow task"""
    task_name: str
    workflow_name: str
    sql_file: Optional[str] = None
    lineage: Optional[SQLLineage] = None


class SQLParser:
    """Parse SQL and extract table references"""
    
    def __init__(self, dialect: str = "presto"):
        self.dialect = dialect
    
    def extract_tables(self, sql: str) -> SQLLineage:
        """
        Extract source and target tables from SQL.
        
        Args:
            sql: SQL query string
            
        Returns:
            SQLLineage object with sources and targets
        """
        try:
            # Parse SQL - use parse() not parse_one() to handle multiple statements
            # (e.g., DROP TABLE IF EXISTS; CREATE TABLE AS ...)
            statements = sqlglot.parse(sql, dialect=self.dialect)
            
            if not statements:
                return SQLLineage(
                    sources=[],
                    targets=[],
                    resolved=False,
                    error="No SQL statements found"
                )
            
            sources = set()
            targets = set()
            cte_names = set()  # Track CTE (WITH clause) names to exclude
            
            # Process all statements
            for parsed in statements:
                # Collect CTE names (WITH clause aliases)
                for cte in parsed.find_all(exp.CTE):
                    if cte.alias:
                        cte_names.add(cte.alias.lower())
                
                # Find all table references in this statement
                for table in parsed.find_all(exp.Table):
                    table_ref = self._extract_table_reference(table)
                    if table_ref and self._is_real_table(table_ref, cte_names):
                        sources.add(table_ref)
                
                # Find INSERT INTO / CREATE TABLE targets
                if isinstance(parsed, exp.Insert):
                    target_ref = self._extract_table_reference(parsed.this)
                    if target_ref:
                        targets.add(target_ref)
                        # Remove target from sources
                        sources.discard(target_ref)
                
                elif isinstance(parsed, exp.Create):
                    # Extract target table from CREATE TABLE
                    target_ref = self._extract_table_reference(parsed.this)
                    if target_ref:
                        targets.add(target_ref)
                        # Remove target from sources (it shouldn't be in sources anyway)
                        sources.discard(target_ref)
                    
                    # For CREATE TABLE AS, the sources are in the expression
                    # We need to find tables in the AS clause
                    if parsed.expression:
                        # Collect CTEs from the CREATE TABLE AS expression
                        for cte in parsed.expression.find_all(exp.CTE):
                            if cte.alias:
                                cte_names.add(cte.alias.lower())
                        
                        for table in parsed.expression.find_all(exp.Table):
                            table_ref = self._extract_table_reference(table)
                            if table_ref and table_ref != target_ref and self._is_real_table(table_ref, cte_names):
                                sources.add(table_ref)
            
            return SQLLineage(
                sources=list(sources),
                targets=list(targets),
                resolved=True
            )
        
        except Exception as e:
            logger.debug(f"Failed to parse SQL: {e}")
            return SQLLineage(
                sources=[],
                targets=[],
                resolved=False,
                error=str(e)
            )
    
    def _is_real_table(self, table_ref: TableReference, cte_names: set) -> bool:
        """
        Check if a table reference is a real table (not a CTE, system table, or alias).
        
        Args:
            table_ref: Table reference to check
            cte_names: Set of CTE names to exclude
            
        Returns:
            True if this is a real table, False otherwise
        """
        table_name = table_ref.name.lower()
        full_name = table_ref.full_name.lower()
        
        # Exclude CTE names
        if table_name in cte_names or full_name in cte_names:
            return False
        
        # Exclude system tables
        if table_ref.database and table_ref.database.lower() in ['information_schema', 'sys', 'pg_catalog']:
            return False
        
        # Exclude very short names (likely aliases like T1, T2, CJ, etc.)
        # Real table names are usually longer than 3 characters
        if len(table_name) <= 2:
            return False
        
        # Exclude common single-letter or short CTE patterns
        if table_name in ['t', 't1', 't2', 't3', 't4', 't5', 'cj', 'a', 'b', 'c', 'd']:
            return False
        
        return True
    
    def _extract_table_reference(self, table_node) -> Optional[TableReference]:
        """Extract TableReference from sqlglot table node"""
        try:
            if not table_node:
                return None
            
            # Handle different node types
            if isinstance(table_node, exp.Table):
                name = table_node.name
                db = table_node.db if hasattr(table_node, 'db') else None
                
                return TableReference(
                    name=name,
                    database=db
                )
            
            # Handle identifier nodes
            elif hasattr(table_node, 'name'):
                return TableReference(name=table_node.name)
            
            return None
        
        except Exception as e:
            logger.debug(f"Failed to extract table reference: {e}")
            return None


class TemplateResolver:
    """Resolve Jinja templates in SQL queries"""
    
    def __init__(self):
        self.env = Environment()
    
    def resolve(self, sql_template: str, context: Dict) -> Tuple[str, bool]:
        """
        Resolve Jinja template with given context.
        
        Args:
            sql_template: SQL with Jinja templates
            context: Variable context from workflow
            
        Returns:
            Tuple of (resolved_sql, success)
        """
        try:
            template = self.env.from_string(sql_template)
            resolved = template.render(**context)
            return resolved, True
        
        except UndefinedError as e:
            logger.debug(f"Template resolution failed - undefined variable: {e}")
            return sql_template, False
        
        except Exception as e:
            logger.debug(f"Template resolution failed: {e}")
            return sql_template, False
    
    def extract_variables(self, sql_template: str) -> List[str]:
        """
        Extract Jinja variable names from template.
        
        Args:
            sql_template: SQL with Jinja templates
            
        Returns:
            List of variable names
        """
        # Pattern: {{ variable }} or ${variable}
        jinja_pattern = r'\{\{\s*(\w+)\s*\}\}'
        digdag_pattern = r'\$\{\s*(\w+)\s*\}'
        
        jinja_vars = re.findall(jinja_pattern, sql_template)
        digdag_vars = re.findall(digdag_pattern, sql_template)
        
        return list(set(jinja_vars + digdag_vars))


class WorkflowLineageExtractor:
    """Extract lineage from workflow definitions"""
    
    def __init__(self):
        self.sql_parser = SQLParser()
        self.template_resolver = TemplateResolver()
    
    def extract_from_workflow(
        self,
        workflow_doc,
        base_path: Path,
        search_roots: Optional[List[Path]] = None
    ) -> List[TaskLineage]:
        """
        Extract lineage from a workflow document.
        
        Args:
            workflow_doc: WorkflowDocument object
            base_path: Base path for resolving SQL file paths
            
        Returns:
            List of TaskLineage objects
        """
        lineages = []
        
        # Build variable context from workflow
        context = self._build_context(workflow_doc)
        
        # Recursively find all td> operators in the workflow
        td_tasks = self._find_td_operators(workflow_doc.content, workflow_doc.name)
        
        # Extract lineage from each SQL file
        for task_path, sql_value, task_def, is_inline in td_tasks:
            lineage = self._extract_from_sql(
                sql_value,
                base_path,
                context,
                task_def,  # Pass task definition to check for create_table
                search_roots=search_roots,
                is_inline=is_inline
            )
            
            lineages.append(TaskLineage(
                task_name=task_path,
                workflow_name=workflow_doc.name,
                sql_file=None if is_inline else sql_value,
                lineage=lineage
            ))
        
        return lineages
    
    def _find_td_operators(self, obj, path="") -> List[Tuple[str, str, Dict, bool]]:
        """
        Recursively find all td> operators in workflow structure.
        
        Args:
            obj: Workflow object (dict, list, or primitive)
            path: Current path in the workflow tree
            
        Returns:
            List of (task_path, sql_value, task_def, is_inline) tuples
        """
        results = []
        
        if isinstance(obj, dict):
            # Check if this dict has a td> key
            if 'td>' in obj:
                sql_value = obj['td>']
                # Handle both string and dict values
                if isinstance(sql_value, str):
                    # Return the entire task definition
                    results.append((path, sql_value, obj, False))
                elif isinstance(sql_value, dict):
                    query_value = sql_value.get('query') or sql_value.get('sql')
                    if isinstance(query_value, str):
                        results.append((path, query_value, obj, False))
                    else:
                        inline_sql = sql_value.get('data')
                        if isinstance(inline_sql, str):
                            results.append((path, inline_sql, obj, True))
                        else:
                            logger.debug(f"Skipping unsupported td> value at {path}")
            
            # Recursively search all values
            for key, value in obj.items():
                # Skip None keys
                if key is None:
                    continue
                
                # Build path for nested tasks
                if key.startswith('+'):
                    # Root task
                    new_path = key
                elif path and not key.startswith('_'):
                    # Nested task
                    new_path = f"{path}.{key}"
                else:
                    # Metadata or config
                    new_path = path
                
                results.extend(self._find_td_operators(value, new_path))
        
        elif isinstance(obj, list):
            # Search in list items
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]" if path else f"[{i}]"
                results.extend(self._find_td_operators(item, new_path))
        
        return results
    
    def _build_context(self, workflow_doc) -> Dict:
        """Build variable context from workflow definition"""
        context = {}
        
        # From _export section
        if hasattr(workflow_doc, 'content') and '_export' in workflow_doc.content:
            export_vars = workflow_doc.content['_export']
            if isinstance(export_vars, dict):
                context.update(export_vars)
        
        # Add common Digdag variables as placeholders
        context.update({
            'session_date': '2024-01-01',
            'session_time': '00:00:00',
            'session_uuid': 'placeholder',
            'session_date_hour': 0,
        })
        
        return context
    
    def _looks_like_file_path(self, value: str) -> bool:
        """Heuristic check for file-like query strings."""
        if not value:
            return False
        if any(ch.isspace() for ch in value):
            return False
        lower = value.lower()
        if lower.endswith(".sql") or lower.endswith(".sql.j2"):
            return True
        return "/" in value or "\\" in value

    def _resolve_sql_path(
        self,
        sql_value: str,
        base_path: Path,
        search_roots: Optional[List[Path]] = None
    ) -> Tuple[Optional[Path], bool]:
        """Resolve SQL path from workflow and project roots."""
        raw_path = Path(sql_value)
        if raw_path.is_absolute():
            return raw_path, True

        roots = [base_path]
        for root in search_roots or []:
            if root and root not in roots:
                roots.append(root)

        for root in roots:
            candidate = root / sql_value
            if candidate.exists():
                return candidate, True

        if self._looks_like_file_path(sql_value):
            return roots[0] / sql_value, True

        return None, False

    def _extract_from_sql_text(self, sql_template: str, context: Dict) -> SQLLineage:
        """Extract lineage from SQL text, resolving templates when possible."""
        has_templates = '{{' in sql_template or '{%' in sql_template

        if has_templates:
            # Try to resolve templates
            resolved_sql, success = self.template_resolver.resolve(
                sql_template,
                context
            )

            if success:
                return self.sql_parser.extract_tables(resolved_sql)

            # Extract template variables
            variables = self.template_resolver.extract_variables(sql_template)
            return SQLLineage(
                resolved=False,
                template_variables=variables
            )

        return self.sql_parser.extract_tables(sql_template)

    def _apply_task_overrides(self, lineage: SQLLineage, task_def: Optional[Dict]) -> SQLLineage:
        """Apply Digdag task parameters like database/create_table/insert_into."""
        if not task_def:
            return lineage

        # Apply task database context to unqualified source tables
        task_db = task_def.get('database')
        if task_db:
            for i, source in enumerate(lineage.sources):
                if not source.database:
                    lineage.sources[i] = TableReference(
                        name=source.name,
                        database=task_db,
                        schema=source.schema
                    )

        # Override target table with Digdag parameters if present
        if lineage.resolved:
            # Check for create_table parameter (creates a new table)
            if 'create_table' in task_def:
                table_name = task_def['create_table']
                # Parse database if specified
                database = task_def.get('database')

                # If table name is already fully qualified, use it as is
                if '.' in table_name:
                    # Update database and table_name from the fully qualified name
                    parts = table_name.split('.')
                    if len(parts) > 1:
                        database = parts[0]
                        table_name = '.'.join(parts[1:])

                # Replace targets with the create_table value
                lineage.targets = [TableReference(
                    name=table_name,
                    database=database
                )]

            # Check for insert_into parameter (inserts into existing table)
            elif 'insert_into' in task_def:
                table_name = task_def['insert_into']
                database = task_def.get('database')

                # If table name is already fully qualified, use it as is
                if '.' in table_name:
                    # Update database and table_name from the fully qualified name
                    parts = table_name.split('.')
                    if len(parts) > 1:
                        database = parts[0]
                        table_name = '.'.join(parts[1:])

                # Replace targets with the insert_into value
                lineage.targets = [TableReference(
                    name=table_name,
                    database=database
                )]

        return lineage

    def _extract_from_sql(
        self,
        sql_value: str,
        base_path: Path,
        context: Dict,
        task_def: Optional[Dict] = None,
        search_roots: Optional[List[Path]] = None,
        is_inline: bool = False
    ) -> SQLLineage:
        """Extract lineage from SQL file or inline SQL."""
        try:
            if not isinstance(sql_value, str) or not sql_value.strip():
                return SQLLineage(
                    resolved=False,
                    error="SQL value is empty"
                )

            if is_inline:
                lineage = self._extract_from_sql_text(sql_value, context)
                return self._apply_task_overrides(lineage, task_def)

            sql_path, is_file = self._resolve_sql_path(sql_value, base_path, search_roots)
            if is_file and sql_path:
                if not sql_path.exists():
                    return SQLLineage(
                        resolved=False,
                        error=f"SQL file not found: {sql_value}"
                    )

                sql_template = sql_path.read_text(encoding="utf-8")
                lineage = self._extract_from_sql_text(sql_template, context)
                return self._apply_task_overrides(lineage, task_def)

            # Treat remaining strings as inline SQL
            lineage = self._extract_from_sql_text(sql_value, context)
            return self._apply_task_overrides(lineage, task_def)
        
        except Exception as e:
            logger.warning(f"Failed to extract lineage from {sql_value}: {e}")
            return SQLLineage(
                resolved=False,
                error=str(e)
            )


from dataclasses import dataclass, field

@dataclass
class LineageGraph:
    """Graph of task dependencies and data lineage"""
    task_lineages: List[TaskLineage] = field(default_factory=list)
    table_to_workflows: Dict[str, Set[str]] = field(default_factory=dict)
    table_to_tasks: Dict[str, Set[Tuple[str, str]]] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    
    def add_task_lineage(self, task_lineage: TaskLineage):
        """Add a task lineage to the graph"""
        self.task_lineages.append(task_lineage)
        
        if not task_lineage.lineage:
            return
        
        # Index by tables
        for source in task_lineage.lineage.sources:
            table_name = source.full_name
            
            if table_name not in self.table_to_workflows:
                self.table_to_workflows[table_name] = set()
            self.table_to_workflows[table_name].add(task_lineage.workflow_name)
            
            if table_name not in self.table_to_tasks:
                self.table_to_tasks[table_name] = set()
            self.table_to_tasks[table_name].add(
                (task_lineage.workflow_name, task_lineage.task_name)
            )
    
    def get_upstream_tables(self, table_name: str) -> Set[str]:
        """Get all tables that feed into the given table"""
        upstream = set()
        
        for task_lineage in self.task_lineages:
            if not task_lineage.lineage:
                continue
            
            # Check if this task produces the target table
            for target in task_lineage.lineage.targets:
                if target.full_name == table_name:
                    # Add all sources
                    for source in task_lineage.lineage.sources:
                        upstream.add(source.full_name)
        
        return upstream
    
    def get_downstream_tables(self, table_name: str) -> Set[str]:
        """Get all tables that consume the given table"""
        downstream = set()
        
        for task_lineage in self.task_lineages:
            if not task_lineage.lineage:
                continue
            
            # Check if this task uses the source table
            for source in task_lineage.lineage.sources:
                if source.full_name == table_name:
                    # Add all targets
                    for target in task_lineage.lineage.targets:
                        downstream.add(target.full_name)
        
        return downstream
    
    def get_workflows_for_table(self, table_name: str) -> Set[str]:
        """Get all workflows that reference a table"""
        return self.table_to_workflows.get(table_name, set())
    
    def get_all_tables(self) -> Set[str]:
        """Get all tables in the lineage graph"""
        tables = set()
        
        for task_lineage in self.task_lineages:
            if not task_lineage.lineage:
                continue
            
            for source in task_lineage.lineage.sources:
                tables.add(source.full_name)
            
            for target in task_lineage.lineage.targets:
                tables.add(target.full_name)
        
        return tables

    def generate_graph(
        self,
        output_path: Path,
        table_filter: Optional[str] = None,
        direction: str = "both",
        max_depth: Optional[int] = None
    ) -> Path:
        """
        Generate a Graphviz visualization of the lineage graph.
        
        Args:
            output_path: Path to save the graph (without extension)
            table_filter: Optional table name to focus on
            direction: "upstream", "downstream", or "both"
            max_depth: Maximum depth to traverse
            
        Returns:
            Path to the generated SVG file
        """
        import graphviz
        
        # Create directed graph with improved layout for large graphs
        dot = graphviz.Digraph(comment='Data Lineage')
        dot.attr(rankdir='LR')
        dot.attr('node', shape='cylinder', style='filled', fillcolor='lightblue')
        dot.attr('edge', color='gray')
        
        # Improve spacing for readability
        dot.attr(nodesep='0.8')  # Horizontal spacing between nodes
        dot.attr(ranksep='1.5')  # Vertical spacing between ranks
        dot.attr(splines='ortho')  # Use orthogonal edges for cleaner look
        
        # Determine which tables to include
        if table_filter:
            tables_to_show = self._get_related_tables(table_filter, direction, max_depth)
            tables_to_show.add(table_filter)
        else:
            tables_to_show = self.get_all_tables()
        
        # Filter out tables without database prefix (these are likely parsing errors)
        tables_to_show = {t for t in tables_to_show if '.' in t}
        
        
        # Categorize tables by layer for proper left-to-right layout
        layers = self.config.get('layer_patterns', [])
        layer_tables = {layer['name']: [] for layer in layers}
        other_tables = []
        
        for table in sorted(tables_to_show):
            assigned = False
            if '.' in table:
                db = table.split('.')[0]
                for layer in layers:
                    # Check if any pattern matches the database name
                    if any(pattern in db for pattern in layer['patterns']):
                        layer_tables[layer['name']].append(table)
                        assigned = True
                        break
            
            if not assigned:
                other_tables.append(table)
        
        # Add nodes with rank constraints for left-to-right flow
        # Iterate through configured layers in order
        for layer in layers:
            tables = layer_tables.get(layer['name'], [])
            if tables:
                with dot.subgraph(name=f"cluster_{layer['name']}") as s:
                    s.attr(rank='same')
                    s.attr(style='invis')  # Invisible cluster border
                    for table in tables:
                        color = layer.get('color', 'lightgray')
                        if table == table_filter:
                            s.node(table, table, fillcolor='yellow', penwidth='3')
                        else:
                            s.node(table, table, fillcolor=color)
                    color = '#D5E8D4'  # Green for golden
                    if table == table_filter:
                        s.node(table, table, fillcolor='yellow', penwidth='3')
                    else:
                        s.node(table, table, fillcolor=color)
        
        # Other tables (no rank constraint)
        for table in other_tables:
            color = 'lightgray'
            if table == table_filter:
                dot.node(table, table, fillcolor='yellow', penwidth='3')
            else:
                dot.node(table, table, fillcolor=color)
        
        # Add edges
        edges_added = set()
        for task_lineage in self.task_lineages:
            if not task_lineage.lineage:
                continue
            
            for target in task_lineage.lineage.targets:
                if target.full_name not in tables_to_show:
                    continue
                
                for source in task_lineage.lineage.sources:
                    if source.full_name not in tables_to_show:
                        continue
                    
                    edge = (source.full_name, target.full_name)
                    if edge not in edges_added:
                        dot.edge(source.full_name, target.full_name)
                        edges_added.add(edge)
        
        # Render to SVG
        output_path.parent.mkdir(parents=True, exist_ok=True)
        svg_path = dot.render(str(output_path), format='svg', cleanup=True)
        
        # Generate interactive HTML page
        html_path = self._generate_lineage_html(
            Path(svg_path),
            table_filter,
            direction
        )
        
        return html_path
    
    def get_table_layer(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get the layer configuration for a table based on its name.
        
        Args:
            table_name: Fully qualified table name
            
        Returns:
            Layer configuration dict or None if no match
        """
        if '.' not in table_name:
            return None
            
        db = table_name.split('.')[0]
        layers = self.config.get('layer_patterns', [])
        
        for layer in layers:
            if any(pattern in db for pattern in layer['patterns']):
                return layer
                
        return None

    def _generate_lineage_html(
        self,
        svg_path: Path,
        table_name: Optional[str],
        direction: str
    ) -> Path:
        """Generate interactive HTML page for lineage graph"""
        
        # Read SVG content
        svg_content = svg_path.read_text()
        
        # Determine navigation paths based on page location
        if table_name:
            # Individual table pages are in lineage/ subdirectory
            nav_home = "../index.html"
            nav_schedule = "../scheduled_workflows.html"
            nav_lineage = "../lineage.html"
        else:
            # Full lineage page is also in lineage/ subdirectory
            nav_home = "../index.html"
            nav_schedule = "../scheduled_workflows.html"
            nav_lineage = "../lineage.html"
        
        html_content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{'Lineage: ' + table_name if table_name else 'Full Data Lineage'} - Digdag Graph</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {{
      --primary: #1a365d;
      --primary-light: #2c5282;
      --accent: #3182ce;
      --success: #38a169;
      --font-sans: "Inter", "IBM Plex Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
      --gray-50: #f7fafc;
      --gray-100: #edf2f7;
      --gray-200: #e2e8f0;
      --gray-300: #cbd5e0;
      --gray-600: #4a5568;
      --gray-800: #1a202c;
      --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);

      /* Light Mode Colors */
      --bg-body: #ffffff;
      --bg-main: #f7fafc;
      --bg-card: #ffffff;
      --bg-sidebar: #ffffff;
      --bg-header: #1a365d;
      --text-main: #1a202c;
      --text-muted: #4a5568;
      --border-color: #e2e8f0;
      --shadow-color: rgba(0, 0, 0, 0.1);
    }}

    /* Dark Mode Colors */
    [data-theme="dark"] {{
      --bg-body: #171923;
      --bg-main: #1a202c;
      --bg-card: #2d3748;
      --bg-sidebar: #2d3748;
      --bg-header: #2d3748;
      --text-main: #f7fafc;
      --text-muted: #a0aec0;
      --border-color: #4a5568;
      --shadow-color: rgba(0, 0, 0, 0.4);
      --gray-50: #2d3748;
      --gray-100: #4a5568;
      --gray-200: #4a5568;
      --gray-600: #a0aec0;
      --gray-800: #f7fafc;
      --primary: #90cdf4; /* Lighter blue for dark mode */
      --accent: #63b3ed;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-sans);
      background: var(--bg-body); color: var(--text-main); font-size: 14px; line-height: 1.5;
      min-height: 100vh; display: flex; flex-direction: column;
      transition: background 0.3s ease, color 0.3s ease;
    }}
    header {{
      padding: 0 32px; height: 64px; background: var(--bg-header);
      border-bottom: 1px solid rgba(0,0,0,0.1); display: flex;
      align-items: center; justify-content: space-between;
      box-shadow: 0 2px 4px var(--shadow-color); position: sticky; top: 0; z-index: 1000;
      transition: background 0.3s ease;
    }}
    header h1 {{
      font-size: 18px; font-weight: 600; color: white; margin: 0;
    }}
    .nav-links {{ display: flex; gap: 4px; }}
    .nav-links a {{ 
      color: rgba(255, 255, 255, 0.9); text-decoration: none; 
      font-size: 14px; font-weight: 500; padding: 8px 16px;
      border-radius: 6px; transition: all 0.2s ease;
    }}
    .nav-links a:hover {{ background: rgba(255,255,255,0.1); color: white; }}
    .nav-links a.active {{ background: var(--accent); color: white; }}
    
    .header-controls {{ display: flex; align-items: center; gap: 16px; }}
    .theme-toggle {{
      background: rgba(255,255,255,0.1); border: none; cursor: pointer;
      color: white; padding: 8px; border-radius: 6px;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.2s;
    }}
    .theme-toggle:hover {{ background: rgba(255,255,255,0.2); }}

    main {{ flex: 1; padding: 32px; max-width: 100%; margin: 0 auto; overflow: auto; background: var(--bg-body); transition: background 0.3s ease; }}
    
    .info-bar {{
      background: var(--bg-card); border: 1px solid var(--border-color);
      border-radius: 8px; padding: 16px; margin-bottom: 24px;
      display: flex; justify-content: space-between; align-items: center;
      flex-wrap: wrap; gap: 16px; box-shadow: 0 2px 4px var(--shadow-color);
    }}
    .info-bar h1 {{
      font-size: 20px; font-weight: 600; color: var(--text-main);
      margin: 0;
    }}
    .info-bar .controls {{
      display: flex; gap: 8px; align-items: center;
    }}
    .btn {{
      padding: 8px 16px; background: var(--accent); color: white;
      text-decoration: none; border-radius: 6px; font-size: 13px;
      font-weight: 500; transition: all 0.2s; border: none;
      cursor: pointer;
    }}
    .btn:hover {{ background: var(--primary-light); }}
    .btn-secondary {{
      background: var(--bg-card); color: var(--text-main);
      border: 1px solid var(--border-color);
    }}
    .btn-secondary:hover {{ background: var(--gray-50); }}
    
    .graph-container {{
      background: var(--bg-card); border: 1px solid var(--border-color);
      border-radius: 8px; padding: 24px; box-shadow: var(--shadow);
      overflow: auto; min-height: 500px;
    }}
    .graph-container svg {{
      max-width: 100%; height: auto;
    }}
    
    .legend {{
      background: var(--bg-card); border: 1px solid var(--border-color);
      border-radius: 8px; padding: 16px; margin-top: 24px;
    }}
    .legend h3 {{
      font-size: 14px; font-weight: 600; margin-bottom: 12px; color: var(--text-main);
    }}
    .legend-items {{
      display: flex; gap: 24px; flex-wrap: wrap; color: var(--text-main);
    }}
    .legend-item {{
      display: flex; align-items: center; gap: 8px;
    }}
    .legend-color {{
      width: 20px; height: 20px; border-radius: 4px;
      border: 1px solid var(--border-color);
    }}
    
    /* Dropdown CSS */
    .dropdown {{
      position: relative; display: inline-block;
    }}
    .dropdown-content {{
      display: none; position: absolute; background-color: var(--bg-card);
      min-width: 120px; box-shadow: 0px 8px 16px 0px var(--shadow-color);
      z-index: 10000; border-radius: 6px; overflow: visible;
      top: 100%; left: 0; margin-top: 10px; border: 1px solid var(--border-color);
    }}
    /* Invisible bridge to prevent hover loss */
    .dropdown-content::before {{
      content: ""; position: absolute;
      top: -10px; left: 0; width: 100%; height: 10px;
      background: transparent;
    }}
    .dropdown-content a {{
      color: var(--text-main); padding: 12px 16px; text-decoration: none;
      display: block; font-size: 13px;
    }}
    .dropdown-content a:hover {{ background-color: var(--gray-50); }}
    .dropdown:hover .dropdown-content {{ display: block; }}
    
    /* Focus Mode CSS */
    .btn.active {{
      background: var(--accent); color: white;
      box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
    }}
    g.node.dimmed, g.edge.dimmed {{
      opacity: 0.1 !important; transition: opacity 0.3s;
    }}
    g.node.focused, g.edge.focused {{
      opacity: 1 !important; transition: opacity 0.3s;
    }}
    
    /* SVG Dark Mode Styles */
    [data-theme="dark"] svg text {{
      fill: #f7fafc !important;
    }}
    [data-theme="dark"] .graph-container {{
      background: #2d3748;
    }}
    [data-theme="dark"] .legend {{
      background: #2d3748; color: #f7fafc;
    }}
  </style>
</head>
<body>
<header>
  <h1>🔗 Digdag Data Lineage</h1>
  
  <div class="header-controls">
    <nav class="nav-links">
      <a href="{nav_home}">🏠 Home</a>
      <a href="{nav_schedule}">📅 Scheduled</a>
      <a href="{nav_lineage}" class="active">🔗 Lineage</a>
    </nav>
    <button class="theme-toggle" id="themeToggle" title="Toggle Dark Mode">
      <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
      </svg>
    </button>
  </div>
</header>
<main>
  <div class="info-bar">
    <h1>{'📊 ' + table_name if table_name else '🌐 Full Data Lineage'}</h1>
    <div class="controls">
      <button class="btn btn-secondary" onclick="toggleFocusMode()" id="focusBtn">🎯 Focus Mode: OFF</button>
      <div class="dropdown">
        <button class="btn btn-secondary">📸 Export</button>
        <div class="dropdown-content">
          <a href="#" onclick="exportSVG()">SVG</a>
          <a href="#" onclick="exportPNG()">PNG</a>
        </div>
      </div>
      <button class="btn btn-secondary" onclick="zoomIn()">Zoom In</button>
      <button class="btn btn-secondary" onclick="zoomOut()">Zoom Out</button>
      <button class="btn btn-secondary" onclick="resetZoom()">Reset</button>
      <a href="{nav_lineage}" class="btn">Back to List</a>
    </div>
  </div>

  <div class="graph-container" id="graph">
    {svg_content}
  </div>

  <div class="legend">
    <h3>Legend</h3>
    <div class="legend-items">
"""
        # Generate legend items dynamically from config
        layers = self.config.get('layer_patterns', [])
        for layer in layers:
            html_content += f"""      <div class="legend-item">
        <div class="legend-color" style="background: {layer['color']};"></div>
        <span>{layer['label']}</span>
      </div>
"""
            
        html_content += f"""      {'<div class="legend-item"><div class="legend-color" style="background: yellow;"></div><span>Focus Table</span></div>' if table_name else ''}
    </div>
  </div>
</main>
"""

        html_content += """
<script>
let scale = 1;
let graph, svg;
let focusMode = false;
const graphData = {};

document.addEventListener('DOMContentLoaded', function() {
  graph = document.getElementById('graph');
  if (graph) {
    svg = graph.querySelector('svg');
    if (svg) {
      initGraphInteractions();
    } else {
      console.error('SVG element not found in graph container');
    }
  } else {
    console.error('Graph container not found');
  }
  
  // Dark Mode Logic
  const themeToggle = document.getElementById('themeToggle');
  const storedTheme = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  if (storedTheme === 'dark' || (!storedTheme && prefersDark)) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
  
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
    });
  }
});

function initGraphInteractions() {
  // Build graph data structure for highlighting
  svg.querySelectorAll('g.edge').forEach(edge => {
    const title = edge.querySelector('title');
    if (title) {
      const [source, target] = title.textContent.split('->').map(s => s.trim());
      if (!graphData[source]) graphData[source] = { upstream: [], downstream: [] };
      if (!graphData[target]) graphData[target] = { upstream: [], downstream: [] };
      graphData[source].downstream.push(target);
      graphData[target].upstream.push(source);
    }
  });

  // Make SVG clickable tables navigate
  svg.querySelectorAll('g.node').forEach(node => {
    node.style.cursor = 'pointer';
    
    // Click to navigate or focus
    node.addEventListener('click', function(e) {
      const title = this.querySelector('title');
      if (title) {
        const tableName = title.textContent;
        
        if (focusMode) {
          focusNode(tableName);
        } else {
          const safeName = tableName.replace(/\\./g, '_');
          const htmlPath = `${safeName}.html`;
          window.location.href = htmlPath;
        }
      }
    });
    
    // Hover to highlight dependencies (only if not in focus mode)
    node.addEventListener('mouseenter', function(e) {
      if (focusMode) return;
      
      const title = this.querySelector('title');
      if (!title) return;
      
      const tableName = title.textContent;
      const data = graphData[tableName];
      if (!data) return;
      
      // Highlight current node
      this.style.opacity = '1';
      const ellipse = this.querySelector('ellipse, polygon');
      if (ellipse) {
        ellipse.style.strokeWidth = '3';
        ellipse.style.stroke = '#3182ce';
      }
      
      // Highlight upstream nodes and edges
      data.upstream.forEach(upstreamTable => {
        highlightNode(upstreamTable, '#FF6B6B');
        highlightEdge(upstreamTable, tableName, '#FF6B6B');
      });
      
      // Highlight downstream nodes and edges
      data.downstream.forEach(downstreamTable => {
        highlightNode(downstreamTable, '#4ECDC4');
        highlightEdge(tableName, downstreamTable, '#4ECDC4');
      });
      
      // Dim other nodes
      svg.querySelectorAll('g.node').forEach(n => {
        const t = n.querySelector('title');
        if (t && t.textContent !== tableName && 
            !data.upstream.includes(t.textContent) && 
            !data.downstream.includes(t.textContent)) {
          n.style.opacity = '0.2';
        }
      });
      
      // Dim other edges
      svg.querySelectorAll('g.edge').forEach(e => {
        const t = e.querySelector('title');
        if (t) {
          const [src, tgt] = t.textContent.split('->').map(s => s.trim());
          if (!((src === tableName && data.downstream.includes(tgt)) ||
                (tgt === tableName && data.upstream.includes(src)))) {
            e.style.opacity = '0.1';
          }
        }
      });
    });
    
    node.addEventListener('mouseleave', function(e) {
      if (focusMode) return;
      
      // Reset all highlighting
      svg.querySelectorAll('g.node').forEach(n => {
        n.style.opacity = '1';
        const ellipse = n.querySelector('ellipse, polygon');
        if (ellipse) {
          ellipse.style.strokeWidth = '1';
          ellipse.style.stroke = 'black';
        }
      });
      
      svg.querySelectorAll('g.edge').forEach(e => {
        e.style.opacity = '1';
        const path = e.querySelector('path');
        if (path) {
          path.style.strokeWidth = '1';
          path.style.stroke = 'gray';
        }
      });
    });
  });
}

function resetFocus() {
  svg.querySelectorAll('g.node, g.edge').forEach(el => {
    el.classList.remove('dimmed', 'focused');
  });
}

function toggleFocusMode() {
  console.log('Toggling focus mode');
  focusMode = !focusMode;
  const btn = document.getElementById('focusBtn');
  if (focusMode) {
    btn.classList.add('active');
    btn.textContent = '🎯 Focus Mode: ON';
    if (graph) graph.style.cursor = 'crosshair';
  } else {
    btn.classList.remove('active');
    btn.textContent = '🎯 Focus Mode: OFF';
    if (graph) graph.style.cursor = 'default';
    resetFocus();
  }
}

function focusNode(tableName) {
  if (!focusMode) return;
  
  const data = graphData[tableName];
  if (!data) return;
  
  // Reset first
  resetFocus();
  
  // Identify all connected nodes (upstream + downstream + self)
  const connected = new Set([tableName, ...data.upstream, ...data.downstream]);
  
  // Dim everything
  svg.querySelectorAll('g.node').forEach(node => {
    const title = node.querySelector('title').textContent;
    if (connected.has(title)) {
      node.classList.add('focused');
    } else {
      node.classList.add('dimmed');
    }
  });
  
  svg.querySelectorAll('g.edge').forEach(edge => {
    const title = edge.querySelector('title');
    if (title) {
      const [src, tgt] = title.textContent.split('->').map(s => s.trim());
      if (connected.has(src) && connected.has(tgt)) {
        edge.classList.add('focused');
      } else {
        edge.classList.add('dimmed');
      }
    }
  });
}

function exportSVG() {
  const svgData = new XMLSerializer().serializeToString(svg);
  const blob = new Blob([svgData], {type: 'image/svg+xml;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'lineage_graph.svg';
  link.click();
}

function exportPNG() {
  const canvas = document.createElement('canvas');
  const bbox = svg.getBBox();
  canvas.width = bbox.width + 100;
  canvas.height = bbox.height + 100;
  const ctx = canvas.getContext('2d');
  
  // Handle Dark Mode for export
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  ctx.fillStyle = isDark ? '#2d3748' : 'white';
  
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  const img = new Image();
  const svgData = new XMLSerializer().serializeToString(svg);
  const blob = new Blob([svgData], {type: 'image/svg+xml;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  
  img.onload = function() {
    ctx.drawImage(img, 50, 50);
    const pngUrl = canvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.href = pngUrl;
    link.download = 'lineage_graph.png';
    link.click();
    URL.revokeObjectURL(url);
  };
  img.src = url;
}

function zoomIn() {
  scale = Math.min(scale + 0.2, 3);
  svg.style.transform = `scale(${scale})`;
  svg.style.transformOrigin = 'top left';
}

function zoomOut() {
  scale = Math.max(scale - 0.2, 0.5);
  svg.style.transform = `scale(${scale})`;
  svg.style.transformOrigin = 'top left';
}

function resetZoom() {
  scale = 1;
  svg.style.transform = 'scale(1)';
}

function highlightNode(tableName, color) {
  svg.querySelectorAll('g.node').forEach(node => {
    const title = node.querySelector('title');
    if (title && title.textContent === tableName) {
      node.style.opacity = '1';
      const ellipse = node.querySelector('ellipse, polygon');
      if (ellipse) {
        ellipse.style.strokeWidth = '2';
        ellipse.style.stroke = color;
      }
    }
  });
}

function highlightEdge(source, target, color) {
  svg.querySelectorAll('g.edge').forEach(edge => {
    const title = edge.querySelector('title');
    if (title) {
      const [src, tgt] = title.textContent.split('->').map(s => s.trim());
      if (src === source && tgt === target) {
        edge.style.opacity = '1';
        const path = edge.querySelector('path');
        if (path) {
          path.style.strokeWidth = '2';
          path.style.stroke = color;
        }
      }
    }
  });
}

// Add search functionality for full lineage graph
"""
        
        # Add search functionality only for full lineage graph (not individual tables)
        if not table_name:
            html_content += """
// Add search functionality for full lineage graph
document.addEventListener('DOMContentLoaded', function() {
  // Ensure svg is available
  if (!svg) {
    const graph = document.getElementById('graph');
    if (graph) svg = graph.querySelector('svg');
  }
  
  if (!svg) return;

  const searchInput = document.createElement('input');
  searchInput.type = 'search';
  searchInput.placeholder = 'Search for table...';
  searchInput.style.cssText = `
    position: fixed; top: 80px; right: 350px; z-index: 1001;
    padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 6px;
    font-family: var(--font-sans); font-size: 14px;
    background: var(--bg-card); color: var(--text-main);
    box-shadow: 0 4px 6px -1px var(--shadow-color);
    width: 250px;
  `;

  // Add database filter dropdown
  const dbFilter = document.createElement('select');
  dbFilter.style.cssText = `
    position: fixed; top: 80px; right: 40px; z-index: 1001;
    padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 6px;
    font-family: var(--font-sans); font-size: 14px;
    background: var(--bg-card); color: var(--text-main);
    box-shadow: 0 4px 6px -1px var(--shadow-color);
    width: 280px; cursor: pointer;
  `;

  // Collect all databases
  const databases = new Set();
  let tableCount = 0;
  svg.querySelectorAll('g.node title').forEach(t => {
    const tableName = t.textContent;
    if (tableName.includes('.')) {
      const db = tableName.split('.')[0];
      databases.add(db);
      tableCount++;
    }
  });

  // Add options
  const allOption = document.createElement('option');
  allOption.value = '';
  allOption.textContent = `🗂️ All Databases (${tableCount} tables)`;
  dbFilter.appendChild(allOption);

  Array.from(databases).sort().forEach(db => {
    const option = document.createElement('option');
    option.value = db;
    option.textContent = `📊 ${db}`;
    dbFilter.appendChild(option);
  });

  // Append controls
  document.body.appendChild(searchInput);
  document.body.appendChild(dbFilter);

  // Filter Logic
  function applyFilters() {
    const searchQuery = searchInput.value.toLowerCase();
    const selectedDb = dbFilter.value;
  
  if (!searchQuery && !selectedDb) {
    // Reset all
    svg.querySelectorAll('g.node').forEach(n => {
      n.style.opacity = '1';
      const ellipse = n.querySelector('ellipse, polygon');
      if (ellipse) {
        ellipse.style.strokeWidth = '1';
        ellipse.style.stroke = 'black';
      }
    });
    svg.querySelectorAll('g.edge').forEach(e => e.style.opacity = '1');
    return;
  }
  
  // Find matching nodes
  const matches = [];
  svg.querySelectorAll('g.node').forEach(node => {
    const title = node.querySelector('title');
    if (!title) return;
    
    const tableName = title.textContent;
    const matchesSearch = !searchQuery || tableName.toLowerCase().includes(searchQuery);
    const matchesDb = !selectedDb || tableName.startsWith(selectedDb + '.');
    
    if (matchesSearch && matchesDb) {
      matches.push(tableName);
      node.style.opacity = '1';
      const ellipse = node.querySelector('ellipse, polygon');
      if (ellipse) {
        ellipse.style.strokeWidth = '3';
        ellipse.style.stroke = '#3182ce';
      }
    } else {
      node.style.opacity = '0.1';
      const ellipse = node.querySelector('ellipse, polygon');
      if (ellipse) {
        ellipse.style.strokeWidth = '1';
        ellipse.style.stroke = 'black';
      }
    }
  });
  
  // Highlight edges connected to matches
  svg.querySelectorAll('g.edge').forEach(edge => {
    const title = edge.querySelector('title');
    if (title) {
      const [src, tgt] = title.textContent.split('->').map(s => s.trim());
      if (matches.includes(src) || matches.includes(tgt)) {
        edge.style.opacity = '1';
      } else {
        edge.style.opacity = '0.05';
      }
    }
  });
}

searchInput.addEventListener('input', applyFilters);
dbFilter.addEventListener('change', applyFilters);

document.body.appendChild(searchInput);
document.body.appendChild(dbFilter);
});
"""
        
        html_content += """
</script>

</body>
</html>
"""
        
        # Write HTML file
        html_path = svg_path.with_suffix('.html')
        html_path.write_text(html_content)
        
        return html_path
    
    def _get_related_tables(
        self,
        table_name: str,
        direction: str,
        max_depth: Optional[int]
    ) -> Set[str]:
        """Get tables related to the given table"""
        related = set()
        
        if direction in ["upstream", "both"]:
            related.update(self._get_upstream_recursive(table_name, max_depth or 999))
        
        if direction in ["downstream", "both"]:
            related.update(self._get_downstream_recursive(table_name, max_depth or 999))
        
        return related
    
    def _get_upstream_recursive(self, table_name: str, depth: int) -> Set[str]:
        """Recursively get upstream tables"""
        if depth <= 0:
            return set()
        
        upstream = self.get_upstream_tables(table_name)
        result = upstream.copy()
        
        for table in upstream:
            result.update(self._get_upstream_recursive(table, depth - 1))
        
        return result
    
    def _get_downstream_recursive(self, table_name: str, depth: int) -> Set[str]:
        """Recursively get downstream tables"""
        if depth <= 0:
            return set()
        
        downstream = self.get_downstream_tables(table_name)
        result = downstream.copy()
        
        for table in downstream:
            result.update(self._get_downstream_recursive(table, depth - 1))
        
        return result
