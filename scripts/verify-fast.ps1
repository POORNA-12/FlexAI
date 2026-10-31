#
# scripts/verify-fast.ps1 - environment gate that does NOT need MySQL.
# Passes only if: interpreter is the project venv, imports resolve, lint runs,
# pytest collects, and the database-free smoke suite passes.
#
# Usage:  .\scripts\verify-fast.ps1
# Exit :  0 = PASS, 1 = FAIL
#
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$failures = New-Object System.Collections.Generic.List[string]

function Section([string]$Name) {
    Write-Host ""
    Write-Host "== $Name ==" -ForegroundColor Cyan
}

function Check([string]$Name, [scriptblock]$Action) {
    try {
        & $Action
        Write-Host "   PASS  $Name" -ForegroundColor Green
    } catch {
        Write-Host "   FAIL  $Name -> $($_.Exception.Message)" -ForegroundColor Red
        $failures.Add($Name)
    }
}

Section "1. Interpreter"
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "   FAIL  .venv missing -> run: py -3.12 -m venv .venv" -ForegroundColor Red
    exit 1
}
Check "venv python is 3.12.x" {
    $v = & $py -c "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($v.Trim() -ne "3.12") { throw "found $v" }
}
Check "system site-packages disabled" {
    $cfg = Get-Content (Join-Path $root ".venv\pyvenv.cfg") -Raw
    if ($cfg -notmatch "include-system-site-packages\s*=\s*false") { throw "include-system-site-packages is not false" }
}

Section "2. Imports"
Check "runtime dependencies import" {
    & $py -c "import fastapi, sqlalchemy, pydantic, pymysql, openpyxl, pandas, dotenv; print('imports OK')" | Out-Null
}
Check "application module imports without a database" {
    & $py -c "import backend.config, backend.models, backend.business_rules, backend.validation, backend.generator; print('modules OK')" | Out-Null
}
Check "configuration validates" {
    & $py -c "from backend.config import get_settings; s=get_settings(); assert s.db_password; print('config OK', s.db_host, s.db_port)" | Out-Null
}

Section "3. Static analysis (advisory)"
& $py -m ruff check backend tests 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Host "   WARN  ruff reported findings (advisory during setup, blocking in Phase B)" -ForegroundColor Yellow
}

Section "4. Tests"
Check "pytest collects" {
    & $py -m pytest --collect-only -q 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "collection failed" }
}
Check "smoke suite passes (no DB)" {
    & $py -m pytest -m "not db" -q 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "smoke tests failed" }
}

Section "RESULT"
if ($failures.Count -eq 0) {
    Write-Host "RESULT: PASS" -ForegroundColor Green
    exit 0
}
Write-Host "RESULT: FAIL ($($failures.Count) check(s))" -ForegroundColor Red
$failures | ForEach-Object { Write-Host " - $_" }
exit 1
