# ExcelPilot

ExcelPilot is a local Excel agent. You talk to it in a task pane inside Microsoft Excel. It reads and writes the workbook that is already open.

This project is still under development. Expect rough edges. Some planned pieces are in the repo but are not wired into the live chat path yet.

It runs on your machine. The Python server binds to `127.0.0.1:8765`. The Office add-in loads from `https://localhost:3000`. Cell data only leaves the machine when a model API is called (OpenRouter for the chat model, and TypeSafe or OpenRouter for Jev).

## What it does today

- Live control of an open workbook on Mac and Windows through an Office.js task pane.
- Chat with streaming replies, a tool log, and Apply / Decline cards for destructive changes.
- PDF attach in the pane (digital PDFs up to 8 MB). Tables go onto a new sheet when extraction works.
- FastMCP tool server with 48 tools (ranges, sheets, formulas, tables, pivots, charts, formatting, SQL on a sheet, scripts, snapshots).
- Headless file mode via openpyxl and DuckDB (`excelpilot analyze path.xlsx`).
- Optional MCP stdio/SSE server so another client can call the same tools.

## What Jev is for

Jev is not the model that writes formulas or chats with you. That is the OpenRouter chat model (`OPENROUTER_MODEL`, default `inception/mercury-2.5`).

Jev is a small decision model (TypeSafe System One, `jev-latest`). ExcelPilot uses it as a judge, not as a writer.

**Live path today.** Destructive tools (`sheet_delete`, `workbook_reset`, `range_clear`, `range_insert_delete_rows_cols`, `table_to_range`, `pivot_delete`, `chart_delete`, `script_run_typescript`, `vba_run`) go through `judge_tool_call` before they run. Jev answers three questions: did the user ask for this, is the target in scope, and is it acceptable if the user confirmed in the UI. The scores become `approve`, `block`, or `review`. `block` skips the tool. `review` (and every destructive call) still shows an Apply card in the pane.

If Jev cannot be reached, the gate returns `review` and the Apply card still appears. Ordinary writes (values, formulas, format, new sheets) do not call Jev. They run unless you set `EXCELPILOT_ALWAYS_ASK_BEFORE_WRITES=true`.

**Backends.** `server/excelpilot/agent/jev/client.py` tries TypeSafe (`TYPESAFE_API_KEY`), then OpenRouter System One (`OPENROUTER_API_KEY`, if `JEV_FALLBACK_VIA_OPENROUTER=true`), then offline. Callers then use local Python policy (`heuristic_intent`, `evaluate_static_policy`). Auth failures on TypeSafe cool down for 15 minutes. Other errors cool down for 30 seconds. `/health` reports `jev.backend` as `typesafe`, `openrouter`, `offline`, or `unprobed`. The task pane shows that as `Jev: ...`.

**In code, not on the chat path.** `route_turn` can ask Jev for intent and model tier. Chat turns currently use `heuristic_intent` and `heuristic_tier` instead, so a Jev outage does not stall routing. `verify.py`, `judge_script_safety`, and `judge_task_done` exist but `orchestrator.py` does not call them.

## How a turn works

1. The pane sends the prompt (and optional PDF) over `/chat`.
2. The add-in also keeps a `/bridge` WebSocket so tools can call Excel via JSON-RPC.
3. The orchestrator classifies the request with local heuristics, loads a skill prompt from `server/excelpilot/agent/skills/`, and exposes only that skill's tool subset.
4. pydantic-ai runs the OpenRouter model with sequential tool calls.
5. `before_tool_execute` applies static policy, optionally waits for Apply, and calls Jev only for destructive tools.
6. Writes go through the bridge router: Office.js if the pane is connected, otherwise xlwings if installed, otherwise the openpyxl file bridge.

Wipe-the-workbook and "delete sheet X" requests skip the LLM and run a dedicated destructive path with the same Jev + Apply gate.

## Requirements

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js (add-in webpack build)
- Microsoft Excel for Mac or Windows (for the live pane)
- An [OpenRouter](https://openrouter.ai/) API key

A TypeSafe key is optional. Without it, Jev falls back to OpenRouter System One, then to local policy.

## Setup

```bash
uv sync
cp .env.example .env
```

Put at least `OPENROUTER_API_KEY` in `.env`. See `.env.example` for the rest.

```bash
uv run python -m excelpilot doctor
```

That checks the data dir (`~/.excelpilot`), probes Jev, hits OpenRouter, and looks for Excel.

First add-in build:

```bash
cd addin && npm install && npm run build && cd ..
```

## Run

One process that starts the API, the add-in webpack server, and Excel:

```bash
./start.sh
```

Same thing: `make start` or `uv run python -m excelpilot start`.

Then in Excel, Home -> ExcelPilot. Wait until the pane says Connected.

Other commands:

| Command | What it does |
|---|---|
| `uv run python -m excelpilot serve` | API only, `127.0.0.1:8765` |
| `uv run python -m excelpilot mcp` | FastMCP over stdio (`--transport sse` is also valid) |
| `uv run python -m excelpilot analyze file.xlsx` | Audit report on a file, no Excel needed |
| `uv run python -m excelpilot doctor` | Connectivity checks |
| `make test` | `pytest tests/` |
| `make addin-build` | Rebuild the task pane |

If the pane sits on Connecting, the backend is probably not running or two processes are fighting over 8765. Kill whatever is on that port and start once:

```bash
lsof -ti :8765 | xargs kill -9
uv run python -m excelpilot start
```

After changing add-in TypeScript, rebuild (`cd addin && npm run build`) and reload the add-in.

Manual sideload if the launcher did not copy the manifest: Excel -> Insert -> Add-ins -> Upload My Add-in -> `addin/manifest.xml`. On Mac the launcher also copies it to `~/Library/Containers/com.microsoft.Excel/Data/Documents/wef/excelpilot-manifest.xml`.

## Chat models

Set in `.env` or in the pane settings.

- `OPENROUTER_MODEL` (default `inception/mercury-2.5`) for ordinary turns
- `OPENROUTER_MODEL_CAPABLE` (default `openai/gpt-5.6-luna`) when the heuristic picks `capable` (financial model, multi-sheet, large workbooks)
- `OPENROUTER_MODEL_FALLBACKS` if the primary model fails

The pane can pin a specific OpenRouter id instead of Auto.

## PDF attach

Drop or attach a `.pdf` in the pane. Limit is 8 MB, 20 pages.

Digital PDFs are parsed with pdfplumber (tables) and pypdf (text). If both are empty, `maybe_vision_extract` sends extracted text (not page images) to `google/gemini-2.5-flash` on OpenRouter. Scanned image-only PDFs often still come back empty. That path is unfinished.

There is also `POST /api/upload-pdf` for the same parser without chat.

## Safety, as implemented

- Destructive tools always pause for Apply in the pane (120 s timeout).
- Jev can `block` a destructive call even before the card.
- Static policy refuses deleting the last sheet, deleting a sheet other formulas reference, and clearing more than 50,000 cells.
- `sheet_add`, `table_create`, and `pivot_create` reuse a name that already exists instead of failing with `ItemAlreadyExists`.
- Audit rows go to SQLite under `~/.excelpilot`.

Undo is not working in the live path. Snapshot helpers exist (`snapshot_restore`, `snapshot_info`, bridge `restore`), but `before_tool_execute` sets `snapshot_id = None` so writes are not snapshotted. Do not rely on rollback.

## Repo layout

```
addin/                      Office.js task pane (React + Fluent UI)
server/excelpilot/
  app/                      FastAPI: /health, /api/*, /bridge, /chat
  agent/                    orchestrator, skills, hooks, Jev
  tools/                    FastMCP tools + TOOL_FUNCTIONS
  bridge/                   Office.js, xlwings, openpyxl file adapter
  analysis/                 health checks, formula graph, PDF parser
  store/                    SQLite audit + snapshot tables
  cli/                      start launcher, doctor
tests/
fixtures/                   sample workbooks for tests
```

## Tests

```bash
uv run pytest tests/ -v
```

Covered today: Jev client cascade, intent heuristics, write/destructive gates, PDF parser, file bridge, store, range grid, turn reliability (multiple event streams in one run).

## Known gaps

- Snapshot / undo on the write path
- Jev intent routing and claim checks not used by `execute_turn`
- Scanned PDF vision (text snippet only, no page images)
- TypeSafe keys that 401 are skipped; Jev then uses OpenRouter or local policy
- Health checks implement 8 rules, not a full audit suite
- `PLAN.md` is an internal status note and is gitignored

## License

MIT. See `LICENSE`.
