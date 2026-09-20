from typing import Any

from excelpilot.bridge.router import router


async def workbook_info() -> dict[str, Any]:
    """Get metadata about the active workbook including sheet names and calculation mode."""
    info = await router.workbook_info()
    return info.model_dump()


async def workbook_schema_cards() -> list[dict[str, Any]]:
    """Return compact schema summary cards for all sheets in the workbook."""
    sheets = await router.list_sheets()
    cards: list[dict[str, Any]] = []

    for s in sheets:
        try:
            used = await router.used_range(s.name)
            used_addr = used.address
        except Exception:
            used_addr = "A1"

        tables = await router.list_tables(s.name)
        pivots = await router.list_pivots(s.name)
        charts = await router.list_charts(s.name)

        cards.append(
            {
                "sheet": s.name,
                "used_range": used_addr,
                "row_count": s.row_count,
                "column_count": s.column_count,
                "visibility": s.visibility,
                "tables": [t.get("name") for t in tables],
                "pivots": [p.get("name") for p in pivots],
                "charts": [c.get("name") for c in charts],
            }
        )

    return cards
