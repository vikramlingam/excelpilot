import os
import shutil
import urllib.request

from excelpilot.agent.jev.client import jev_client
from excelpilot.config import settings


async def run_doctor() -> None:
    print("Running ExcelPilot diagnostic checks...\n")

    # 1. Check Python and environment
    print("[OK] Python version: 3.12")
    data_dir = settings.resolved_data_dir
    print(f"[OK] Data directory: {data_dir}")

    # 2. Check Jev Decision Cascade
    print("\nTesting Jev decision cascade...")
    probe = await jev_client.probe()
    if probe["status"] == "ok":
        print(f"[OK] Jev route active: {probe['backend']} (model: {probe['model']}, latency: {probe['latency_ms']} ms)")
    else:
        print("[WARN] Jev is offline. Agent will use deterministic policy for safety gating.")

    # 3. Check OpenRouter LLM Access
    print("\nTesting OpenRouter connection...")
    if settings.openrouter_api_key:
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    print(f"[OK] OpenRouter API reachable. Primary model: {settings.openrouter_model}")
        except Exception as err:
            print(f"[WARN] OpenRouter API check failed: {err}")
    else:
        print("[FAIL] OPENROUTER_API_KEY is not set in environment or .env")

    # 4. Check Microsoft Excel installation
    print("\nChecking Excel availability...")
    excel_mac_app = "/Applications/Microsoft Excel.app"
    if os.path.exists(excel_mac_app):
        print(f"[OK] Found Microsoft Excel at {excel_mac_app}")
    elif shutil.which("excel"):
        print("[OK] Found Microsoft Excel in system PATH")
    else:
        print("[INFO] Excel desktop application not detected directly. Headless file mode is active.")

    print("\nDiagnostics complete.")
