from typing import Any

from excelpilot.analysis.health import HealthIssue, run_health_checks
from excelpilot.analysis.indexer import index_workbook
from excelpilot.analysis.reconcile import reconcile_totals


async def generate_audit_report() -> dict[str, Any]:
    """Run full analysis pipeline and produce structured markdown audit and facts table."""
    index = await index_workbook()

    all_issues: list[HealthIssue] = []
    reconciliations: dict[str, list[dict[str, Any]]] = {}

    for s in index.sheets:
        sheet_issues = await run_health_checks(s.name)
        all_issues.extend(sheet_issues)
        recon = await reconcile_totals(s.name)
        reconciliations[s.name] = recon

    # Sort issues by severity: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    sorted_issues = sorted(all_issues, key=lambda i: severity_order.get(i.severity, 3))

    # Build Markdown document
    lines: list[str] = [
        f"# Workbook Audit Report: {index.workbook_name}\n",
        "## 1. Workbook at a Glance",
        f"- Worksheets count: {index.sheet_count}",
        f"- Defined named ranges: {len(index.named_ranges)}\n",
        "| Sheet Name | Used Range | Rows | Columns | Tables | Pivots | Charts |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for s in index.sheets:
        lines.append(
            f"| {s.name} | {s.used_range} | {s.row_count} | {s.column_count} | "
            f"{len(s.tables)} | {len(s.pivots)} | {len(s.charts)} |"
        )

    lines.extend(["\n## 2. Data Health and Risk Register", f"Total issues identified: {len(sorted_issues)}\n"])

    if sorted_issues:
        lines.append("| Severity | Rule | Location | Evidence |")
        lines.append("| --- | --- | --- | --- |")
        for iss in sorted_issues:
            lines.append(f"| {iss.severity.upper()} | {iss.rule} | {iss.sheet}!{iss.location} | {iss.evidence} |")
    else:
        lines.append("No critical data health risks detected.")

    lines.extend(["\n## 3. Total Reconciliation", "Verifying displayed formula totals against recomputed numbers:\n"])

    has_recon = False
    for s_name, recons in reconciliations.items():
        if recons:
            has_recon = True
            lines.append(f"### Sheet: {s_name}")
            lines.append("| Cell | Formula | Displayed | Recomputed | Delta | Status |")
            lines.append("| --- | --- | --- | --- | --- | --- |")
            for r in recons:
                status = "PASS" if r["matches"] else "FAIL"
                lines.append(
                    f"| {r['cell']} | `{r['formula']}` | {r['displayed']} | "
                    f"{r['recomputed']} | {r['delta']} | {status} |"
                )

    if not has_recon:
        lines.append("No explicit SUM formula totals found for reconciliation.")

    lines.extend([
        "\n## 4. Prioritized Recommendations",
        "1. Resolve any critical circular references and formula errors immediately.",
        "2. Convert large plain ranges into official Excel Tables for structured references.",
        "3. Replace volatile functions like OFFSET and INDIRECT with modern dynamic array functions.",
    ])

    markdown_report = "\n".join(lines)

    return {
        "report_markdown": markdown_report,
        "index": index.model_dump(),
        "issues": [i.model_dump() for i in sorted_issues],
        "reconciliations": reconciliations,
    }
