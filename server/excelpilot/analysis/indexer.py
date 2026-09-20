from typing import Any

from pydantic import BaseModel, Field

from excelpilot.bridge.router import router


class SheetIndex(BaseModel):
    name: str
    used_range: str
    row_count: int
    column_count: int
    visibility: str
    tables: list[dict[str, Any]] = Field(default_factory=list)
    pivots: list[dict[str, Any]] = Field(default_factory=list)
    charts: list[dict[str, Any]] = Field(default_factory=list)


class WorkbookIndex(BaseModel):
    workbook_name: str
    sheet_count: int
    sheets: list[SheetIndex]
    named_ranges: list[dict[str, Any]] = Field(default_factory=list)


async def index_workbook() -> WorkbookIndex:
    """Build a comprehensive structural index of all worksheets, tables, and objects."""
    wb_info = await router.workbook_info()
    sheet_indices: list[SheetIndex] = []

    for s in wb_info.sheets:
        try:
            used = await router.used_range(s.name)
            used_addr = used.address
        except Exception:
            used_addr = "A1"

        tables = await router.list_tables(s.name)
        pivots = await router.list_pivots(s.name)
        charts = await router.list_charts(s.name)

        sheet_indices.append(
            SheetIndex(
                name=s.name,
                used_range=used_addr,
                row_count=s.row_count,
                column_count=s.column_count,
                visibility=s.visibility,
                tables=tables,
                pivots=pivots,
                charts=charts,
            )
        )

    names = await router.list_names()

    return WorkbookIndex(
        workbook_name=wb_info.name,
        sheet_count=len(sheet_indices),
        sheets=sheet_indices,
        named_ranges=names,
    )
