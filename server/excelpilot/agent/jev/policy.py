from typing import Any

DESTRUCTIVE_TOOLS: set[str] = {
    "sheet_delete",
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


def evaluate_static_policy(
    tool_name: str, args: dict[str, Any], context: dict[str, Any] | None = None
) -> tuple[bool, str | None]:
    # Returns (allowed, block_reason)
    ctx = context or {}

    # Prevent deleting the only sheet
    if tool_name == "sheet_delete":
        sheet_count = ctx.get("sheet_count", 2)
        if sheet_count <= 1:
            return False, "Cannot delete the only remaining worksheet in the workbook."

        # Prevent deleting a sheet that is referenced by formulas
        referenced_sheets: list[str] = ctx.get("referenced_sheets", [])
        target_sheet = args.get("sheet_name") or args.get("sheet", "")
        if target_sheet in referenced_sheets:
            return False, f"Sheet '{target_sheet}' is referenced by formulas in other sheets."

    # Prevent clearing massive ranges unless explicitly intended
    if tool_name == "range_clear":
        cell_count = ctx.get("target_cell_count", 0)
        if cell_count > 50000:
            return False, f"Clearing {cell_count} cells exceeds safe threshold of 50000."

    return True, None
