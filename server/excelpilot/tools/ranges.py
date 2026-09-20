from typing import Any

from excelpilot.bridge.models import Page, RangeRef
from excelpilot.bridge.router import router


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
    res = await router.write(ref, values=values)
    return res.model_dump()


async def range_write_formulas(
    sheet: str, address: str, formulas: list[list[str]]
) -> dict[str, Any]:
    """Write a 2D array of formula strings to a worksheet range."""
    ref = RangeRef(sheet=sheet, address=address)
    res = await router.write(ref, formulas=formulas)
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
    res = await router.write(dst, values=data.values, formulas=data.formulas)
    return res.model_dump()
