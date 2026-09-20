from pydantic import BaseModel

from excelpilot.analysis.formulas_graph import analyze_formula_graph
from excelpilot.analysis.profile import profile_sheet_columns
from excelpilot.bridge.router import router


class HealthIssue(BaseModel):
    rule: str
    severity: str  # critical, warning, info
    sheet: str
    location: str
    evidence: str


async def run_health_checks(sheet_name: str) -> list[HealthIssue]:
    """Run comprehensive health checks across formulas, types, formatting, and structures."""
    issues: list[HealthIssue] = []

    # Check 1: Formula graph rules (circular refs, errors, volatile functions, constants)
    f_graph = await analyze_formula_graph(sheet_name)

    for cell in f_graph["circular_references"]:
        issues.append(
            HealthIssue(
                rule="CircularReference",
                severity="critical",
                sheet=sheet_name,
                location=cell,
                evidence=f"Cell {cell} directly references itself in its calculation formula",
            )
        )

    for err in f_graph["error_cells"]:
        issues.append(
            HealthIssue(
                rule="FormulaError",
                severity="critical",
                sheet=sheet_name,
                location=err["cell"],
                evidence=f"Formula '{err['formula']}' evaluated to calculation error '{err['error']}'",
            )
        )

    for const in f_graph["hardcoded_constants"]:
        issues.append(
            HealthIssue(
                rule="HardcodedConstant",
                severity="warning",
                sheet=sheet_name,
                location=const["cell"],
                evidence=f"Formula '{const['formula']}' contains hardcoded magic numbers",
            )
        )

    for vol in f_graph["volatile_functions"]:
        issues.append(
            HealthIssue(
                rule="VolatileFunction",
                severity="info",
                sheet=sheet_name,
                location=vol["cell"],
                evidence=f"Uses volatile function {vol['function']} which forces recalculation on any sheet edit",
            )
        )

    # Check 2: Profile checks (numbers stored as text, trailing whitespace, null headers)
    profiles = await profile_sheet_columns(sheet_name)
    for p in profiles:
        col = p["column"]
        if p["numbers_stored_as_text"] > 0:
            issues.append(
                HealthIssue(
                    rule="NumberStoredAsText",
                    severity="warning",
                    sheet=sheet_name,
                    location=f"Column {col}",
                    evidence=f"{p['numbers_stored_as_text']} numbers are stored as text strings",
                )
            )

        if p["cells_with_whitespace"] > 0:
            issues.append(
                HealthIssue(
                    rule="WhitespaceInValues",
                    severity="info",
                    sheet=sheet_name,
                    location=f"Column {col}",
                    evidence=f"{p['cells_with_whitespace']} cells contain leading or trailing whitespace",
                )
            )

        if "unnamed" in col.lower() or not col.strip():
            issues.append(
                HealthIssue(
                    rule="BlankHeader",
                    severity="warning",
                    sheet=sheet_name,
                    location=f"Header {col}",
                    evidence="Table column is missing a descriptive header name",
                )
            )

    # Check 3: Check table presence
    tables = await router.list_tables(sheet_name)
    if not tables and len(profiles) > 3 and any(p["total_count"] > 20 for p in profiles):
        issues.append(
            HealthIssue(
                rule="MissingTableStructure",
                severity="info",
                sheet=sheet_name,
                location=sheet_name,
                evidence="Data range has over 20 rows but is not converted to an Excel Table",
            )
        )

    return issues
