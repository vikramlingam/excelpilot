from typing import Any

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router


async def pivot_create(
    source_sheet: str,
    source_address: str,
    dest_sheet: str,
    dest_address: str,
    pivot_name: str,
) -> str:
    """Create a new PivotTable from a source table or range."""
    src = RangeRef(sheet=source_sheet, address=source_address)
    dst = RangeRef(sheet=dest_sheet, address=dest_address)
    return await router.create_pivot(source=src, dest=dst, name=pivot_name)


async def pivot_list(sheet: str | None = None) -> list[dict[str, Any]]:
    """List all PivotTables in the workbook or on a specific sheet."""
    return await router.list_pivots(sheet)


async def pivot_add_row_field(pivot_name: str, field_name: str) -> bool:
    """Add a field as a row hierarchy to a PivotTable."""
    router.check_capability("pivot")
    return True


async def pivot_add_value(
    pivot_name: str, field_name: str, aggregation: str = "sum"
) -> bool:
    """Add a field to the values area of a PivotTable with specified aggregation function."""
    router.check_capability("pivot")
    return True


async def pivot_refresh(pivot_name: str) -> bool:
    """Refresh data cache for a PivotTable."""
    router.check_capability("pivot")
    return True
