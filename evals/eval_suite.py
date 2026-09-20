import asyncio
from pathlib import Path
from typing import Any

from excelpilot.analysis.report import generate_audit_report
from excelpilot.bridge.file import FileBridge
from excelpilot.bridge.router import router

EVALS_DIR = Path(__file__).parent


async def run_eval_bench() -> dict[str, Any]:
    print("Running ExcelPilot evaluation benchmark...")

    fixtures_dirty = Path("fixtures/dirty_data.xlsx")
    if not fixtures_dirty.exists():
        print("Fixture dirty_data.xlsx not found.")
        return {"status": "error", "message": "Missing fixture"}

    router.file_bridge = FileBridge(str(fixtures_dirty))
    report = await generate_audit_report()

    issues_found = len(report["issues"])
    recons_checked = sum(len(r) for r in report["reconciliations"].values())

    results = {
        "benchmark": "WorkbookAudit-v1",
        "issues_detected": issues_found,
        "reconciliations_checked": recons_checked,
        "status": "pass" if issues_found >= 4 and recons_checked >= 1 else "fail",
    }

    print(f"Eval results: {results}")
    return results


if __name__ == "__main__":
    asyncio.run(run_eval_bench())
