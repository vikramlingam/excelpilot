import pytest
from excelpilot.analysis.health import run_health_checks
from excelpilot.analysis.indexer import index_workbook
from excelpilot.analysis.reconcile import reconcile_totals
from excelpilot.analysis.report import generate_audit_report
from excelpilot.bridge.file import FileBridge
from excelpilot.bridge.router import router


@pytest.mark.asyncio
async def test_analyzer_on_dirty_data():
    router.file_bridge = FileBridge("fixtures/dirty_data.xlsx")

    # Index workbook
    index = await index_workbook()
    assert index.sheet_count >= 1
    assert index.sheets[0].name == "DirtyData"

    # Health checks
    issues = await run_health_checks("DirtyData")
    rule_names = [i.rule for i in issues]
    assert "HardcodedConstant" in rule_names
    assert "NumberStoredAsText" in rule_names

    # Reconciliation
    recons = await reconcile_totals("DirtyData")
    assert len(recons) >= 1
    assert recons[0]["recomputed"] == 750.0

    # Full report generation
    report = await generate_audit_report()
    assert "Workbook Audit Report" in report["report_markdown"]
    assert len(report["issues"]) >= 1
