# Changelog

Notable changes to ExcelPilot. This project is still under development. Version numbers in `pyproject.toml` / the add-in are `1.0.0`; treat that as a working snapshot, not a finished release.

## Unreleased

### Fixed

- Chat turns no longer die on the second model/tool stream. pydantic-ai calls `event_stream_handler` once per node; the orchestrator used to treat the first stream ending as "run finished" and then hit the idle timeout ("The model took too long"). The run task is now the only terminal signal. Covered by `tests/test_turn_reliability.py`.
- `sheet_add`, `table_create`, and `pivot_create` (server tools and the Office.js executors) reuse an existing name instead of raising `ItemAlreadyExists`.
- Default `LLM_TIMEOUT_S` is 90. Idle wait is at least 180 s. Tool calls are sequential (`parallel_tool_calls=False`).
- Bulk writes no longer pop an Apply card unless `EXCELPILOT_ALWAYS_ASK_BEFORE_WRITES=true`. Destructive tools still always ask.
- Task pane status shows "Waiting for your approval..." on `approval_required`, and `Jev: ...` is filled from `/health` (`jev.backend`) instead of staying on "local".

### Added

- PDF attach in the task pane and `POST /api/upload-pdf`. Digital PDFs via pdfplumber/pypdf. Empty extracts can try a text-only OpenRouter fallback (`google/gemini-2.5-flash`). Scanned page images are not sent; that path is unfinished.
- Dedicated wipe-workbook / delete-sheet path that skips the LLM and still goes through Jev + Apply.
- Fast path that writes extracted PDF tables onto a new sheet without a full agent turn.

### Known not working

- Pre-write snapshots and undo. The store and `snapshot_restore` tool exist, but the write hook does not take a snapshot.
- Jev `route_turn` / claim verification / script safety / done-check are implemented in `agent/jev/gates.py` and `agent/verify.py` but are not called from `execute_turn`.

## 2026-09-20 (initial snapshot)

- Live Office.js bridge over a local WebSocket JSON-RPC (`/bridge`).
- Chat over `/chat` with pydantic-ai and an OpenRouter model.
- Jev decision client: TypeSafe, then OpenRouter System One, then local policy. Used on destructive tools.
- FastMCP tool server (48 registered tools).
- Workbook health checks (8 rules in `analysis/health.py`) plus formula graph and total reconciliation.
- React / Fluent UI task pane for Excel on Mac and Windows.
- CLI: `start`, `serve`, `mcp`, `doctor`, `analyze`.

