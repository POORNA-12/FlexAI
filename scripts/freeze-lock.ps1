#
# scripts/freeze-lock.ps1 - regenerate backend\requirements.lock from the CURRENT environment.
#
# "Pin by measurement" (ADR-0001 D5): the lock is derived from the packages that actually
# installed and imported successfully - never from a version list typed by hand.
#
# Usage:  .\scripts\freeze-lock.ps1
# Exit :  0 = lock written and validated, 1 = blocked
#
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "BLOCKED: .venv missing - run scripts\setup.ps1" -ForegroundColor Red; exit 1 }

$freeze = Join-Path $env:TEMP "yfx_freeze.txt"
$report = Join-Path $env:TEMP "yfx_report.json"
$lock   = Join-Path $root "backend\requirements.lock"

Write-Host "== 1. Freeze the current environment ==" -ForegroundColor Cyan
& $py -m pip freeze --all > $freeze
if ($LASTEXITCODE -ne 0) { Write-Host "BLOCKED: pip freeze failed" -ForegroundColor Red; exit 1 }
$pinned = (Get-Content $freeze | Measure-Object -Line).Lines
Write-Host "   $pinned distributions frozen"

Write-Host "== 2. Resolve the runtime closure with hashes ==" -ForegroundColor Cyan
& $py -m pip install --dry-run --ignore-installed --quiet --report $report -c $freeze -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "BLOCKED: resolution failed (network or index issue)" -ForegroundColor Red; exit 1 }

Write-Host "== 3. Write backend\requirements.lock ==" -ForegroundColor Cyan
$data = Get-Content $report -Raw | ConvertFrom-Json
$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine("# Hashed lock generated from a measured install (ADR-0001 D5).")
[void]$sb.AppendLine("# Install with: pip install --require-hashes -r backend/requirements.lock")
[void]$sb.AppendLine("# Regenerate with: .\scripts\freeze-lock.ps1")
[void]$sb.AppendLine("")
$withHash = 0
foreach ($item in ($data.install | Sort-Object { $_.metadata.name.ToLower() })) {
    $name = $item.metadata.name
    $version = $item.metadata.version
    $sha = $item.download_info.archive_info.hashes.sha256
    if ($sha) {
        [void]$sb.AppendLine("$name==$version ``")
        [void]$sb.AppendLine("    --hash=sha256:$sha")
        $withHash++
    } else {
        [void]$sb.AppendLine("$name==$version")
    }
}
Set-Content -Path $lock -Value $sb.ToString().TrimEnd() -Encoding UTF8
Write-Host "   $($data.install.Count) packages, $withHash hashed"

Write-Host "== 4. Validate the lock ==" -ForegroundColor Cyan
& $py -m pip install --dry-run --require-hashes --quiet -r backend\requirements.lock
if ($LASTEXITCODE -ne 0) { Write-Host "BLOCKED: the generated lock does not satisfy --require-hashes" -ForegroundColor Red; exit 1 }

Remove-Item $freeze, $report -Force -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "RESULT: PASS - backend\requirements.lock regenerated and validated" -ForegroundColor Green
exit 0
