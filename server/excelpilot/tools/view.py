import base64

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router


async def view_select(sheet: str, address: str) -> bool:
    """Select a cell or range in Excel to bring it into the user's viewport."""
    ref = RangeRef(sheet=sheet, address=address)
    return await router.select(ref)


async def view_highlight(
    sheet: str, address: str, color: str = "#FFF2B2", duration_seconds: int = 3
) -> bool:
    """Temporarily highlight a range in Excel with a soft color."""
    ref = RangeRef(sheet=sheet, address=address)
    return await router.highlight(ref, color=color, ttl_s=duration_seconds)


async def view_screenshot(sheet_or_range: str) -> str | None:
    """Capture a screenshot of a range or worksheet and return base64 encoded PNG data."""
    img_bytes = await router.screenshot(sheet_or_range)
    if img_bytes:
        return base64.b64encode(img_bytes).decode("utf-8")
    return None
