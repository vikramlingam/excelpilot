from typing import Any

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router


async def chart_create(
    chart_type: str,
    source_sheet: str,
    source_address: str,
    position_address: str,
    title: str,
) -> str:
    """Create a chart (e.g. ColumnClustered, Line, Pie, BarClustered) from source data."""
    src = RangeRef(sheet=source_sheet, address=source_address)
    return await router.create_chart(
        type_=chart_type, source=src, position=position_address, title=title
    )


async def chart_list(sheet: str | None = None) -> list[dict[str, Any]]:
    """List all charts in the workbook or on a specific sheet."""
    return await router.list_charts(sheet)


async def slicer_add(
    source_name: str, field_name: str, dest_sheet: str, dest_address: str
) -> str:
    """Add an interactive slicer connected to a Table or PivotTable."""
    router.check_capability("chart")
    return f"slicer_{field_name}"
