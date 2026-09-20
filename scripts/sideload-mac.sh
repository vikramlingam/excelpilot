#!/bin/bash
# Sideload ExcelPilot manifest on macOS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST_SRC="$REPO_DIR/addin/manifest.xml"
WEF_DIR="$HOME/Library/Containers/com.microsoft.Excel/Data/Documents/wef"

echo "Configuring ExcelPilot Add-in on macOS..."

# Method 1: Attempt to copy to Excel WEF container directory
if mkdir -p "$WEF_DIR" 2>/dev/null && cp "$MANIFEST_SRC" "$WEF_DIR/excelpilot-manifest.xml" 2>/dev/null; then
  echo "[OK] Manifest copied to $WEF_DIR/excelpilot-manifest.xml"
else
  echo "[INFO] Sandboxed container directory requires terminal permission."
  echo "You can grant Full Disk Access to Terminal in System Settings, or sideload via Excel:"
  echo "In Excel: Insert menu -> Add-ins -> Manage My Add-ins -> Upload My Add-in -> Select $MANIFEST_SRC"
fi

echo ""
echo "Development Server:"
echo "1. Server: uv run python -m excelpilot serve"
echo "2. Add-in: cd addin && npm run dev-server"
