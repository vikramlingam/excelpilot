import asyncio
import json
from typing import Any

from excelpilot.bridge.base import ExcelBridge
from excelpilot.bridge.models import (
    BridgeError,
    Page,
    RangePage,
    RangeRef,
    ScriptResult,
    SheetInfo,
    WorkbookInfo,
    WriteResult,
)


class OfficeJsBridge(ExcelBridge):
    """Bridge communicating with the Office.js add-in over WebSocket JSON-RPC."""

    def __init__(self, ws: Any | None = None) -> None:
        self._ws = ws
        self._msg_id = 0
        self._pending: dict[int, asyncio.Future[Any]] = {}

    def set_websocket(self, ws: Any) -> None:
        self._ws = ws

    @property
    def is_connected(self) -> bool:
        return self._ws is not None

    @property
    def capabilities(self) -> set[str]:
        return {
            "values",
            "formulas",
            "formatting",
            "tables",
            "pivot",
            "chart",
            "validation",
            "names",
            "comments",
            "screenshot",
            "script",
            "snapshots",
        }

    async def _rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if not self._ws:
            raise BridgeError("BridgeDisconnected", "Office.js add-in is not connected.")

        self._msg_id += 1
        call_id = self._msg_id
        payload = {
            "jsonrpc": "2.0",
            "id": call_id,
            "method": method,
            "params": params or {},
        }

        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._pending[call_id] = future

        await self._ws.send_text(json.dumps(payload))

        try:
            timeout = 120.0 if "script" in method or "screenshot" in method else 30.0
            return await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError:
            self._pending.pop(call_id, None)
            raise BridgeError("Timeout", f"Timeout waiting for add-in RPC {method}")

    def handle_incoming_rpc_response(self, data: dict[str, Any]) -> None:
        call_id = data.get("id")
        if call_id in self._pending:
            fut = self._pending.pop(call_id)
            if "error" in data:
                err = data["error"]
                fut.set_exception(
                    BridgeError(
                        err.get("code", "RpcError"),
                        err.get("message", "Add-in error"),
                        err.get("requirementSet"),
                    )
                )
            else:
                fut.set_result(data.get("result"))

    async def workbook_info(self) -> WorkbookInfo:
        res = await self._rpc("bridge.workbook.info")
        return WorkbookInfo(**res)

    async def list_sheets(self) -> list[SheetInfo]:
        res = await self._rpc("bridge.sheet.list")
        return [SheetInfo(**s) for s in res]

    async def used_range(self, sheet: str) -> RangeRef:
        res = await self._rpc("bridge.sheet.used_range", {"sheet": sheet})
        return RangeRef(sheet=sheet, address=res["address"])

    async def add_sheet(self, name: str | None = None) -> SheetInfo:
        res = await self._rpc("bridge.sheet.add", {"name": name})
        return SheetInfo(**res)

    async def rename_sheet(self, old_name: str, new_name: str) -> SheetInfo:
        res = await self._rpc("bridge.sheet.rename", {"old_name": old_name, "new_name": new_name})
        return SheetInfo(**res)

    async def delete_sheet(self, name: str) -> bool:
        res = await self._rpc("bridge.sheet.delete", {"sheet": name})
        return bool(res.get("success", False))

    async def set_sheet_visibility(self, name: str, visible: bool) -> bool:
        res = await self._rpc("bridge.sheet.set_visibility", {"sheet": name, "visible": visible})
        return bool(res.get("success", False))

    async def read(
        self,
        ref: RangeRef,
        values: bool = True,
        formulas: bool = False,
        formats: bool = False,
        page: Page | None = None,
    ) -> RangePage:
        params = {
            "sheet": ref.sheet,
            "address": ref.address,
            "values": values,
            "formulas": formulas,
            "formats": formats,
            "page": page.model_dump() if page else None,
        }
        res = await self._rpc("bridge.range.read", params)
        return RangePage(**res)

    async def write(
        self,
        ref: RangeRef,
        values: list[list[Any]] | None = None,
        formulas: list[list[Any]] | None = None,
    ) -> WriteResult:
        params = {
            "sheet": ref.sheet,
            "address": ref.address,
            "values": values,
            "formulas": formulas,
        }
        res = await self._rpc("bridge.range.write", params)
        return WriteResult(**res)

    async def clear(self, ref: RangeRef) -> bool:
        res = await self._rpc("bridge.range.clear", {"sheet": ref.sheet, "address": ref.address})
        return bool(res.get("success", False))

    async def create_table(
        self, ref: RangeRef, name: str | None = None, has_headers: bool = True
    ) -> str:
        params = {
            "sheet": ref.sheet,
            "address": ref.address,
            "name": name,
            "has_headers": has_headers,
        }
        res = await self._rpc("bridge.table.create", params)
        return str(res.get("name", ""))

    async def list_tables(self, sheet: str | None = None) -> list[dict[str, Any]]:
        return await self._rpc("bridge.table.list", {"sheet": sheet})

    async def create_pivot(self, source: RangeRef, dest: RangeRef, name: str) -> str:
        params = {
            "source_sheet": source.sheet,
            "source_address": source.address,
            "dest_sheet": dest.sheet,
            "dest_address": dest.address,
            "name": name,
        }
        res = await self._rpc("bridge.pivot.create", params)
        return str(res.get("name", name))

    async def list_pivots(self, sheet: str | None = None) -> list[dict[str, Any]]:
        return await self._rpc("bridge.pivot.list", {"sheet": sheet})

    async def create_chart(
        self, type_: str, source: RangeRef, position: str, title: str
    ) -> str:
        params = {
            "type": type_,
            "source_sheet": source.sheet,
            "source_address": source.address,
            "position": position,
            "title": title,
        }
        res = await self._rpc("bridge.chart.create", params)
        return str(res.get("name", ""))

    async def list_charts(self, sheet: str | None = None) -> list[dict[str, Any]]:
        return await self._rpc("bridge.chart.list", {"sheet": sheet})

    async def format(
        self,
        ref: RangeRef,
        font: dict[str, Any] | None = None,
        fill: dict[str, Any] | None = None,
        borders: dict[str, Any] | None = None,
        alignment: dict[str, Any] | None = None,
    ) -> bool:
        params = {
            "sheet": ref.sheet,
            "address": ref.address,
            "font": font,
            "fill": fill,
            "borders": borders,
            "alignment": alignment,
        }
        res = await self._rpc("bridge.format.range", params)
        return bool(res.get("success", False))

    async def number_format(self, ref: RangeRef, format_code: str) -> bool:
        params = {"sheet": ref.sheet, "address": ref.address, "format": format_code}
        res = await self._rpc("bridge.format.number", params)
        return bool(res.get("success", False))

    async def conditional_format_add(self, ref: RangeRef, rule: dict[str, Any]) -> str:
        params = {"sheet": ref.sheet, "address": ref.address, "rule": rule}
        res = await self._rpc("bridge.format.conditional_add", params)
        return str(res.get("id", ""))

    async def conditional_format_clear(self, ref: RangeRef) -> bool:
        res = await self._rpc("bridge.format.conditional_clear", {"sheet": ref.sheet, "address": ref.address})
        return bool(res.get("success", False))

    async def autofit(self, ref: RangeRef) -> bool:
        res = await self._rpc("bridge.format.autofit", {"sheet": ref.sheet, "address": ref.address})
        return bool(res.get("success", False))

    async def freeze_panes(self, sheet: str, row: int, col: int) -> bool:
        res = await self._rpc("bridge.view.freeze_panes", {"sheet": sheet, "row": row, "col": col})
        return bool(res.get("success", False))

    async def define_name(self, name: str, ref: RangeRef) -> bool:
        res = await self._rpc("bridge.name.define", {"name": name, "sheet": ref.sheet, "address": ref.address})
        return bool(res.get("success", False))

    async def list_names(self) -> list[dict[str, Any]]:
        return await self._rpc("bridge.name.list")

    async def data_validation_add(self, ref: RangeRef, rule: dict[str, Any]) -> bool:
        params = {"sheet": ref.sheet, "address": ref.address, "rule": rule}
        res = await self._rpc("bridge.validation.add", params)
        return bool(res.get("success", False))

    async def add_comment(self, sheet: str, cell: str, text: str) -> bool:
        res = await self._rpc("bridge.comment.add", {"sheet": sheet, "cell": cell, "text": text})
        return bool(res.get("success", False))

    async def select(self, ref: RangeRef) -> bool:
        res = await self._rpc("bridge.view.select", {"sheet": ref.sheet, "address": ref.address})
        return bool(res.get("success", False))

    async def highlight(self, ref: RangeRef, color: str = "#FFF2B2", ttl_s: int = 3) -> bool:
        params = {"sheet": ref.sheet, "address": ref.address, "color": color, "ttl_s": ttl_s}
        res = await self._rpc("bridge.view.highlight", params)
        return bool(res.get("success", False))

    async def screenshot(self, ref_or_sheet: str) -> bytes | None:
        res = await self._rpc("bridge.view.screenshot", {"target": ref_or_sheet})
        if res and "image_bytes" in res:
            import base64

            return base64.b64decode(res["image_bytes"])
        return None

    async def run_script(
        self, code: str, args: dict[str, Any] | None = None
    ) -> ScriptResult:
        res = await self._rpc("bridge.script.run", {"code": code, "args": args or {}})
        return ScriptResult(**res)

    async def snapshot(self, ref: RangeRef) -> str:
        res = await self._rpc("bridge.snapshot.create", {"sheet": ref.sheet, "address": ref.address})
        return str(res.get("snapshot_id", ""))

    async def restore(self, snapshot_id: str) -> bool:
        res = await self._rpc("bridge.snapshot.restore", {"snapshot_id": snapshot_id})
        return bool(res.get("success", False))
