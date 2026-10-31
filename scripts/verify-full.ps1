#
# scripts/verify-full.ps1 - database-backed verification.
# Requires MySQL80 running and backend\.env populated.
#
# Usage:  .\scripts\verify-full.ps1
# Exit :  0 = PASS, 1 = FAIL
#
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "FAIL: .venv missing - run scripts\setup.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "== Database health ==" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "db-health.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "RESULT: FAIL (database unhealthy)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "== Seed (only if empty) ==" -ForegroundColor Cyan
& $py -c @"
from backend.database import init_db, SessionLocal
from backend import models
init_db(safe_only=True)
db = SessionLocal()
try:
    n = db.query(models.PurchaseOrder).count()
    print(f'purchase_orders={n}')
    if n == 0:
        from backend.services import seed_database_from_generator
        r = seed_database_from_generator('full')
        print(f'seeded: {r[\"purchase_order_count\"]} POs, {r[\"total_business_records\"]} business rows')
finally:
    db.close()
"@
if ($LASTEXITCODE -ne 0) {
    Write-Host "RESULT: FAIL (seed step)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "== Full test suite (db marker) ==" -ForegroundColor Cyan
& $py -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "RESULT: FAIL (tests)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "RESULT: PASS" -ForegroundColor Green
exit 0
