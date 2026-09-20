from typing import Any

from pydantic import BaseModel, Field


class RangeRef(BaseModel):
    sheet: str
    address: str

    @property
    def full_a1(self) -> str:
        clean_sheet = f"'{self.sheet}'" if " " in self.sheet else self.sheet
        return f"{clean_sheet}!{self.address}"

    @classmethod
    def from_a1(cls, a1_notation: str, default_sheet: str = "Sheet1") -> "RangeRef":
        if "!" in a1_notation:
            sheet_part, addr_part = a1_notation.split("!", 1)
            sheet = sheet_part.strip("'\"")
            return cls(sheet=sheet, address=addr_part)
        return cls(sheet=default_sheet, address=a1_notation)


class Page(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=4000, gt=0)


class RangePage(BaseModel):
    address: str
    values: list[list[Any]] | None = None
    formulas: list[list[Any]] | None = None
    formats: list[list[Any]] | None = None
    next_offset: int | None = None
    total_cells: int = 0


class SheetInfo(BaseModel):
    name: str
    index: int
    visibility: str = "visible"
    row_count: int = 0
    column_count: int = 0
    has_tables: bool = False
    has_pivots: bool = False
    has_charts: bool = False


class WorkbookInfo(BaseModel):
    name: str
    path: str | None = None
    sheet_count: int = 0
    sheets: list[SheetInfo] = Field(default_factory=list)
    calculation_mode: str = "automatic"


class WriteResult(BaseModel):
    success: bool
    address: str
    cells_modified: int
    snapshot_id: str | None = None
    message: str | None = None


class ScriptResult(BaseModel):
    success: bool
    output: str | None = None
    logs: list[str] = Field(default_factory=list)
    error: str | None = None
    cells_affected: int = 0


class BridgeError(Exception):
    def __init__(self, code: str, message: str, requirement_set: str | None = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.requirement_set = requirement_set
