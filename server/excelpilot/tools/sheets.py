from typing import Any

from excelpilot.bridge.router import router


async def sheet_list() -> list[dict[str, Any]]:
    """List all worksheets in the current workbook."""
    sheets = await router.list_sheets()
    return [s.model_dump() for s in sheets]


async def sheet_add(name: str | None = None) -> dict[str, Any]:
    """Add a new worksheet to the workbook."""
    sheet = await router.add_sheet(name)
    return sheet.model_dump()


async def sheet_rename(old_name: str, new_name: str) -> dict[str, Any]:
    """Rename an existing worksheet."""
    sheet = await router.rename_sheet(old_name, new_name)
    return sheet.model_dump()


async def sheet_delete(sheet_name: str) -> bool:
    """Delete a worksheet from the workbook."""
    return await router.delete_sheet(sheet_name)


async def sheet_set_visibility(sheet_name: str, visible: bool) -> bool:
    """Set worksheet visibility."""
    return await router.set_sheet_visibility(sheet_name, visible)
