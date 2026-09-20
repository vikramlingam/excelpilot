from typing import Any

from excelpilot.bridge.models import Page, RangeRef
from excelpilot.bridge.router import router


def as_grid(values: Any) -> list[list[Any]]:
    """Coerce model output into a rectangular 2-D array Excel will accept."""
    if values is None:
        return [[""]]
    if not isinstance(values, list):
        return [[values]]
    if not values:
        return [[""]]
    if not isinstance(values[0], list):
        return [list(values)]
    width = max((len(r) if isinstance(r, list) else 1) for r in values)
    grid: list[list[Any]] = []
    for row in values:
        cells = list(row) if isinstance(row, list) else [row]
        if len(cells) < width:
            cells = cells + [None] * (width - len(cells))
        grid.append(cells[:width])
    return grid


async def range_read(
    sheet: str,
    address: str,
    values: bool = True,
    formulas: bool = False,
    formats: bool = False,
    offset: int = 0,
    limit: int = 4000,
) -> dict[str, Any]:
    """Read cell values, formulas, or formats from a range with pagination."""
    ref = RangeRef(sheet=sheet, address=address)
    page = Page(offset=offset, limit=limit)
    res = await router.read(ref, values=values, formulas=formulas, formats=formats, page=page)
    return res.model_dump()


async def range_write_values(
    sheet: str, address: str, values: list[list[Any]]
) -> dict[str, Any]:
    """Write a 2D array of values to a worksheet range."""
    ref = RangeRef(sheet=sheet, address=address)
    res = await router.write(ref, values=as_grid(values))
    return res.model_dump()


async def range_write_formulas(
    sheet: str, address: str, formulas: list[list[str]]
) -> dict[str, Any]:
    """Write a 2D array of formula strings to a worksheet range."""
    ref = RangeRef(sheet=sheet, address=address)
    res = await router.write(ref, formulas=as_grid(formulas))
    return res.model_dump()


async def range_clear(sheet: str, address: str) -> bool:
    """Clear all contents and formatting in the specified range."""
    ref = RangeRef(sheet=sheet, address=address)
    return await router.clear(ref)


async def range_fill_down(
    sheet: str, source_address: str, target_address: str
) -> dict[str, Any]:
    """Copy formulas or values from source range down across target range."""
    src = RangeRef(sheet=sheet, address=source_address)
    data = await router.read(src, values=True, formulas=True)
    dst = RangeRef(sheet=sheet, address=target_address)
    formulas = as_grid(data.formulas)
    has_formula = any(
        isinstance(cell, str) and cell.startswith("=") for row in formulas for cell in row
    )
    if has_formula:
        res = await router.write(dst, formulas=formulas)
    else:
        res = await router.write(dst, values=as_grid(data.values))
    return res.model_dump()
