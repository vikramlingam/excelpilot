from typing import Any

DESTRUCTIVE_TOOLS: set[str] = {
    "sheet_delete",
    "workbook_reset",
    "range_clear",
    "range_insert_delete_rows_cols",
    "table_to_range",
    "pivot_delete",
    "chart_delete",
    "script_run_typescript",
    "vba_run",
}

WRITE_TOOLS: set[str] = {
    "range_write_values",
    "range_write_formulas",
    "range_clear",
    "range_fill_down",
    "range_insert_delete_rows_cols",
    "range_copy",
    "table_create",
    "table_add_column",
    "table_sort",
    "table_filter",
    "table_to_range",
    "pivot_create",
    "pivot_add_row_field",
    "pivot_add_column_field",
    "pivot_add_value",
    "pivot_add_filter",
    "pivot_refresh",
    "pivot_delete",
    "chart_create",
    "chart_configure",
    "chart_delete",
    "slicer_add",
    "format_range",
    "number_format",
    "conditional_format_add",
    "conditional_format_clear",
    "autofit",
    "freeze_panes",
    "column_width_row_height",
    "data_validation_add",
    "trim_clean_range",
    "name_define",
    "comment_add",
    "note_add",
    "sheet_add",
    "sheet_rename",
    "sheet_delete",
    "workbook_reset",
    "sheet_set_visibility",
    "sheet_move",
    "script_run_typescript",
    "vba_run",
    "snapshot_restore",
}


def is_destructive_tool(tool_name: str) -> bool:
    return tool_name in DESTRUCTIVE_TOOLS


def is_write_tool(tool_name: str) -> bool:
    return tool_name in WRITE_TOOLS or tool_name in DESTRUCTIVE_TOOLS


def is_wipe_all_request(user_message: str) -> bool:
    """True when the user asked to delete/reset every worksheet, not just cell contents."""
    text = (user_message or "").lower()
    if not any(w in text for w in ("delete", "remove", "reset", "wipe", "start over", "clear all")):
        return False
    return any(
        w in text
        for w in (
            "all worksheet",
            "all sheet",
            "every sheet",
            "every worksheet",
            "all tabs",
            "entire workbook",
            "whole workbook",
            "the workbook",
            "reset workbook",
            "start over",
            "delete everything",
            "remove everything",
            "wipe the workbook",
        )
    )


def extract_sheet_delete_target(user_message: str, known_sheets: list[str] | None = None) -> str | None:
    """Return the worksheet name the user wants deleted, or None.

    Handles: "delete the Inventory worksheet", "remove sheet Sales", "delete 'Q1 Data' tab",
    and bare "delete Inventory" when Inventory is a known sheet name.
    """
    import re

    text = (user_message or "").strip()
    low = text.lower()
    if not any(w in low for w in ("delete", "remove", "drop", "get rid of")):
        return None
    if is_wipe_all_request(text):
        return None

    quoted = re.search(r"[\"'“‘]([^\"'”’]{1,64})[\"'”’]", text)
    if quoted:
        return quoted.group(1).strip()

    patterns = [
        r"(?:delete|remove|drop|get rid of)\s+(?:the\s+)?(?:worksheet|sheet|tab)\s+(?:named\s+|called\s+)?([A-Za-z0-9 _\-\.]{1,64}?)(?:\s+(?:worksheet|sheet|tab))?\s*[\.\!\?]?$",
        r"(?:delete|remove|drop|get rid of)\s+(?:the\s+)?([A-Za-z0-9 _\-\.]{1,64}?)\s+(?:worksheet|sheet|tab)\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            cand = m.group(1).strip().strip("'\"")
            if cand and cand.lower() not in {"this", "that", "the", "a", "current", "active"}:
                return cand

    if known_sheets:
        for name in sorted(known_sheets, key=len, reverse=True):
            if name and name.lower() in low:
                return name
    if any(w in low for w in ("this worksheet", "this sheet", "current sheet", "active sheet", "this tab")):
        return "__ACTIVE__"
    return None


def estimate_write_cells(tool_name: str, args: dict[str, Any]) -> int:
    """Best-effort cell count for a write so we can ask the user before large inserts."""
    values = args.get("values") or args.get("formulas")
    if isinstance(values, list) and values:
        rows = len(values)
        cols = max((len(r) if isinstance(r, list) else 1) for r in values) if rows else 1
        return rows * cols
    address = str(args.get("address") or "")
    import re

    m = re.search(r"([A-Za-z]+)(\d+):([A-Za-z]+)(\d+)", address.replace("$", ""))
    if not m:
        return 1
    def col_n(letters: str) -> int:
        n = 0
        for ch in letters.upper():
            n = n * 26 + (ord(ch) - 64)
        return n
    return max(1, (int(m.group(4)) - int(m.group(2)) + 1) * (col_n(m.group(3)) - col_n(m.group(1)) + 1))


def needs_human_approval(tool_name: str, args: dict[str, Any]) -> bool:
    """Large inserts, generated data, and destructive ops wait for a click."""
    if tool_name in DESTRUCTIVE_TOOLS:
        return True
    if tool_name in {"range_write_values", "range_write_formulas", "range_fill_down"}:
        return estimate_write_cells(tool_name, args) >= 20
    return False


_ACTION_WORDS = (
    "add", "create", "make", "put", "insert", "write", "set", "apply", "change", "update", "fill",
    "delete", "remove", "clear", "sort", "filter", "highlight", "bold", "color", "colour", "sum",
    "total", "calculate", "compute", "build", "generate", "rename", "move", "copy", "convert",
    "format", "clean", "trim", "dedupe", "fix", "replace",
)


def heuristic_intent(user_message: str) -> str:
    """Local, zero-latency intent router. Biases toward the broad `edit_values` skill so the
    model always has write tools when the user asks for an action."""
    text = user_message.lower().strip()
    has_action = any(f" {w} " in f" {text} " or text.startswith(w) for w in _ACTION_WORDS)
    refers_to_sheet = any(n in text for n in ("this", "the sheet", "the data", "column", "row", "cell", "range", "workbook", "selection"))
    # "Which region has the highest sales?" is a data question → needs analyze tools, not a lecture.
    data_question = any(n in text for n in ("which", "highest", "lowest", "most", "least", "average", "total", "how many", "how much", "top ", "bottom "))

    # Pure knowledge questions ("What is XLOOKUP?") never need tools.
    if (
        not has_action
        and not refers_to_sheet
        and not data_question
        and (text.endswith("?") or text.startswith(("what is", "what's", "how do i", "how does", "explain", "why does", "difference between")))
    ):
        return "question_only"

    if any(n in text for n in ("dashboard", "kpi card", "kpi tiles")):
        return "dashboard"
    if any(n in text for n in ("pivot", "chart", "graph", "plot", "slicer", "visuali")):
        return "pivot_or_chart"
    if any(n in text for n in ("office.js", "typescript", "run a script", "write a script", "vba", "macro")):
        return "script"
    if any(
        n in text
        for n in (
            "analyze",
            "analyse",
            "analysis",
            "audit",
            "summarize",
            "summarise",
            "health check",
            "review this workbook",
            "what does this sheet",
            "what's in this",
        )
    ):
        return "analyze"
    if any(n in text for n in ("conditional", "highlight", "bold", "italic", "font", "fill color", "background", "border", "number format", "currency format", "percent format", "autofit", "freeze", "colour", "color")) and not any(n in text for n in ("formula", "sumif", "xlookup")):
        return "format"
    if any(n in text for n in ("formula", "xlookup", "vlookup", "index match", "sumif", "countif", "#n/a", "#ref", "#value", "#div", "lambda", "let(")):
        return "formula"
    if not has_action and (refers_to_sheet or data_question) and (
        text.endswith("?") or text.startswith(("what", "why", "how", "which", "is ", "are ", "show me", "tell me"))
    ):
        return "analyze"
    return "edit_values"


def heuristic_tier(user_message: str, stats: dict[str, Any] | None = None) -> str:
    text = user_message.lower()
    stats = stats or {}
    if any(k in text for k in ("financial model", "reconcile", "multi-sheet", "dcf", "three statement")):
        return "capable"
    if int(stats.get("sheet_count", 1) or 1) >= 8 or int(stats.get("formula_count", 0) or 0) >= 200:
        return "capable"
    return "fast"


def evaluate_static_policy(
    tool_name: str, args: dict[str, Any], context: dict[str, Any] | None = None
) -> tuple[bool, str | None]:
    ctx = context or {}

    if tool_name == "sheet_delete":
        sheet_count = ctx.get("sheet_count", 2)
        if sheet_count <= 1:
            return False, "Cannot delete the only remaining worksheet in the workbook."
        referenced_sheets: list[str] = ctx.get("referenced_sheets", [])
        target_sheet = args.get("sheet_name") or args.get("sheet", "")
        if target_sheet in referenced_sheets:
            return False, f"Sheet '{target_sheet}' is referenced by formulas in other sheets."

    if tool_name == "range_clear":
        cell_count = ctx.get("target_cell_count", 0)
        if cell_count > 50000:
            return False, f"Clearing {cell_count} cells exceeds safe threshold of 50000."

    return True, None
