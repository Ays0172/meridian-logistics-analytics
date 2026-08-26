# Meridian — Windows one-shot setup.
# Right-click > Run with PowerShell, or:  .\SETUP.ps1
#
# Creates a virtual environment, installs dependencies, then builds and verifies
# the whole dataset. Roughly 25-35 minutes.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "=============================================================================="
Write-Host "  MERIDIAN LOGISTICS ANALYTICS - Windows setup"
Write-Host "=============================================================================="

# --- Python present? ---------------------------------------------------------
try {
    $ver = & python --version 2>&1
    Write-Host "`nFound $ver"
} catch {
    Write-Host "`nPython not found on PATH." -ForegroundColor Red
    Write-Host "Install Python 3.11+ from python.org and tick 'Add python.exe to PATH'."
    exit 1
}

# --- Virtual environment -----------------------------------------------------
$venv = Join-Path $root ".venv"
if (-not (Test-Path $venv)) {
    Write-Host "`nCreating virtual environment at .venv ..."
    & python -m venv $venv
} else {
    Write-Host "`nUsing existing .venv"
}

$py = Join-Path $venv "Scripts\python.exe"

# --- Dependencies ------------------------------------------------------------
Write-Host "`nInstalling dependencies ..."
& $py -m pip install --upgrade pip --quiet
& $py -m pip install -r (Join-Path $root "01_generator\requirements.txt")

# --- Build, verify, feed -----------------------------------------------------
Write-Host "`nBuilding and verifying. This is the long part - leave it running.`n"
& $py (Join-Path $root "setup_all.py")

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nSetup did not complete cleanly. Read the output above." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n=============================================================================="
Write-Host "  Done. Open 00_docs\start-here.html to begin."
Write-Host "=============================================================================="
Write-Host "`nEvery morning, to advance the live feed:"
Write-Host "  .\.venv\Scripts\python.exe .\01_generator\live_feed.py"
