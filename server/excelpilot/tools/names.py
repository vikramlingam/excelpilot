from typing import Any

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router


async def name_define(name: str, sheet: str, address: str) -> bool:
    """Define or update a workbook named range."""
    ref = RangeRef(sheet=sheet, address=address)
    return await router.define_name(name, ref)


async def name_list() -> list[dict[str, Any]]:
    """List all defined named ranges in the workbook."""
    return await router.list_names()


async def comment_add(sheet: str, cell: str, comment_text: str) -> bool:
    """Add a threaded comment or note to a cell."""
    return await router.add_comment(sheet, cell, comment_text)
