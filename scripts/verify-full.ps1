#
# scripts/verify-full.ps1 - database-backed verification.
# Requires MySQL80 running and backend\.env populated.
#
# Usage:  .\scripts\verify-full.ps1
# Exit :  0 = PASS, 1 = FAIL
#
# NOTE: ErrorActionPreference is "Continue" on purpose - native tools write to stderr on
# success paths (pip/pytest warnings) and "Stop" would abort on harmless output.
#
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "FAIL: .venv missing - run scripts\setup.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "== 1. Environment ==" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "verify-fast.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "RESULT: FAIL (environment gate)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "== 2. Database health ==" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "db-health.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "RESULT: FAIL (database unhealthy)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "== 3. Seed (only if empty) ==" -ForegroundColor Cyan
$seedScript = Join-Path $env:TEMP "yfx_seed_probe.py"
@"
import sys
from pathlib import Path
root = r"$root"
if root not in sys.path:
    sys.path.insert(0, root)

from backend.database import init_db, SessionLocal
from backend import models

init_db(safe_only=True)
db = SessionLocal()
try:
    count = db.query(models.PurchaseOrder).count()
    print(f"purchase_orders={count}")
    if count == 0:
        from backend.services import seed_database_from_generator
        result = seed_database_from_generator("full")
        print(f"seeded: {result['purchase_order_count']} POs, {result['total_business_records']} business rows")
finally:
    db.close()
"@ | Set-Content -Path $seedScript -Encoding ASCII
$env:PYTHONPATH = $root
& $py $seedScript
$code = $LASTEXITCODE
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
Remove-Item $seedScript -Force -ErrorAction SilentlyContinue
if ($code -ne 0) {
    Write-Host "RESULT: FAIL (seed step)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "== 4. Full test suite ==" -ForegroundColor Cyan
& $py -m pytest -q 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "RESULT: FAIL (tests)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "RESULT: PASS" -ForegroundColor Green
exit 0
