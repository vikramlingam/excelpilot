from typing import Any

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router


async def pivot_create(
    source_sheet: str,
    source_address: str,
    dest_sheet: str,
    dest_address: str,
    pivot_name: str,
    row_fields: list[str] | None = None,
    value_fields: list[str] | None = None,
    column_fields: list[str] | None = None,
    aggregation: str = "sum",
) -> dict[str, Any]:
    """Create a complete PivotTable in ONE call. source_address must include the header row.
    row_fields/value_fields/column_fields are header names from the source. Use this instead of
    separate add-field calls."""
    router.check_capability("pivot")
    try:
        res = await router.officejs_bridge._rpc(
            "bridge.pivot.create",
            {
                "source_sheet": source_sheet,
                "source_address": source_address,
                "dest_sheet": dest_sheet,
                "dest_cell": dest_address,
                "name": pivot_name,
                "rows": row_fields or [],
                "values": value_fields or [],
                "columns": column_fields or [],
                "aggregation": aggregation,
            },
        )
        return res if isinstance(res, dict) else {"name": pivot_name}
    except Exception as err:
        msg = str(err)
        if "already exists" in msg.lower() or "ItemAlreadyExists" in msg:
            return {"name": pivot_name, "existed": True}
        raise


async def pivot_list(sheet: str | None = None) -> list[dict[str, Any]]:
    """List all PivotTables on a specific sheet."""
    return await router.list_pivots(sheet)


async def pivot_add_row_field(pivot_name: str, field_name: str, sheet: str) -> dict[str, Any]:
    """Add a row field to an existing PivotTable on `sheet`."""
    router.check_capability("pivot")
    return await router.officejs_bridge._rpc(
        "bridge.pivot.add_field",
        {"sheet": sheet, "name": pivot_name, "field": field_name, "area": "row"},
    )


async def pivot_add_value(
    pivot_name: str, field_name: str, sheet: str, aggregation: str = "sum"
) -> dict[str, Any]:
    """Add a value (data) field with aggregation (sum, count, average, max, min) to an existing PivotTable."""
    router.check_capability("pivot")
    return await router.officejs_bridge._rpc(
        "bridge.pivot.add_field",
        {"sheet": sheet, "name": pivot_name, "field": field_name, "area": "value", "aggregation": aggregation},
    )


async def pivot_refresh(pivot_name: str, sheet: str) -> dict[str, Any]:
    """Refresh a PivotTable on `sheet`."""
    router.check_capability("pivot")
    return await router.officejs_bridge._rpc("bridge.pivot.refresh", {"sheet": sheet, "name": pivot_name})
