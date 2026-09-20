# ExcelPilot

ExcelPilot is a live, cross-platform Excel AI agent for macOS and Windows. It works directly with an open, active workbook via an Office.js task-pane add-in, or runs headless against files with openpyxl and DuckDB.

## Features

- Live control of open Excel workbooks on Mac and Windows.
- Qwen 3.8 Flash via OpenRouter for planning and reasoning, with optional escalation to Qwen 3.8 Max.
- Jev decision model for intent routing, tool call gating, and claim verification.
- Automatic fallback cascade for Jev: TypeSafe direct to OpenRouter System One to local deterministic policy.
- FastMCP tool server with about 40 tools for ranges, sheets, formulas, tables, charts, pivots, formatting, and snapshots.
- Deep workbook analyzer that inspects structure, dependencies, data health, and reconciliation.
- Pre-write snapshot and rollback system to undo any change.
- Office.js React task pane with live streaming, tool logs, diff approval cards, and undo buttons.

## One-Command Launch

Start ExcelPilot, launch the add-in server, and open Microsoft Excel with a single command:

```bash
./start.sh
```
*(or `make start` or `uv run python -m excelpilot start`)*

This command automatically:
1. Sideloads the add-in manifest for Excel.
2. Builds the add-in bundle if needed.
3. Starts the Python backend server on `http://127.0.0.1:8765`.
4. Starts the Office Add-in server on `https://localhost:3000`.
5. Opens Microsoft Excel so you can use ExcelPilot immediately from the Home ribbon.

## First-Time Setup

1. Install Python dependencies:
   ```bash
   uv sync
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Add your OPENROUTER_API_KEY and TYPESAFE_API_KEY to .env
   ```

3. Run diagnostic check:
   ```bash
   uv run python -m excelpilot doctor
   ```

4. Launch everything:
   ```bash
   ./start.sh
   ```

## Sideloading into Excel Manually (if required)

If your system requires manual add-in loading:
1. In Excel, go to the **Insert** tab.
2. Click **Add-ins** -> **Manage My Add-ins** -> **Upload My Add-in**.
3. Select `addin/manifest.xml`.

## License

MIT
