import re
from typing import Any

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router


async def reconcile_totals(sheet_name: str) -> list[dict[str, Any]]:
    """Verify displayed totals (SUM/SUBTOTAL formulas) against recomputed values."""
    used = await router.used_range(sheet_name)
    data = await router.read(used, values=True, formulas=True)

    reconciliations: list[dict[str, Any]] = []
    if not data.formulas or not data.values:
        return reconciliations

    for r_idx, row in enumerate(data.formulas):
        for c_idx, formula in enumerate(row):
            if not formula or not isinstance(formula, str):
                continue

            # Look for SUM formulas like =SUM(B2:B10)
            match = re.search(r"=\s*SUM\s*\(\s*([A-Z]{1,3}[0-9]+:[A-Z]{1,3}[0-9]+)\s*\)", formula, re.IGNORECASE)
            if match:
                ref_span = match.group(1)
                try:
                    ref = RangeRef(sheet=sheet_name, address=ref_span)
                    page = await router.read(ref, values=True)
                    # Sum up numeric cells
                    recomputed = 0.0
                    for p_row in page.values or []:
                        for cell in p_row:
                            if isinstance(cell, (int, float)):
                                recomputed += float(cell)

                    displayed_val = data.values[r_idx][c_idx]
                    displayed_float = float(displayed_val) if isinstance(displayed_val, (int, float)) else None

                    cell_addr = f"{chr(65 + c_idx)}{r_idx + 1}"
                    delta = abs(recomputed - (displayed_float or 0.0))
                    matches = delta < 1e-5 if displayed_float is not None else False

                    reconciliations.append(
                        {
                            "cell": cell_addr,
                            "formula": formula,
                            "displayed": displayed_float,
                            "recomputed": round(recomputed, 4),
                            "delta": round(delta, 4),
                            "matches": matches,
                        }
                    )
                except Exception:
                    pass

    return reconciliations
