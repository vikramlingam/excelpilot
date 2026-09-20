from typing import Any

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router


async def data_validation_add(
    sheet: str, address: str, validation_type: str, formula1: str
) -> bool:
    """Add data validation rule (e.g. list, whole number range, date) to cells."""
    ref = RangeRef(sheet=sheet, address=address)
    rule = {"type": validation_type, "formula1": formula1}
    return await router.data_validation_add(ref, rule)


async def duplicates_find(
    sheet: str, address: str, column_index: int = 0
) -> list[Any]:
    """Find duplicate values within a column range."""
    ref = RangeRef(sheet=sheet, address=address)
    page = await router.read(ref, values=True)
    if not page.values:
        return []

    seen = set()
    duplicates = set()
    for row in page.values:
        if len(row) > column_index:
            val = row[column_index]
            if val is not None and val != "":
                if val in seen:
                    duplicates.add(val)
                else:
                    seen.add(val)
    return list(duplicates)


async def trim_clean_range(sheet: str, address: str) -> dict[str, Any]:
    """Trim leading and trailing whitespace and clean non-printable characters across range."""
    ref = RangeRef(sheet=sheet, address=address)
    page = await router.read(ref, values=True)
    if not page.values:
        return {"modified": 0}

    new_vals: list[list[Any]] = []
    mod_count = 0
    for row in page.values:
        new_row: list[Any] = []
        for cell in row:
            if isinstance(cell, str):
                cleaned = cell.strip()
                if cleaned != cell:
                    mod_count += 1
                new_row.append(cleaned)
            else:
                new_row.append(cell)
        new_vals.append(new_row)

    if mod_count > 0:
        await router.write(ref, values=new_vals)

    return {"modified": mod_count}
