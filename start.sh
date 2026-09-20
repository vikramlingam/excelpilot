#!/bin/bash
# Single command launcher for ExcelPilot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Run the python launcher
exec uv run python -m excelpilot start
