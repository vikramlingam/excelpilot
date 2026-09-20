from abc import ABC, abstractmethod
from typing import Any

from excelpilot.bridge.models import (
    Page,
    RangePage,
    RangeRef,
    ScriptResult,
    SheetInfo,
    WorkbookInfo,
    WriteResult,
)


class ExcelBridge(ABC):
    """Abstract base class for Excel bridges."""

    @property
    @abstractmethod
    def capabilities(self) -> set[str]:
        # Supported feature tags such as values, formulas, formatting, pivot, chart, script
        pass

    @abstractmethod
    async def workbook_info(self) -> WorkbookInfo:
        pass

    @abstractmethod
    async def list_sheets(self) -> list[SheetInfo]:
        pass

    @abstractmethod
    async def used_range(self, sheet: str) -> RangeRef:
        pass

    @abstractmethod
    async def add_sheet(self, name: str | None = None) -> SheetInfo:
        pass

    @abstractmethod
    async def rename_sheet(self, old_name: str, new_name: str) -> SheetInfo:
        pass

    @abstractmethod
    async def delete_sheet(self, name: str) -> bool:
        pass

    @abstractmethod
    async def set_sheet_visibility(self, name: str, visible: bool) -> bool:
        pass

    @abstractmethod
    async def read(
        self,
        ref: RangeRef,
        values: bool = True,
        formulas: bool = False,
        formats: bool = False,
        page: Page | None = None,
    ) -> RangePage:
        pass

    @abstractmethod
    async def write(
        self,
        ref: RangeRef,
        values: list[list[Any]] | None = None,
        formulas: list[list[Any]] | None = None,
    ) -> WriteResult:
        pass

    @abstractmethod
    async def clear(self, ref: RangeRef) -> bool:
        pass

    @abstractmethod
    async def create_table(
        self, ref: RangeRef, name: str | None = None, has_headers: bool = True
    ) -> str:
        pass

    @abstractmethod
    async def list_tables(self, sheet: str | None = None) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def create_pivot(self, source: RangeRef, dest: RangeRef, name: str) -> str:
        pass

    @abstractmethod
    async def list_pivots(self, sheet: str | None = None) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def create_chart(
        self, type_: str, source: RangeRef, position: str, title: str
    ) -> str:
        pass

    @abstractmethod
    async def list_charts(self, sheet: str | None = None) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def format(
        self,
        ref: RangeRef,
        font: dict[str, Any] | None = None,
        fill: dict[str, Any] | None = None,
        borders: dict[str, Any] | None = None,
        alignment: dict[str, Any] | None = None,
    ) -> bool:
        pass

    @abstractmethod
    async def number_format(self, ref: RangeRef, format_code: str) -> bool:
        pass

    @abstractmethod
    async def conditional_format_add(
        self, ref: RangeRef, rule: dict[str, Any]
    ) -> str:
        pass

    @abstractmethod
    async def conditional_format_clear(self, ref: RangeRef) -> bool:
        pass

    @abstractmethod
    async def autofit(self, ref: RangeRef) -> bool:
        pass

    @abstractmethod
    async def freeze_panes(self, sheet: str, row: int, col: int) -> bool:
        pass

    @abstractmethod
    async def define_name(self, name: str, ref: RangeRef) -> bool:
        pass

    @abstractmethod
    async def list_names(self) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def data_validation_add(self, ref: RangeRef, rule: dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def add_comment(self, sheet: str, cell: str, text: str) -> bool:
        pass

    @abstractmethod
    async def select(self, ref: RangeRef) -> bool:
        pass

    @abstractmethod
    async def highlight(self, ref: RangeRef, color: str = "#FFF2B2", ttl_s: int = 3) -> bool:
        pass

    @abstractmethod
    async def screenshot(self, ref_or_sheet: str) -> bytes | None:
        pass

    @abstractmethod
    async def run_script(
        self, code: str, args: dict[str, Any] | None = None
    ) -> ScriptResult:
        pass

    @abstractmethod
    async def snapshot(self, ref: RangeRef) -> str:
        pass

    @abstractmethod
    async def restore(self, snapshot_id: str) -> bool:
        pass
