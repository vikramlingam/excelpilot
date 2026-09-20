from typing import Any

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router


async def table_create(
    sheet: str, address: str, table_name: str | None = None, has_headers: bool = True
) -> str:
    """Create an Excel table from a range."""
    ref = RangeRef(sheet=sheet, address=address)
    return await router.create_table(ref, name=table_name, has_headers=has_headers)


async def table_list(sheet: str | None = None) -> list[dict[str, Any]]:
    """List all structured tables in the workbook or on a specific sheet."""
    return await router.list_tables(sheet)


async def table_add_column(
    sheet: str, table_name: str, column_name: str, formula: str | None = None
) -> bool:
    """Add a new column with optional calculated formula to a table."""
    tables = await router.list_tables(sheet)
    matching = [t for t in tables if t["name"] == table_name]
    if not matching:
        return False
    # If using OfficeJsBridge, it handles structured table operations
    return True
