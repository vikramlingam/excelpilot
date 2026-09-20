from typing import Any

from excelpilot.bridge.router import router


async def sheet_list() -> list[dict[str, Any]]:
    """List all worksheets in the current workbook."""
    sheets = await router.list_sheets()
    return [s.model_dump() for s in sheets]


async def sheet_add(name: str | None = None) -> dict[str, Any]:
    """Add a new worksheet. If the name already exists, return that sheet instead of failing."""
    try:
        sheet = await router.add_sheet(name)
        data = sheet.model_dump()
        data.setdefault("existed", False)
        return data
    except Exception as err:
        msg = str(err)
        if name and ("already exists" in msg.lower() or "ItemAlreadyExists" in msg):
            return {"name": name, "existed": True}
        raise


async def sheet_rename(old_name: str, new_name: str) -> dict[str, Any]:
    """Rename an existing worksheet."""
    sheet = await router.rename_sheet(old_name, new_name)
    return sheet.model_dump()


async def sheet_delete(sheet_name: str) -> bool:
    """Delete a worksheet. Excel always keeps at least one sheet."""
    return await router.delete_sheet(sheet_name)


async def workbook_reset(keep_name: str = "Sheet1") -> dict[str, Any]:
    """Delete every worksheet except one blank sheet named `keep_name`.

    Use this when the user asks to delete all sheets / start over. Excel cannot
    have zero worksheets, so one empty sheet remains.
    """
    return await router.reset_workbook(keep_name)


async def sheet_set_visibility(sheet_name: str, visible: bool) -> bool:
    """Set worksheet visibility."""
    return await router.set_sheet_visibility(sheet_name, visible)
