# Windows PowerShell sideload helper for ExcelPilot

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoDir = Split-Path -Parent $ScriptDir
$ManifestPath = Join-Path $RepoDir "addin\manifest.xml"

Write-Host "Registering ExcelPilot manifest for Office Add-in debugging on Windows..."

# Run office-addin-debugging to register manifest
Set-Location -Path (Join-Path $RepoDir "addin")
npx office-addin-debugging start manifest.xml desktop

Write-Host "[OK] Manifest registered. Launch Microsoft Excel to use ExcelPilot."
