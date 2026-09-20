from fastmcp import FastMCP

from excelpilot.tools import (
    analysis,
    charts,
    formatting,
    formulas,
    names,
    pivots,
    ranges,
    scripts,
    sheets,
    snapshots,
    tables,
    validation,
    view,
    workbook,
)

mcp = FastMCP("ExcelPilot")

# Register all tools onto the FastMCP instance
mcp.tool(name="workbook_info")(workbook.workbook_info)
mcp.tool(name="workbook_schema_cards")(workbook.workbook_schema_cards)

mcp.tool(name="sheet_list")(sheets.sheet_list)
mcp.tool(name="sheet_add")(sheets.sheet_add)
mcp.tool(name="sheet_rename")(sheets.sheet_rename)
mcp.tool(name="sheet_delete")(sheets.sheet_delete)
mcp.tool(name="sheet_set_visibility")(sheets.sheet_set_visibility)

mcp.tool(name="range_read")(ranges.range_read)
mcp.tool(name="range_write_values")(ranges.range_write_values)
mcp.tool(name="range_write_formulas")(ranges.range_write_formulas)
mcp.tool(name="range_clear")(ranges.range_clear)
mcp.tool(name="range_fill_down")(ranges.range_fill_down)

mcp.tool(name="formula_explain")(formulas.formula_explain)
mcp.tool(name="formula_evaluate")(formulas.formula_evaluate)
mcp.tool(name="formula_audit_sheet")(formulas.formula_audit_sheet)

mcp.tool(name="table_create")(tables.table_create)
mcp.tool(name="table_list")(tables.table_list)
mcp.tool(name="table_add_column")(tables.table_add_column)

mcp.tool(name="pivot_create")(pivots.pivot_create)
mcp.tool(name="pivot_list")(pivots.pivot_list)
mcp.tool(name="pivot_add_row_field")(pivots.pivot_add_row_field)
mcp.tool(name="pivot_add_value")(pivots.pivot_add_value)
mcp.tool(name="pivot_refresh")(pivots.pivot_refresh)

mcp.tool(name="chart_create")(charts.chart_create)
mcp.tool(name="chart_list")(charts.chart_list)
mcp.tool(name="slicer_add")(charts.slicer_add)

mcp.tool(name="format_range")(formatting.format_range)
mcp.tool(name="number_format")(formatting.number_format)
mcp.tool(name="conditional_format_add")(formatting.conditional_format_add)
mcp.tool(name="conditional_format_clear")(formatting.conditional_format_clear)
mcp.tool(name="autofit")(formatting.autofit)
mcp.tool(name="freeze_panes")(formatting.freeze_panes)

mcp.tool(name="data_validation_add")(validation.data_validation_add)
mcp.tool(name="duplicates_find")(validation.duplicates_find)
mcp.tool(name="trim_clean_range")(validation.trim_clean_range)

mcp.tool(name="name_define")(names.name_define)
mcp.tool(name="name_list")(names.name_list)
mcp.tool(name="comment_add")(names.comment_add)

mcp.tool(name="sheet_sql")(analysis.sheet_sql)
mcp.tool(name="sheet_profile")(analysis.sheet_profile)

mcp.tool(name="script_run_typescript")(scripts.script_run_typescript)
mcp.tool(name="vba_run")(scripts.vba_run)

mcp.tool(name="view_select")(view.view_select)
mcp.tool(name="view_highlight")(view.view_highlight)
mcp.tool(name="view_screenshot")(view.view_screenshot)

mcp.tool(name="snapshot_restore")(snapshots.snapshot_restore)
mcp.tool(name="snapshot_info")(snapshots.snapshot_info)

# Skill tool subsets (maximum 12 tools per skill for high accuracy)
SKILL_TOOL_SUBSETS: dict[str, set[str]] = {
    "analyze": {
        "workbook_info",
        "workbook_schema_cards",
        "sheet_profile",
        "sheet_sql",
        "formula_explain",
        "formula_evaluate",
        "formula_audit_sheet",
        "view_screenshot",
    },
    "edit_values": {
        "range_read",
        "range_write_values",
        "range_clear",
        "range_fill_down",
        "trim_clean_range",
        "duplicates_find",
        "snapshot_restore",
    },
    "formula": {
        "range_read",
        "formula_explain",
        "formula_evaluate",
        "range_write_formulas",
        "name_define",
    },
    "format": {
        "format_range",
        "number_format",
        "conditional_format_add",
        "conditional_format_clear",
        "autofit",
        "freeze_panes",
    },
    "pivot_or_chart": {
        "table_create",
        "table_list",
        "pivot_create",
        "pivot_list",
        "chart_create",
        "chart_list",
        "slicer_add",
        "view_screenshot",
    },
    "dashboard": {
        "sheet_add",
        "table_create",
        "pivot_create",
        "chart_create",
        "slicer_add",
        "format_range",
        "name_define",
        "view_screenshot",
    },
    "script": {
        "script_run_typescript",
        "range_read",
        "workbook_schema_cards",
    },
    "question_only": set(),
}
