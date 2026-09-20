from typing import Any

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router


async def format_range(
    sheet: str,
    address: str,
    font: dict[str, Any] | None = None,
    fill: dict[str, Any] | None = None,
    borders: dict[str, Any] | None = None,
    alignment: dict[str, Any] | None = None,
) -> bool:
    """Apply font, fill color, borders, and alignment to a range."""
    ref = RangeRef(sheet=sheet, address=address)
    return await router.format(ref, font=font, fill=fill, borders=borders, alignment=alignment)


async def number_format(sheet: str, address: str, format_code: str) -> bool:
    """Apply standard Excel number format code (e.g. '$#,##0.00', '0.0%') to a range."""
    ref = RangeRef(sheet=sheet, address=address)
    return await router.number_format(ref, format_code=format_code)


async def conditional_format_add(
    sheet: str, address: str, rule: dict[str, Any]
) -> str:
    """Add a conditional formatting rule (e.g. color scale, highlight negatives, data bars)."""
    ref = RangeRef(sheet=sheet, address=address)
    return await router.conditional_format_add(ref, rule)


async def conditional_format_clear(sheet: str, address: str) -> bool:
    """Clear all conditional formatting rules from a range."""
    ref = RangeRef(sheet=sheet, address=address)
    return await router.conditional_format_clear(ref)


async def autofit(sheet: str, address: str) -> bool:
    """Autofit columns and rows for the specified range."""
    ref = RangeRef(sheet=sheet, address=address)
    return await router.autofit(ref)


async def freeze_panes(sheet: str, row: int, col: int) -> bool:
    """Freeze panes at the specified row and column indices."""
    return await router.freeze_panes(sheet, row, col)
