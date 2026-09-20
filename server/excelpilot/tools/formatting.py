from typing import Any

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router


def _as_dict(value: Any) -> dict[str, Any] | None:
    if value is None or value == "" or value == {}:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("#") or s.lower() in {"yellow", "red", "green", "blue", "orange", "grey", "gray"}:
            return {"color": s}
        if s.lower() in {"bold", "italic", "underline"}:
            return {s.lower(): True}
    return None


async def format_range(
    sheet: str,
    address: str,
    font: Any = None,
    fill: Any = None,
    borders: Any = None,
    alignment: Any = None,
) -> dict[str, Any]:
    """Apply font, fill, borders, and alignment. Nested objects may be omitted.
    Hex strings in fill are treated as fill.color. Never raises — returns {success, error}."""
    try:
        ref = RangeRef(sheet=sheet, address=address)
        ok = await router.format(
            ref,
            font=_as_dict(font),
            fill=_as_dict(fill),
            borders=_as_dict(borders),
            alignment=_as_dict(alignment),
        )
        return {"success": bool(ok), "address": address}
    except Exception as err:
        return {"success": False, "error": str(err), "address": address}


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
