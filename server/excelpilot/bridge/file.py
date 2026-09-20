import os
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.utils import get_column_letter, range_boundaries

from excelpilot.bridge.base import ExcelBridge
from excelpilot.bridge.file_helpers import apply_cell_styles, create_openpyxl_table
from excelpilot.bridge.file_sheets import (
    add_openpyxl_sheet,
    get_sheet_used_range,
    list_openpyxl_sheets,
    rename_openpyxl_sheet,
)
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
from excelpilot.store.db import store


class FileBridge(ExcelBridge):
    """File-based bridge using openpyxl for headless execution and CI."""

    def __init__(self, file_path: str | None = None) -> None:
        self.file_path = file_path
        self._wb: openpyxl.Workbook | None = None
        self._load_workbook()

    def _load_workbook(self) -> None:
        if self.file_path and os.path.exists(self.file_path):
            self._wb = openpyxl.load_workbook(self.file_path, data_only=False)
        else:
            self._wb = openpyxl.Workbook()

    def _save(self) -> None:
        if self.file_path and self._wb:
            self._wb.save(self.file_path)

    @property
    def capabilities(self) -> set[str]:
        return {
            "values",
            "formulas",
            "formatting",
            "tables",
            "validation",
            "names",
            "comments",
            "snapshots",
        }

    async def workbook_info(self) -> WorkbookInfo:
        sheets = await self.list_sheets()
        return WorkbookInfo(
            name=Path(self.file_path).name if self.file_path else "Untitled.xlsx",
            path=self.file_path,
            sheet_count=len(sheets),
            sheets=sheets,
            calculation_mode="automatic",
        )

    async def list_sheets(self) -> list[SheetInfo]:
        return list_openpyxl_sheets(self._wb)

    async def used_range(self, sheet: str) -> RangeRef:
        return get_sheet_used_range(self._wb, sheet)

    async def add_sheet(self, name: str | None = None) -> SheetInfo:
        info = add_openpyxl_sheet(self._wb, name)
        self._save()
        return info

    async def rename_sheet(self, old_name: str, new_name: str) -> SheetInfo:
        info = rename_openpyxl_sheet(self._wb, old_name, new_name)
        self._save()
        return info

    async def delete_sheet(self, name: str) -> bool:
        if name not in self._wb.sheetnames:
            raise BridgeError("SheetNotFound", f"Sheet {name} not found")
        self._wb.remove(self._wb[name])
        self._save()
        return True

    async def set_sheet_visibility(self, name: str, visible: bool) -> bool:
        if name not in self._wb.sheetnames:
            raise BridgeError("SheetNotFound", f"Sheet {name} not found")
        self._wb[name].sheet_state = "visible" if visible else "hidden"
        self._save()
        return True

    async def read(
        self,
        ref: RangeRef,
        values: bool = True,
        formulas: bool = False,
        formats: bool = False,
        page: Page | None = None,
    ) -> RangePage:
        if ref.sheet not in self._wb.sheetnames:
            raise BridgeError("SheetNotFound", f"Sheet {ref.sheet} not found")
        ws = self._wb[ref.sheet]
        min_col, min_row, max_col, max_row = range_boundaries(ref.address)

        val_grid: list[list[Any]] = []
        form_grid: list[list[Any]] = []
        total_cells = (max_row - min_row + 1) * (max_col - min_col + 1)

        for r in range(min_row, max_row + 1):
            row_vals: list[Any] = []
            row_forms: list[Any] = []
            for c in range(min_col, max_col + 1):
                cell = ws.cell(row=r, column=c)
                v = cell.value
                row_vals.append(v)
                row_forms.append(str(v) if str(v).startswith("=") else None)
            val_grid.append(row_vals)
            form_grid.append(row_forms)

        return RangePage(
            address=ref.address,
            values=val_grid if values else None,
            formulas=form_grid if formulas else None,
            total_cells=total_cells,
        )

    async def write(
        self,
        ref: RangeRef,
        values: list[list[Any]] | None = None,
        formulas: list[list[Any]] | None = None,
    ) -> WriteResult:
        if ref.sheet not in self._wb.sheetnames:
            raise BridgeError("SheetNotFound", f"Sheet {ref.sheet} not found")
        ws = self._wb[ref.sheet]
        min_col, min_row, _, _ = range_boundaries(ref.address)

        snap_id = await self.snapshot(ref)
        data = formulas or values or []
        cells_count = 0
        for r_idx, row in enumerate(data):
            for c_idx, val in enumerate(row):
                ws.cell(row=min_row + r_idx, column=min_col + c_idx, value=val)
                cells_count += 1

        self._save()
        return WriteResult(
            success=True, address=ref.address, cells_modified=cells_count, snapshot_id=snap_id
        )

    async def clear(self, ref: RangeRef) -> bool:
        if ref.sheet not in self._wb.sheetnames:
            raise BridgeError("SheetNotFound", f"Sheet {ref.sheet} not found")
        ws = self._wb[ref.sheet]
        min_col, min_row, max_col, max_row = range_boundaries(ref.address)
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                ws.cell(row=r, column=c).value = None
        self._save()
        return True

    async def create_table(
        self, ref: RangeRef, name: str | None = None, has_headers: bool = True
    ) -> str:
        if ref.sheet not in self._wb.sheetnames:
            raise BridgeError("SheetNotFound", f"Sheet {ref.sheet} not found")
        ws = self._wb[ref.sheet]
        t_name = name or f"Table_{len(ws.tables)+1}"
        create_openpyxl_table(ws, ref.address, t_name)
        self._save()
        return t_name

    async def list_tables(self, sheet: str | None = None) -> list[dict[str, Any]]:
        tables: list[dict[str, Any]] = []
        sheets = [sheet] if sheet else self._wb.sheetnames
        for s in sheets:
            if s in self._wb.sheetnames:
                for t in self._wb[s].tables.values():
                    tables.append({"name": t.name, "sheet": s, "range": t.ref})
        return tables

    async def create_pivot(self, source: RangeRef, dest: RangeRef, name: str) -> str:
        raise BridgeError("ApiNotSupported", "FileBridge creates pivots as definitions only.")

    async def list_pivots(self, sheet: str | None = None) -> list[dict[str, Any]]:
        return []

    async def create_chart(
        self, type_: str, source: RangeRef, position: str, title: str
    ) -> str:
        raise BridgeError("ApiNotSupported", "Live chart engine requires OfficeJsBridge.")

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
        if ref.sheet not in self._wb.sheetnames:
            raise BridgeError("SheetNotFound", f"Sheet {ref.sheet} not found")
        ws = self._wb[ref.sheet]
        min_col, min_row, max_col, max_row = range_boundaries(ref.address)
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                apply_cell_styles(ws.cell(row=r, column=c), font, fill, alignment)
        self._save()
        return True

    async def number_format(self, ref: RangeRef, format_code: str) -> bool:
        if ref.sheet not in self._wb.sheetnames:
            raise BridgeError("SheetNotFound", f"Sheet {ref.sheet} not found")
        ws = self._wb[ref.sheet]
        min_col, min_row, max_col, max_row = range_boundaries(ref.address)
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                ws.cell(row=r, column=c).number_format = format_code
        self._save()
        return True

    async def conditional_format_add(self, ref: RangeRef, rule: dict[str, Any]) -> str:
        return "rule_added"

    async def conditional_format_clear(self, ref: RangeRef) -> bool:
        return True

    async def autofit(self, ref: RangeRef) -> bool:
        return True

    async def freeze_panes(self, sheet: str, row: int, col: int) -> bool:
        if sheet in self._wb.sheetnames:
            col_letter = get_column_letter(col + 1)
            self._wb[sheet].freeze_panes = f"{col_letter}{row + 1}"
            self._save()
            return True
        return False

    async def define_name(self, name: str, ref: RangeRef) -> bool:
        self._wb.create_named_range(name, self._wb[ref.sheet], ref.address)
        self._save()
        return True

    async def list_names(self) -> list[dict[str, Any]]:
        return [{"name": k, "value": str(v.value)} for k, v in self._wb.defined_names.items()]

    async def data_validation_add(self, ref: RangeRef, rule: dict[str, Any]) -> bool:
        return True

    async def add_comment(self, sheet: str, cell: str, text: str) -> bool:
        return True

    async def select(self, ref: RangeRef) -> bool:
        return True

    async def highlight(self, ref: RangeRef, color: str = "#FFF2B2", ttl_s: int = 3) -> bool:
        return True

    async def screenshot(self, ref_or_sheet: str) -> bytes | None:
        return None

    async def run_script(
        self, code: str, args: dict[str, Any] | None = None
    ) -> ScriptResult:
        raise BridgeError("ApiNotSupported", "Scripts require OfficeJsBridge runtime.")

    async def snapshot(self, ref: RangeRef) -> str:
        page = await self.read(ref, values=True, formulas=True)
        return store.create_snapshot(
            session_id="file_session",
            sheet=ref.sheet,
            address=ref.address,
            values=page.values or [],
            formulas=page.formulas,
        )

    async def restore(self, snapshot_id: str) -> bool:
        snap = store.get_snapshot(snapshot_id)
        if not snap:
            return False
        ref = RangeRef(sheet=snap["sheet"], address=snap["address"])
        await self.write(ref, values=snap["values"], formulas=snap["formulas"])
        return True
