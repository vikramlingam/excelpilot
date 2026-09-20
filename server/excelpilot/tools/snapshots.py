from typing import Any

from excelpilot.bridge.router import router
from excelpilot.store.db import store


async def snapshot_restore(snapshot_id: str) -> bool:
    """Restore workbook cells to a previously saved snapshot state."""
    return await router.restore(snapshot_id)


async def snapshot_info(snapshot_id: str) -> dict[str, Any] | None:
    """Retrieve details about a saved snapshot."""
    snap = store.get_snapshot(snapshot_id)
    if not snap:
        return None
    return {
        "id": snap["id"],
        "sheet": snap["sheet"],
        "address": snap["address"],
        "created_at": str(snap["created_at"]),
    }
