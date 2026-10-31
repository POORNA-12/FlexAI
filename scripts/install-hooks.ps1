#
# scripts/install-hooks.ps1 - install the versioned pre-commit secret scan.
# Safe to re-run; overwrites only the hooks this script owns.
#
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$hooksDir = Join-Path $root ".git\hooks"
if (-not (Test-Path $hooksDir)) {
    Write-Host "BLOCKED: .git\hooks not found - is this a git repository?" -ForegroundColor Red
    exit 1
}

$source = Join-Path $root "scripts\pre-commit"
$target = Join-Path $hooksDir "pre-commit"
Copy-Item $source $target -Force

# Git for Windows executes hooks through its bundled sh, so the mode bit is advisory,
# but set it anyway for WSL/Linux checkouts.
git update-index --chmod=+x scripts/pre-commit 2>$null | Out-Null

Write-Host "Installed: $target" -ForegroundColor Green
Write-Host ""
Write-Host "Test it (must be rejected):" -ForegroundColor Cyan
Write-Host '  "DB_PASSWORD=SuperSecret123" | Out-File -Append backend\config.py'
Write-Host '  git add backend\config.py ; git commit -m "should fail"'
Write-Host '  git restore --staged backend\config.py ; git checkout -- backend\config.py'
exit 0
