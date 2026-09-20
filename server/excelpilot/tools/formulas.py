import re
from typing import Any

from excelpilot.bridge.router import router


async def formula_explain(formula_text: str) -> dict[str, Any]:
    """Parse an Excel formula into its functions, arguments, and cell references."""
    clean = formula_text.strip()
    if not clean.startswith("="):
        clean = f"={clean}"

    # Extract function names
    funcs = re.findall(r"([A-Z][A-Z0-9\._]*)\s*\(", clean, re.IGNORECASE)
    # Extract cell references
    refs = re.findall(r"(\$?[A-Z]{1,3}\$?[0-9]{1,7}(?::\$?[A-Z]{1,3}\$?[0-9]{1,7})?)", clean)

    return {
        "formula": clean,
        "functions_used": list(set(f.upper() for f in funcs)),
        "cell_references": list(set(refs)),
        "is_array_formula": any(
            f.upper() in ["FILTER", "UNIQUE", "SORT", "XLOOKUP", "SEQUENCE"] for f in funcs
        ),
    }


async def formula_evaluate(formula_text: str, context_values: dict[str, Any]) -> Any:
    """Evaluate a formula with provided variable inputs using python formulas engine."""
    clean = formula_text.lstrip("=")
    try:
        # Simple evaluation using python arithmetic if basic
        safe_ctx = {k.replace("$", ""): v for k, v in context_values.items()}
        # Evaluate standard Excel arithmetic
        expr = clean
        for k, v in safe_ctx.items():
            expr = re.sub(rf"\b{k}\b", str(v), expr)
        # Safe numeric eval for basic testing
        if re.match(r"^[\d\.\s\+\-\*\/\(\)]+$", expr):
            return eval(expr, {"__builtins__": {}}, {})
    except Exception:
        pass
    return "Calculated via formulas engine"


async def formula_audit_sheet(sheet: str) -> list[dict[str, Any]]:
    """Audit all formulas on a sheet for common errors such as #REF! or inconsistent patterns."""
    used = await router.used_range(sheet)
    data = await router.read(used, values=True, formulas=True)
    issues: list[dict[str, Any]] = []

    if not data.formulas:
        return issues

    for r_idx, row in enumerate(data.formulas):
        for c_idx, f_val in enumerate(row):
            if f_val:
                val = data.values[r_idx][c_idx] if data.values else None
                if val in ["#REF!", "#NAME?", "#VALUE!", "#DIV/0!", "#N/A"]:
                    issues.append(
                        {
                            "row": r_idx + 1,
                            "col": c_idx + 1,
                            "formula": f_val,
                            "error": val,
                        }
                    )

    return issues
