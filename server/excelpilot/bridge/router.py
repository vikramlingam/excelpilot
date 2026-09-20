from typing import Any

from excelpilot.bridge.base import ExcelBridge
from excelpilot.bridge.file import FileBridge
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
from excelpilot.bridge.officejs import OfficeJsBridge
from excelpilot.bridge.xlwings_ import XlwingsBridge
from excelpilot.config import settings


class BridgeRouter(ExcelBridge):
    """Router that selects the best active Excel bridge based on preference and connection."""

    def __init__(self, default_file_path: str | None = None) -> None:
        self.officejs_bridge = OfficeJsBridge()
        self.xlwings_bridge = XlwingsBridge()
        self.file_bridge = FileBridge(file_path=default_file_path)

    @property
    def active_bridge(self) -> ExcelBridge:
        prefs = [p.strip().lower() for p in settings.excelpilot_bridge_preference.split(",")]
        for pref in prefs:
            if pref == "officejs" and self.officejs_bridge.is_connected:
                return self.officejs_bridge
            if pref == "xlwings" and self.xlwings_bridge.is_available:
                return self.xlwings_bridge
            if pref == "file":
                return self.file_bridge
        return self.file_bridge

    @property
    def capabilities(self) -> set[str]:
        return self.active_bridge.capabilities

    def check_capability(self, cap: str) -> None:
        if cap not in self.capabilities:
            raise BridgeError(
                "ApiNotSupported",
                f"Active bridge does not support '{cap}'. Connect Office.js add-in for full support.",
            )

    async def workbook_info(self) -> WorkbookInfo:
        return await self.active_bridge.workbook_info()

    async def list_sheets(self) -> list[SheetInfo]:
        return await self.active_bridge.list_sheets()

    async def used_range(self, sheet: str) -> RangeRef:
        return await self.active_bridge.used_range(sheet)

    async def add_sheet(self, name: str | None = None) -> SheetInfo:
        return await self.active_bridge.add_sheet(name)

    async def rename_sheet(self, old_name: str, new_name: str) -> SheetInfo:
        return await self.active_bridge.rename_sheet(old_name, new_name)

    async def delete_sheet(self, name: str) -> bool:
        return await self.active_bridge.delete_sheet(name)

    async def reset_workbook(self, keep_name: str = "Sheet1") -> dict[str, Any]:
        bridge = self.active_bridge
        fn = getattr(bridge, "reset_workbook", None)
        if fn is None:
            raise BridgeError("ApiNotSupported", "Active bridge cannot reset the workbook.")
        return await fn(keep_name)

    async def set_sheet_visibility(self, name: str, visible: bool) -> bool:
        return await self.active_bridge.set_sheet_visibility(name, visible)

    async def read(
        self,
        ref: RangeRef,
        values: bool = True,
        formulas: bool = False,
        formats: bool = False,
        page: Page | None = None,
    ) -> RangePage:
        return await self.active_bridge.read(ref, values, formulas, formats, page)

    async def write(
        self,
        ref: RangeRef,
        values: list[list[Any]] | None = None,
        formulas: list[list[Any]] | None = None,
    ) -> WriteResult:
        return await self.active_bridge.write(ref, values, formulas)

    async def clear(self, ref: RangeRef) -> bool:
        return await self.active_bridge.clear(ref)

    async def create_table(
        self, ref: RangeRef, name: str | None = None, has_headers: bool = True
    ) -> str:
        return await self.active_bridge.create_table(ref, name, has_headers)

    async def list_tables(self, sheet: str | None = None) -> list[dict[str, Any]]:
        return await self.active_bridge.list_tables(sheet)

    async def create_pivot(self, source: RangeRef, dest: RangeRef, name: str) -> str:
        self.check_capability("pivot")
        return await self.active_bridge.create_pivot(source, dest, name)

    async def list_pivots(self, sheet: str | None = None) -> list[dict[str, Any]]:
        return await self.active_bridge.list_pivots(sheet)

    async def create_chart(
        self, type_: str, source: RangeRef, position: str, title: str
    ) -> str:
        self.check_capability("chart")
        return await self.active_bridge.create_chart(type_, source, position, title)

    async def list_charts(self, sheet: str | None = None) -> list[dict[str, Any]]:
        return await self.active_bridge.list_charts(sheet)

    async def format(
        self,
        ref: RangeRef,
        font: dict[str, Any] | None = None,
        fill: dict[str, Any] | None = None,
        borders: dict[str, Any] | None = None,
        alignment: dict[str, Any] | None = None,
    ) -> bool:
        return await self.active_bridge.format(ref, font, fill, borders, alignment)

    async def number_format(self, ref: RangeRef, format_code: str) -> bool:
        return await self.active_bridge.number_format(ref, format_code)

    async def conditional_format_add(self, ref: RangeRef, rule: dict[str, Any]) -> str:
        return await self.active_bridge.conditional_format_add(ref, rule)

    async def conditional_format_clear(self, ref: RangeRef) -> bool:
        return await self.active_bridge.conditional_format_clear(ref)

    async def autofit(self, ref: RangeRef) -> bool:
        return await self.active_bridge.autofit(ref)

    async def freeze_panes(self, sheet: str, row: int, col: int) -> bool:
        return await self.active_bridge.freeze_panes(sheet, row, col)

    async def define_name(self, name: str, ref: RangeRef) -> bool:
        return await self.active_bridge.define_name(name, ref)

    async def list_names(self) -> list[dict[str, Any]]:
        return await self.active_bridge.list_names()

    async def data_validation_add(self, ref: RangeRef, rule: dict[str, Any]) -> bool:
        return await self.active_bridge.data_validation_add(ref, rule)

    async def add_comment(self, sheet: str, cell: str, text: str) -> bool:
        return await self.active_bridge.add_comment(sheet, cell, text)

    async def select(self, ref: RangeRef) -> bool:
        return await self.active_bridge.select(ref)

    async def highlight(self, ref: RangeRef, color: str = "#FFF2B2", ttl_s: int = 3) -> bool:
        return await self.active_bridge.highlight(ref, color, ttl_s)

    async def screenshot(self, ref_or_sheet: str) -> bytes | None:
        return await self.active_bridge.screenshot(ref_or_sheet)

    async def run_script(
        self, code: str, args: dict[str, Any] | None = None
    ) -> ScriptResult:
        self.check_capability("script")
        return await self.active_bridge.run_script(code, args)

    async def snapshot(self, ref: RangeRef) -> str:
        return await self.active_bridge.snapshot(ref)

    async def restore(self, snapshot_id: str) -> bool:
        return await self.active_bridge.restore(snapshot_id)


# Global default bridge router
router = BridgeRouter()
