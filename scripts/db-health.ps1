#
# scripts/db-health.ps1 - prove that MySQL is actually usable by the app.
# Reports: service state, server version, connectivity, schema, live row counts, grants.
#
# Usage:  .\scripts\db-health.ps1
# Exit :  0 = healthy, 1 = unhealthy
#
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# --- read backend/.env (authoritative, ADR-0001 D4) ---
$envFile = Join-Path $root "backend\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "FAIL: backend\.env not found (copy backend\.env.example)" -ForegroundColor Red
    exit 1
}
$cfg = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
        $cfg[$matches[1]] = $matches[2].Trim('"').Trim("'")
    }
}
$dbHost = if ($cfg.ContainsKey("DB_HOST")) { $cfg["DB_HOST"] } else { "127.0.0.1" }
$dbPort = if ($cfg.ContainsKey("DB_PORT")) { $cfg["DB_PORT"] } else { "3306" }
$dbUser = if ($cfg.ContainsKey("DB_USER")) { $cfg["DB_USER"] } else { "yfx_app" }
$dbName = if ($cfg.ContainsKey("DB_NAME")) { $cfg["DB_NAME"] } else { "supplier_schedule_manager" }
$dbPass = $cfg["DB_PASSWORD"]

# --- locate the client (prefer 8.0 explicitly; 8.4 is also installed on this machine) ---
$mysql = $null
$mysql80 = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
if (Test-Path $mysql80) {
    $mysql = Get-Item $mysql80
} else {
    $mysql = Get-ChildItem "C:\Program Files\MySQL\MySQL Server 8.*\bin\mysql.exe" -ErrorAction SilentlyContinue |
             Sort-Object FullName | Select-Object -First 1
}
if (-not $mysql) {
    Write-Host "FAIL: mysql client not found under C:\Program Files\MySQL" -ForegroundColor Red
    exit 1
}

Write-Host "== Service ==" -ForegroundColor Cyan
$svc = Get-Service MySQL80 -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host "   FAIL  service 'MySQL80' does not exist (see SETUP-CHECKLIST Step 6)" -ForegroundColor Red
    exit 1
}
Write-Host "   MySQL80: $($svc.Status)"
if ($svc.Status -ne "Running") {
    Write-Host "   FAIL  service is not running -> Start-Service MySQL80 (admin)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "== Connection ==" -ForegroundColor Cyan
$env:MYSQL_PWD = $dbPass
$version = & $mysql.FullName --protocol=TCP -h $dbHost -P $dbPort -u $dbUser -N -B -e "SELECT VERSION();" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "   FAIL  cannot connect as $dbUser -> $version" -ForegroundColor Red
    Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "   server : $version"
Write-Host "   target : ${dbHost}:${dbPort}/${dbName} as $dbUser"

Write-Host ""
Write-Host "== Schema ==" -ForegroundColor Cyan
$tables = & $mysql.FullName --protocol=TCP -h $dbHost -P $dbPort -u $dbUser -N -B -e `
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$dbName';" 2>&1
Write-Host "   tables in ${dbName}: $tables"
if ([int]$tables -eq 0) {
    Write-Host "   WARN  schema not created yet (the app creates it on startup)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "== Row counts ==" -ForegroundColor Cyan
foreach ($t in @("purchase_orders","po_lines","acknowledgements","change_requests","approvals","inventory_plans","schedule_impacts")) {
    $n = & $mysql.FullName --protocol=TCP -h $dbHost -P $dbPort -u $dbUser -N -B -e "SELECT COUNT(*) FROM $dbName.$t;" 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host ("   {0,-18} {1}" -f $t, $n) }
}

Write-Host ""
Write-Host "== Grants ==" -ForegroundColor Cyan
& $mysql.FullName --protocol=TCP -h $dbHost -P $dbPort -u $dbUser -N -B -e "SHOW GRANTS;" 2>&1 | ForEach-Object { Write-Host "   $_" }
Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "RESULT: HEALTHY" -ForegroundColor Green
exit 0
