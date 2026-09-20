from typing import Any

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router


async def chart_create(
    chart_type: str,
    source_sheet: str,
    source_address: str,
    title: str,
    dest_sheet: str | None = None,
    position_address: str | None = None,
) -> dict[str, Any]:
    """Create a chart from source data (include header row). chart_type: ColumnClustered, BarClustered,
    Line, Pie, Doughnut, XYScatter, Area. dest_sheet/position_address place it (default: next to the data)."""
    router.check_capability("chart")
    return await router.officejs_bridge._rpc(
        "bridge.chart.create",
        {
            "type": chart_type,
            "source_sheet": source_sheet,
            "source_address": source_address,
            "dest_sheet": dest_sheet or source_sheet,
            "position": position_address,
            "title": title,
        },
    )


async def chart_list(sheet: str | None = None) -> list[dict[str, Any]]:
    """List all charts on a specific sheet."""
    return await router.list_charts(sheet)


async def slicer_add(
    source_name: str, field_name: str, dest_sheet: str, dest_address: str, source_sheet: str
) -> dict[str, Any]:
    """Add a slicer for `field_name` connected to a Table or PivotTable named `source_name` on `source_sheet`."""
    router.check_capability("chart")
    return await router.officejs_bridge._rpc(
        "bridge.slicer.add",
        {
            "source_sheet": source_sheet,
            "source_name": source_name,
            "field": field_name,
            "dest_sheet": dest_sheet,
            "dest_cell": dest_address,
        },
    )
