"""Context pack generation for AI assistants."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import json


def build_context_pack(
    workflows: List[Dict[str, Any]],
    lineage_data: List[Dict[str, Any]],
    sql_files: List[Dict[str, Any]],
    lineage_issues: List[Dict[str, Any]],
    input_path: Path,
    output_dir: Path,
    tool_version: str,
) -> Dict[str, Any]:
    scheduled_count = 0
    workflow_rows = []
    workflow_inputs = []
    workflow_outputs = []
    op_counts = []

    lineage_task_count = 0
    lineage_resolved_tasks = 0
    lineage_unresolved_tasks = 0

    for wf in workflows:
        summary = wf.get("summary") or {}
        if wf.get("schedule"):
            scheduled_count += 1

        workflow_rows.append({
            "name": wf.get("name", ""),
            "project": wf.get("project", ""),
            "file": wf.get("file", ""),
            "schedule": wf.get("schedule") or "",
            "taskCount": summary.get("task_count", 0),
            "tdCount": summary.get("td_queries", 0),
            "inputTableCount": summary.get("input_tables", 0),
            "outputTableCount": summary.get("output_tables", 0),
            "hasError": bool(summary.get("has_error_handlers")),
            "hasParallel": bool(summary.get("has_parallel")),
            "hasRetry": bool(summary.get("has_retry")),
        })

        for table in summary.get("input_table_list") or []:
            workflow_inputs.append({
                "workflow": wf.get("name", ""),
                "table": table,
            })

        for table in summary.get("output_table_list") or []:
            workflow_outputs.append({
                "workflow": wf.get("name", ""),
                "table": table,
            })

        for op, count in (summary.get("operators") or {}).items():
            op_counts.append({
                "workflow": wf.get("name", ""),
                "operator": op,
                "count": count,
            })

        lineage_task_count += summary.get("lineage_task_count", 0)
        lineage_resolved_tasks += summary.get("lineage_resolved_tasks", 0)
        lineage_unresolved_tasks += summary.get("lineage_unresolved_tasks", 0)

    table_rows = []
    for table in lineage_data:
        layer = table.get("layer")
        layer_name = layer.get("name") if isinstance(layer, dict) else ""
        table_rows.append({
            "name": table.get("full_name", ""),
            "database": table.get("database") or "",
            "layer": layer_name,
            "upstreamCount": table.get("upstream_count", 0),
            "downstreamCount": table.get("downstream_count", 0),
            "workflowCount": table.get("workflow_count", 0),
        })

    missing_sql_files = sum(
        1 for sql in sql_files
        if not sql.get("inline") and not sql.get("exists")
    )
    inline_sql_files = sum(1 for sql in sql_files if sql.get("inline"))
    lineage_issue_count = len(lineage_issues)
    lineage_unresolved_templates = sum(
        1 for issue in lineage_issues
        if issue.get("template_variables")
    )

    context = {
        "context": {
            "task": "Digdag workflow context",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "input_path": str(input_path),
            "output_dir": str(output_dir),
            "tool_version": tool_version,
        },
        "stats": {
            "workflowCount": len(workflows),
            "scheduledCount": scheduled_count,
            "unscheduledCount": len(workflows) - scheduled_count,
            "tableCount": len(table_rows),
            "sqlFileCount": len(sql_files),
            "inlineSqlCount": inline_sql_files,
            "missingSqlFileCount": missing_sql_files,
            "lineageTaskCount": lineage_task_count,
            "lineageResolvedTaskCount": lineage_resolved_tasks,
            "lineageUnresolvedTaskCount": lineage_unresolved_tasks,
            "lineageIssueCount": lineage_issue_count,
            "lineageUnresolvedTemplateCount": lineage_unresolved_templates,
        },
        "workflows": workflow_rows,
        "workflowInputs": workflow_inputs,
        "workflowOutputs": workflow_outputs,
        "tables": table_rows,
        "sqlFiles": sql_files,
        "lineageIssues": lineage_issues,
        "opCounts": op_counts,
    }

    return context


def write_context_pack(context: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "context.json"
    toon_path = output_dir / "context.toon"

    json_path.write_text(
        json.dumps(context, indent=2, ensure_ascii=True),
        encoding="utf-8"
    )

    toon_path.write_text(to_toon(context), encoding="utf-8")


def to_toon(context: Dict[str, Any]) -> str:
    lines: List[str] = []

    def toon_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        text = str(value)
        needs_quotes = (
            text.strip() != text or
            any(ch in text for ch in [",", ":", "{", "}", "[", "]", "\n"])
        )
        if needs_quotes:
            return json.dumps(text, ensure_ascii=True)
        return text

    def append_map(name: str, values: Dict[str, Any]) -> None:
        lines.append(f"{name}:")
        for key in sorted(values.keys()):
            lines.append(f"  {key}: {toon_value(values[key])}")

    def append_table(name: str, rows: List[Dict[str, Any]], fields: List[str]) -> None:
        lines.append(f"{name}[{len(rows)}]{{{','.join(fields)}}}:")
        for row in rows:
            values = [toon_value(row.get(field, "")) for field in fields]
            lines.append(f"  {','.join(values)}")

    append_map("context", context.get("context", {}))
    append_map("stats", context.get("stats", {}))

    append_table(
        "workflows",
        context.get("workflows", []),
        [
            "name",
            "project",
            "file",
            "schedule",
            "taskCount",
            "tdCount",
            "inputTableCount",
            "outputTableCount",
            "hasError",
            "hasParallel",
            "hasRetry",
        ],
    )

    append_table(
        "workflowInputs",
        context.get("workflowInputs", []),
        ["workflow", "table"],
    )

    append_table(
        "workflowOutputs",
        context.get("workflowOutputs", []),
        ["workflow", "table"],
    )

    append_table(
        "tables",
        context.get("tables", []),
        ["name", "database", "layer", "upstreamCount", "downstreamCount", "workflowCount"],
    )

    append_table(
        "sqlFiles",
        context.get("sqlFiles", []),
        ["workflow", "task", "file", "resolved_path", "exists", "inline"],
    )

    issue_rows = []
    for issue in context.get("lineageIssues", []):
        issue_rows.append({
            "workflow": issue.get("workflow", ""),
            "task": issue.get("task", ""),
            "file": issue.get("file", ""),
            "templateVars": ",".join(issue.get("template_variables") or []),
            "error": issue.get("error", ""),
        })
    append_table(
        "lineageIssues",
        issue_rows,
        ["workflow", "task", "file", "templateVars", "error"],
    )

    append_table(
        "opCounts",
        context.get("opCounts", []),
        ["workflow", "operator", "count"],
    )

    return "\n".join(lines) + "\n"
