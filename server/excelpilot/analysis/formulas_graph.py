import re
from typing import Any

from excelpilot.bridge.router import router

VOLATILE_FUNCTIONS = {"NOW", "TODAY", "RAND", "RANDBETWEEN", "OFFSET", "INDIRECT"}


def find_cell_references(formula: str) -> list[str]:
    # Extract cell coordinates like A1, B2:B10, $C$4
    return re.findall(r"\$?[A-Z]{1,3}\$?[0-9]{1,7}", formula)


def has_hardcoded_constants(formula: str) -> bool:
    # Check for magic numbers in arithmetic expressions, excluding 0, 1, 100
    numbers = re.findall(r"[\+\-\*\/]\s*([0-9]+(?:\.[0-9]+)?)\b", formula)
    for num in numbers:
        if float(num) not in {0.0, 1.0, 100.0}:
            return True
    return False


async def analyze_formula_graph(sheet_name: str) -> dict[str, Any]:
    """Parse formulas, detect volatile functions, hardcoded constants, and circular refs."""
    used = await router.used_range(sheet_name)
    data = await router.read(used, values=True, formulas=True)

    formulas_grid = data.formulas or []
    values_grid = data.values or []

    volatile_cells: list[dict[str, Any]] = []
    hardcoded_constant_cells: list[dict[str, Any]] = []
    error_cells: list[dict[str, Any]] = []
    circular_refs: list[str] = []

    for r_idx, row in enumerate(formulas_grid):
        for c_idx, form in enumerate(row):
            if not form or not isinstance(form, str) or not form.startswith("="):
                continue

            cell_coord = f"{chr(65 + c_idx)}{r_idx + 1}"
            upper_form = form.upper()

            # Check for volatile functions
            for vol in VOLATILE_FUNCTIONS:
                if f"{vol}(" in upper_form:
                    volatile_cells.append({"cell": cell_coord, "formula": form, "function": vol})

            # Check for hardcoded constants
            if has_hardcoded_constants(form):
                hardcoded_constant_cells.append({"cell": cell_coord, "formula": form})

            # Check for error values in calculated results
            val = values_grid[r_idx][c_idx] if r_idx < len(values_grid) and c_idx < len(values_grid[r_idx]) else None
            if val in ["#REF!", "#NAME?", "#VALUE!", "#DIV/0!", "#N/A"]:
                error_cells.append({"cell": cell_coord, "formula": form, "error": val})

            # Check for direct circular reference (cell referencing itself)
            refs = find_cell_references(form)
            clean_cell = cell_coord.replace("$", "")
            if any(r.replace("$", "") == clean_cell for r in refs):
                circular_refs.append(cell_coord)

    return {
        "sheet": sheet_name,
        "volatile_functions": volatile_cells,
        "hardcoded_constants": hardcoded_constant_cells,
        "error_cells": error_cells,
        "circular_references": circular_refs,
    }
