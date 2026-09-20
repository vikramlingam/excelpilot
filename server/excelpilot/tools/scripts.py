from typing import Any

from excelpilot.bridge.router import router


async def script_run_typescript(
    code: str, args: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Execute generated Office.js TypeScript code inside the Excel task-pane sandbox."""
    res = await router.run_script(code, args)
    return res.model_dump()


async def vba_run(macro_name: str, args: list | None = None) -> Any:
    """Run an existing VBA macro via native desktop automation."""
    if hasattr(router.active_bridge, "run_vba"):
        return await router.active_bridge.run_vba(macro_name, *(args or []))
    return "VBA automation is only available when native Excel is active."
