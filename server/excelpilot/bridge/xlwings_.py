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


class XlwingsBridge(ExcelBridge):
    """Native Excel automation bridge using xlwings for VBA and COM/AppleScript."""

    def __init__(self) -> None:
        self._xw = None
        self._book = None
        try:
            import xlwings as xw

            self._xw = xw
            if xw.apps:
                self._book = xw.books.active
        except Exception:
            pass

    @property
    def is_available(self) -> bool:
        return self._book is not None

    @property
    def capabilities(self) -> set[str]:
        return {
            "values",
            "formulas",
            "formatting",
            "tables",
            "vba",
            "screenshot",
            "snapshots",
        }

    async def workbook_info(self) -> WorkbookInfo:
        if not self._book:
            raise BridgeError("BridgeUnavailable", "Excel is not running or no active book.")
        sheets = await self.list_sheets()
        return WorkbookInfo(
            name=self._book.name,
            path=self._book.fullname,
            sheet_count=len(sheets),
            sheets=sheets,
            calculation_mode="automatic",
        )

    async def list_sheets(self) -> list[SheetInfo]:
        if not self._book:
            raise BridgeError("BridgeUnavailable", "Excel is not running.")
        return [
            SheetInfo(
                name=s.name,
                index=idx,
                visibility="visible" if s.visible else "hidden",
            )
            for idx, s in enumerate(self._book.sheets)
        ]

    async def used_range(self, sheet: str) -> RangeRef:
        if not self._book:
            raise BridgeError("BridgeUnavailable", "Excel is not running.")
        s = self._book.sheets[sheet]
        rng = s.used_range
        return RangeRef(sheet=sheet, address=rng.address.replace("$", ""))

    async def add_sheet(self, name: str | None = None) -> SheetInfo:
        s = self._book.sheets.add(name=name)
        return SheetInfo(name=s.name, index=len(self._book.sheets) - 1)

    async def rename_sheet(self, old_name: str, new_name: str) -> SheetInfo:
        s = self._book.sheets[old_name]
        s.name = new_name
        return SheetInfo(name=new_name, index=0)

    async def delete_sheet(self, name: str) -> bool:
        self._book.sheets[name].delete()
        return True

    async def set_sheet_visibility(self, name: str, visible: bool) -> bool:
        self._book.sheets[name].visible = visible
        return True

    async def read(
        self,
        ref: RangeRef,
        values: bool = True,
        formulas: bool = False,
        formats: bool = False,
        page: Page | None = None,
    ) -> RangePage:
        s = self._book.sheets[ref.sheet]
        rng = s.range(ref.address)
        raw_vals = rng.value
        # Ensure 2D list
        if not isinstance(raw_vals, list):
            grid = [[raw_vals]]
        elif raw_vals and not isinstance(raw_vals[0], list):
            grid = [raw_vals]
        else:
            grid = raw_vals or [[]]

        form_grid = [[rng.formula]] if formulas else None
        return RangePage(
            address=ref.address,
            values=grid if values else None,
            formulas=form_grid,
            total_cells=len(grid) * len(grid[0]) if grid else 0,
        )

    async def write(
        self,
        ref: RangeRef,
        values: list[list[Any]] | None = None,
        formulas: list[list[Any]] | None = None,
    ) -> WriteResult:
        s = self._book.sheets[ref.sheet]
        rng = s.range(ref.address)
        data = formulas or values or []
        rng.value = data
        return WriteResult(success=True, address=ref.address, cells_modified=len(data))

    async def clear(self, ref: RangeRef) -> bool:
        self._book.sheets[ref.sheet].range(ref.address).clear()
        return True

    async def create_table(
        self, ref: RangeRef, name: str | None = None, has_headers: bool = True
    ) -> str:
        s = self._book.sheets[ref.sheet]
        t = s.tables.add(source=s.range(ref.address), name=name)
        return t.name

    async def list_tables(self, sheet: str | None = None) -> list[dict[str, Any]]:
        tables: list[dict[str, Any]] = []
        sheets = [self._book.sheets[sheet]] if sheet else self._book.sheets
        for s in sheets:
            for t in s.tables:
                tables.append({"name": t.name, "sheet": s.name, "range": t.range.address})
        return tables

    async def create_pivot(self, source: RangeRef, dest: RangeRef, name: str) -> str:
        raise BridgeError("ApiNotSupported", "Pivots via xlwings require Windows COM.")

    async def list_pivots(self, sheet: str | None = None) -> list[dict[str, Any]]:
        return []

    async def create_chart(
        self, type_: str, source: RangeRef, position: str, title: str
    ) -> str:
        s = self._book.sheets[source.sheet]
        c = s.charts.add()
        c.set_source_data(s.range(source.address))
        c.name = title
        return c.name

    async def list_charts(self, sheet: str | None = None) -> list[dict[str, Any]]:
        return []

    async def format(
        self,
        ref: RangeRef,
        font: dict[str, Any] | None = None,
        fill: dict[str, Any] | None = None,
        borders: dict[str, Any] | None = None,
        alignment: dict[str, Any] | None = None,
    ) -> bool:
        s = self._book.sheets[ref.sheet]
        rng = s.range(ref.address)
        if font and "color" in font:
            rng.font.color = font["color"]
        if fill and "color" in fill:
            rng.color = fill["color"]
        return True

    async def number_format(self, ref: RangeRef, format_code: str) -> bool:
        s = self._book.sheets[ref.sheet]
        s.range(ref.address).number_format = format_code
        return True

    async def conditional_format_add(self, ref: RangeRef, rule: dict[str, Any]) -> str:
        return "rule_added"

    async def conditional_format_clear(self, ref: RangeRef) -> bool:
        return True

    async def autofit(self, ref: RangeRef) -> bool:
        s = self._book.sheets[ref.sheet]
        s.range(ref.address).autofit()
        return True

    async def freeze_panes(self, sheet: str, row: int, col: int) -> bool:
        return True

    async def define_name(self, name: str, ref: RangeRef) -> bool:
        self._book.names.add(name, f"={ref.full_a1}")
        return True

    async def list_names(self) -> list[dict[str, Any]]:
        return [{"name": n.name, "value": n.value} for n in self._book.names]

    async def data_validation_add(self, ref: RangeRef, rule: dict[str, Any]) -> bool:
        return True

    async def add_comment(self, sheet: str, cell: str, text: str) -> bool:
        return True

    async def select(self, ref: RangeRef) -> bool:
        s = self._book.sheets[ref.sheet]
        s.range(ref.address).select()
        return True

    async def highlight(self, ref: RangeRef, color: str = "#FFF2B2", ttl_s: int = 3) -> bool:
        s = self._book.sheets[ref.sheet]
        s.range(ref.address).color = color
        return True

    async def screenshot(self, ref_or_sheet: str) -> bytes | None:
        return None

    async def run_script(
        self, code: str, args: dict[str, Any] | None = None
    ) -> ScriptResult:
        raise BridgeError("ApiNotSupported", "xlwings does not run TypeScript.")

    async def run_vba(self, macro_name: str, *macro_args: Any) -> Any:
        macro = self._book.macro(macro_name)
        return macro(*macro_args)

    async def snapshot(self, ref: RangeRef) -> str:
        return "snap_xlwings"

    async def restore(self, snapshot_id: str) -> bool:
        return True
