# Changelog

All notable changes to ExcelPilot will be documented in this file.

## [1.0.0] - 2026-09-20

### Added
- Live Office.js bridge over local WebSocket JSON-RPC.
- Qwen 3.8 Flash orchestration with escalation to Qwen 3.8 Max.
- Jev decision model integration with 3-tier cascade:
  1. TypeSafe direct
  2. OpenRouter System One fallback
  3. Deterministic local policy
- FastMCP tool server with ~40 tools for ranges, formulas, sheets, formatting, pivots, and charts.
- Deep workbook analyzer with 25+ automated health rules and total reconciliation.
- Pre-write snapshot system in SQLite with one-click undo.
- React and Fluent UI task-pane add-in for Microsoft Excel on Mac and Windows.
- CLI interface with doctor, serve, analyze, and mcp commands.
