#
# scripts/setup.ps1 - idempotent provisioner (safe to re-run).
# Creates .venv if missing, installs dependencies, seeds backend\.env, installs frontend deps.
#
# Usage:  .\scripts\setup.ps1 [-SkipFrontend]
# Exit :  0 = ready, 1 = blocked (message says what to do)
#
param(
    [switch]$SkipFrontend
)

# NOTE: ErrorActionPreference is "Continue" on purpose - pip/npm write to stderr on
# success paths, and "Stop" would abort the provisioner on harmless progress output.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Say([string]$Text, [string]$Color = "Gray") { Write-Host $Text -ForegroundColor $Color }
function Die([string]$Text) { Write-Host "BLOCKED: $Text" -ForegroundColor Red; exit 1 }

Say "== 1. Prerequisites ==" "Cyan"

$py312 = Get-Command py -ErrorAction SilentlyContinue
$pythonExe = $null
if ($py312) {
    $pythonExe = (py -3.12 -c "import sys;print(sys.executable)" 2>$null)
}
if (-not $pythonExe) {
    $fallback = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
    if (Test-Path $fallback) { $pythonExe = $fallback }
}
if (-not $pythonExe) {
    Die "Python 3.12 not found. Run: winget install --id Python.Python.3.12 -e --scope user"
}
Say "   python : $pythonExe"
Say "   version: $(& $pythonExe -V)"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Say "   WARN   node/npm not found - the frontend step will be skipped" "Yellow"
}

Say ""
Say "== 2. Virtual environment ==" "Cyan"
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Say "   creating .venv ..."
    & $pythonExe -m venv .venv
    if ($LASTEXITCODE -ne 0) { Die "venv creation failed" }
}
Say "   .venv  : $(& $venvPy -V)"

$cfg = Get-Content (Join-Path $root ".venv\pyvenv.cfg") -Raw
if ($cfg -notmatch "include-system-site-packages\s*=\s*false") {
    Die ".venv leaks system site-packages; delete .venv and re-run this script"
}

Say ""
Say "== 3. Dependencies ==" "Cyan"
& $venvPy -m pip install --quiet --upgrade pip
if (Test-Path (Join-Path $root "backend\requirements.lock")) {
    & $venvPy -m pip install --quiet --require-hashes -r backend\requirements.lock
    if ($LASTEXITCODE -ne 0) { Die "hashed install failed (see SETUP-CHECKLIST Step 4)" }
    Say "   installed from backend\requirements.lock (hashed)"
} else {
    & $venvPy -m pip install --quiet -r backend\requirements.txt
    if ($LASTEXITCODE -ne 0) { Die "pip install failed" }
    Say "   installed from backend\requirements.txt (unpinned - run T07 to freeze)"
}
& $venvPy -m pip install --quiet -r backend\requirements-dev.txt
& $venvPy -c "import fastapi, sqlalchemy, pydantic, pymysql, openpyxl, pandas, dotenv; print('   imports OK')"
# marker consumed by run.bat (step 6) so it does not reinstall every launch
Set-Content -Path (Join-Path $root ".venv\.deps_installed") -Value "deps_installed" -Encoding ASCII

Say ""
Say "== 4. Configuration ==" "Cyan"
$envPath = Join-Path $root "backend\.env"
if (-not (Test-Path $envPath)) {
    Copy-Item (Join-Path $root "backend\.env.example") $envPath
    Say "   created backend\.env from template - EDIT DB_PASSWORD BEFORE STARTING" "Yellow"
} else {
    Say "   backend\.env present"
}
$plain = Get-Content $envPath -Raw
if ($plain -match "(?m)^DB_USER=root\s*$") {
    Say "   WARN   DB_USER=root - the app should run as the least-privilege 'yfx_app' user." "Yellow"
    Say "          Run .\scripts\db-init.ps1 in an elevated shell to create it." "Yellow"
}

Say ""
Say "== 5. Frontend ==" "Cyan"
if ($SkipFrontend) {
    Say "   skipped (-SkipFrontend)"
} elseif (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Say "   skipped (npm missing)"
} elseif (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
    Push-Location (Join-Path $root "frontend")
    npm ci
    $code = $LASTEXITCODE
    Pop-Location
    if ($code -ne 0) { Die "npm ci failed" }
    Say "   node_modules installed from package-lock.json"
} else {
    Say "   node_modules present"
}

Say ""
Say "== Next ==" "Cyan"
Say "   .\scripts\verify-fast.ps1     # no database needed"
Say "   .\scripts\verify-full.ps1     # needs MySQL80 running (SETUP-CHECKLIST Step 6)"
Say "   .\run.bat                     # start backend + frontend"
exit 0
