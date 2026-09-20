import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _cleanup_port(port: int) -> None:
    try:
        if platform.system() in ("Darwin", "Linux"):
            res = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True, check=False)
            pids = res.stdout.strip().split()
            for pid in pids:
                if pid and pid.isdigit():
                    subprocess.run(["kill", "-9", pid], check=False)
    except Exception:
        pass


def launch_all() -> None:
    repo_dir = Path(__file__).resolve().parents[3]
    addin_dir = repo_dir / "addin"
    manifest_file = addin_dir / "manifest.xml"

    print("Starting ExcelPilot with a single command...\n")

    # Step 0: Ensure ports 8765 and 3000 are clear
    _cleanup_port(8765)
    _cleanup_port(3000)

    # Step 1: Check manifest sideloading on macOS
    if platform.system() == "Darwin":
        wef_dir = Path.home() / "Library/Containers/com.microsoft.Excel/Data/Documents/wef"
        try:
            wef_dir.mkdir(parents=True, exist_ok=True)
            target_manifest = wef_dir / "excelpilot-manifest.xml"
            shutil.copy(manifest_file, target_manifest)
            print(f"[OK] Add-in manifest sideloaded to {target_manifest}")
        except Exception:
            print("[INFO] Manifest can also be loaded in Excel via: Insert -> Add-ins -> Upload My Add-in.")

    # Step 2: Ensure add-in is built
    dist_dir = addin_dir / "dist"
    if not dist_dir.exists():
        print("Building add-in bundle with webpack...")
        subprocess.run(["npm", "run", "build"], cwd=str(addin_dir), check=False)

    # Step 3: Start Python backend server process
    print("Launching ExcelPilot backend server on http://127.0.0.1:8765...")
    server_cmd = [sys.executable, "-m", "uvicorn", "excelpilot.app.api:app", "--host", "127.0.0.1", "--port", "8765"]
    server_proc = subprocess.Popen(server_cmd, cwd=str(repo_dir))

    # Step 4: Start Add-in dev-server on https://localhost:3000
    print("Launching Office Add-in dev server on https://localhost:3000...")
    addin_cmd = ["npm", "run", "dev-server"]
    addin_proc = subprocess.Popen(addin_cmd, cwd=str(addin_dir))

    time.sleep(2)

    # Step 5: Open Microsoft Excel automatically
    print("Opening Microsoft Excel...")
    if platform.system() == "Darwin":
        subprocess.run(["open", "-a", "Microsoft Excel"], check=False)
    elif platform.system() == "Windows":
        subprocess.run(["cmd", "/c", "start", "excel"], check=False)

    print("\nExcelPilot is live!")
    print("- Backend Server: http://127.0.0.1:8765")
    print("- Add-in UI: https://localhost:3000/taskpane.html")
    print("\nPress Ctrl+C to stop both servers when finished.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping ExcelPilot servers...")
        server_proc.terminate()
        addin_proc.terminate()
        server_proc.wait()
        addin_proc.wait()
        print("Servers stopped cleanly.")
