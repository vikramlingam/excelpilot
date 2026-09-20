from typing import Any

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router


async def table_create(
    sheet: str, address: str, table_name: str | None = None, has_headers: bool = True
) -> str:
    """Create an Excel table from a range. Reuses the table if that name already exists."""
    ref = RangeRef(sheet=sheet, address=address)
    try:
        return await router.create_table(ref, name=table_name, has_headers=has_headers)
    except Exception as err:
        msg = str(err)
        if table_name and ("already exists" in msg.lower() or "ItemAlreadyExists" in msg):
            return table_name
        raise


async def table_list(sheet: str | None = None) -> list[dict[str, Any]]:
    """List all structured tables in the workbook or on a specific sheet."""
    return await router.list_tables(sheet)


async def table_add_column(
    sheet: str, table_name: str, column_name: str, formula: str | None = None
) -> dict[str, Any]:
    """Add a column to an Excel table; `formula` (e.g. '=[@Sales]-[@Cost]') fills every row."""
    router.check_capability("tables")
    return await router.officejs_bridge._rpc(
        "bridge.table.add_column",
        {"sheet": sheet, "table": table_name, "column": column_name, "formula": formula},
    )
