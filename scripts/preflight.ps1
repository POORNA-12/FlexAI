#
# scripts/preflight.ps1 - read-only report of everything setup depends on.
# Never changes state. Compatible with Windows PowerShell 5.1 (no inline if-expressions).
#
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Row([string]$Name, [string]$Value, [bool]$Ok) {
    $mark = "[--]"
    if ($Ok) { $mark = "[ok]" }
    Write-Host ("{0}  {1,-22} {2}" -f $mark, $Name, $Value)
}

Write-Host "== Platform ==" -ForegroundColor Cyan
Row "OS" ([System.Environment]::OSVersion.Version.ToString()) $true
$cwd = (Get-Location).Path
Row "cwd" $cwd ($cwd -like "*yottaflexai3*")

Write-Host ""
Write-Host "== Toolchain ==" -ForegroundColor Cyan

$pyCmd = Get-Command py -ErrorAction SilentlyContinue
if ($pyCmd) {
    $v312 = py -3.12 --version 2>$null
    Row "py -3.12" "$v312" ([bool]$v312)
} else {
    Row "py launcher" "missing" $false
}

$fallback = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$fallbackExists = Test-Path $fallback
if ($fallbackExists) { Row "python 3.12 (direct)" $fallback $true } else { Row "python 3.12 (direct)" "missing" $false }

$venvPy = Join-Path $root ".venv\Scripts\python.exe"
$venvExists = Test-Path $venvPy
if ($venvExists) {
    $venvVersion = (& $venvPy -V)
    Row ".venv" "$venvVersion" $true
} else {
    Row ".venv" "missing - run scripts\setup.ps1" $false
}

if (Get-Command node -ErrorAction SilentlyContinue) { Row "node" (node -v) $true } else { Row "node" "missing" $false }
if (Get-Command npm -ErrorAction SilentlyContinue) { Row "npm" (npm -v) $true } else { Row "npm" "missing" $false }
if (Get-Command git -ErrorAction SilentlyContinue) { Row "git" (git --version) $true } else { Row "git" "missing" $false }

Write-Host ""
Write-Host "== Database ==" -ForegroundColor Cyan
$svc = Get-Service MySQL80 -ErrorAction SilentlyContinue
if ($svc) {
    Row "service MySQL80" $svc.Status ($svc.Status -eq "Running")
} else {
    Row "service MySQL80" "does not exist (SETUP-CHECKLIST Step 6)" $false
}

$client = Get-ChildItem "C:\Program Files\MySQL\MySQL Server 8.*\bin\mysql.exe" -ErrorAction SilentlyContinue |
          Sort-Object FullName -Descending | Select-Object -First 1
if ($client) { Row "mysql client" $client.FullName $true } else { Row "mysql client" "missing" $false }

$dataDir = "C:\ProgramData\MySQL\MySQL Server 8.0\Data"
$initialised = Test-Path (Join-Path $dataDir "mysql")
if ($initialised) { Row "data dir initialised" "yes" $true } else { Row "data dir initialised" "no (needs admin init)" $false }

$listening = Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue
if ($listening) { Row "port 3306" "listening" $true } else { Row "port 3306" "closed" $false }

Write-Host ""
Write-Host "== Configuration ==" -ForegroundColor Cyan
$envFile = Join-Path $root "backend\.env"
$envExists = Test-Path $envFile
if ($envExists) { Row "backend\.env" "present" $true } else { Row "backend\.env" "missing" $false }

if ($envExists) {
    $raw = Get-Content $envFile -Raw
    $usingRoot = $raw -match "(?m)^DB_USER=root\s*$"
    if ($usingRoot) { Row "DB_USER" "root (not least-privilege - run scripts\db-init.ps1)" $false } else { Row "DB_USER" "app user" $true }
    $userLine = (Select-String -Path $envFile -Pattern '^DB_USER=' -ErrorAction SilentlyContinue).Line
    Row "DB_USER line" "$userLine" ([bool]$userLine)
}

$repoExists = Test-Path (Join-Path $root ".git")
if ($repoExists) { Row "git repo" "present" $true } else { Row "git repo" "missing" $false }

Write-Host ""
Write-Host "== Ports (app) ==" -ForegroundColor Cyan
foreach ($p in 8000, 5173) {
    $inUse = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($inUse) { Row "port $p" "in use - run stop.bat" $false } else { Row "port $p" "free" $true }
}

Write-Host ""
Write-Host "Preflight is read-only. Nothing was changed." -ForegroundColor DarkGray
