#
# scripts/db-init.ps1 - one-shot MySQL 8.0 provisioning. MUST run as Administrator.
#
#   Right-click PowerShell -> "Run as administrator", then:
#       cd C:\dev\yottaflexai3
#       .\scripts\db-init.ps1
#
# What it does (idempotent, safe to re-run):
#   1. locates MySQL Server 8.0 binaries
#   2. initialises the data directory only if it is empty
#   3. registers + starts the MySQL80 service
#   4. creates the database
#   5. creates a least-privilege app user with a generated password
#      (SELECT/INSERT/UPDATE/DELETE only - no DDL, no GRANT)
#   6. writes DB_USER/DB_PASSWORD into backend\.env
#   7. prints the grants
#
# Root password rotation is NOT automatic (it can break other tools on this machine).
# To rotate root after verifying the app connects, run:
#       .\scripts\db-init.ps1 -RotateRoot
#
param(
    [switch]$RotateRoot,
    [string]$RootPassword,
    [switch]$ResetRoot,
    [string]$NewRootPassword
)

# Native tools (mysqld/mysql) write to stderr on success paths; explicit $LASTEXITCODE
# checks below provide the real error handling.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# --- elevation check ---
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "BLOCKED: this script must run as Administrator (it registers a Windows service)." -ForegroundColor Red
    Write-Host "         Right-click PowerShell -> Run as administrator, then re-run." -ForegroundColor Yellow
    exit 1
}

function Say([string]$Text, [string]$Color = "Gray") { Write-Host $Text -ForegroundColor $Color }

# Runs SQL as root, discovering the authentication mode in this order:
#   1. no password (a freshly initialised datadir)
#   2. -RootPassword parameter
#   3. secure interactive prompt
# Returns the mysql exit code.
function Invoke-RootSql([string]$Sql, [string]$SourceFile) {
    $baseArgs = @("-u", "root", "--protocol=TCP", "-h", "127.0.0.1", "-P", "3306")
    if ($SourceFile) { $baseArgs += "-e"; $baseArgs += "source $($SourceFile -replace '\\','/')" }
    else             { $baseArgs += "-e"; $baseArgs += $Sql }

    & $mysql @baseArgs "--skip-password" 2>$null
    if ($LASTEXITCODE -eq 0) { return 0 }

    $secret = $RootPassword
    if (-not $secret) {
        $secure = Read-Host "MySQL root password (input hidden)" -AsSecureString
        $secret = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
    }

    $env:MYSQL_PWD = $secret
    & $mysql @baseArgs 2>&1 | ForEach-Object { Write-Host "   $_" }
    $code = $LASTEXITCODE
    Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
    return $code
}

# --- locate MySQL 8.0 (explicitly prefer 8.0 over 8.4) ---
$bin = "C:\Program Files\MySQL\MySQL Server 8.0\bin"
if (-not (Test-Path (Join-Path $bin "mysqld.exe"))) {
    $found = Get-ChildItem "C:\Program Files\MySQL\MySQL Server 8.*\bin\mysqld.exe" -ErrorAction SilentlyContinue |
             Sort-Object FullName | Select-Object -First 1
    if (-not $found) { Write-Host "BLOCKED: MySQL Server 8.x binaries not found." -ForegroundColor Red; exit 1 }
    $bin = $found.DirectoryName
}
$mysqld = Join-Path $bin "mysqld.exe"
$mysql  = Join-Path $bin "mysql.exe"
$myIni  = "C:\ProgramData\MySQL\MySQL Server 8.0\my.ini"
$dataDir = "C:\ProgramData\MySQL\MySQL Server 8.0\Data"

Say "== 1. Binaries ==" "Cyan"
Say "   mysqld : $mysqld"
Say "   version: $(& $mysqld --version)"

Say ""
Say "== 2. Data directory ==" "Cyan"
if (-not (Test-Path (Join-Path $dataDir "mysql"))) {
    New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
    Say "   empty -> initialising (this takes ~20 s) ..."
    $initArgs = @("--initialize-insecure", "`"--datadir=$dataDir`"")
    if (Test-Path $myIni) { $initArgs += "`"--defaults-file=$myIni`"" }
    & $mysqld @initArgs
    if ($LASTEXITCODE -ne 0) { Write-Host "BLOCKED: initialisation failed (see output above)." -ForegroundColor Red; exit 1 }
    Say "   initialised (root has NO password yet)" "Yellow"
} else {
    Say "   already initialised - leaving data untouched"
}

Say ""
Say "== 2b. Root password recovery ==" "Cyan"
# Automates: stop service -> temporary --skip-grant-tables instance -> ALTER USER ->
# graceful shutdown -> restore ACLs -> start service.
#
# Why ACLs are touched: the data directory is owned by LocalSystem (the service account)
# and is not readable by an interactive administrator. An elevated user can run mysqld,
# but the process cannot open the data files until the ACL is widened for the duration
# of the recovery. The grant is removed again before this script exits.
function Test-PortOpen([string]$HostName = "127.0.0.1", [int]$Port = 3306) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect($HostName, $Port, $null, $null)
        if ($iar.AsyncWaitHandle.WaitOne(500, $false)) {
            $client.EndConnect($iar)
            return $true
        }
    } catch { return $false } finally { $client.Close() }
    return $false
}

if ($ResetRoot) {
    if (-not $NewRootPassword) {
        $secure = Read-Host "   NEW root password to set" -AsSecureString
        $NewRootPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
    }
    if (-not $NewRootPassword) { Write-Host "BLOCKED: no new password supplied." -ForegroundColor Red; exit 1 }

    $tmpDir = "C:\dev\_tmp"
    New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
    $errLog = Join-Path $tmpDir "mysqld-reset.err"
    if (Test-Path $errLog) { Remove-Item $errLog -Force }

    Say "   stopping MySQL80 ..."
    Stop-Service MySQL80 -Force -ErrorAction SilentlyContinue
    $waited = 0
    while ($waited -lt 20) {
        $state = (Get-Service MySQL80 -ErrorAction SilentlyContinue).Status
        $listening = Test-PortOpen
        if ($state -ne "Running" -and -not $listening) { break }
        Start-Sleep -Seconds 1
        $waited++
    }

    Say "   granting temporary data-directory access to $($env:USERNAME) ..."
    & icacls $dataDir /grant "$($env:USERNAME):(OI)(CI)F" /T | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "BLOCKED: could not grant data-directory access (elevation missing?)." -ForegroundColor Red
        Start-Service MySQL80 -ErrorAction SilentlyContinue
        exit 1
    }

    $initSql = Join-Path $tmpDir "mysql-init.sql"
    "ALTER USER 'root'@'localhost' IDENTIFIED BY '$NewRootPassword';" | Set-Content -Path $initSql -Encoding ASCII

    Say "   starting temporary recovery instance with --init-file ..."
    $tempArgs = "`"--defaults-file=$myIni`" `"--init-file=$initSql`" `"--log-error=$errLog`""
    $proc = Start-Process -FilePath $mysqld -ArgumentList $tempArgs -PassThru

    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (Test-PortOpen) { $ready = $true; break }
    }

    if (-not $ready) {
        Say "   recovery instance did not listen; last error-log lines:" "Yellow"
        if (Test-Path $errLog) { Get-Content $errLog -Tail 20 | ForEach-Object { Write-Host "     $_" } }
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Remove-Item $initSql -Force -ErrorAction SilentlyContinue
        & icacls $dataDir /remove:g "$($env:USERNAME)" /T | Out-Null
        Start-Service MySQL80 -ErrorAction SilentlyContinue
        Write-Host "BLOCKED: recovery instance failed to start (log above)." -ForegroundColor Red
        exit 1
    }

    $env:MYSQL_PWD = $NewRootPassword
    & $mysql -u root --protocol=TCP -h 127.0.0.1 -P 3306 -e "SELECT 1;" 2>&1 | Out-Null
    $resetCode = $LASTEXITCODE
    Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue

    Say "   shutting the recovery instance down ..."
    $mysqladmin = Join-Path $bin "mysqladmin.exe"
    if (Test-Path $mysqladmin) {
        $env:MYSQL_PWD = $NewRootPassword
        & $mysqladmin -u root --protocol=TCP -h 127.0.0.1 -P 3306 shutdown 2>$null | Out-Null
        Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
    $waited = 0
    while ($waited -lt 15) {
        if (-not (Test-PortOpen)) { break }
        Start-Sleep -Seconds 1
        $waited++
    }

    Remove-Item $initSql -Force -ErrorAction SilentlyContinue

    Say "   restoring data-directory ACL ..."
    & icacls $dataDir /remove:g "$($env:USERNAME)" /T | Out-Null

    Start-Service MySQL80 -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3

    if ($resetCode -ne 0) {
        Write-Host "BLOCKED: root reset failed; MySQL80 restarted with the old credentials." -ForegroundColor Red
        exit 1
    }
    Say "   root password reset; MySQL80 restarted; ACL restored" "Green"
    $RootPassword = $NewRootPassword
}

Say ""
Say "== 3. Service ==" "Cyan"
$svc = Get-Service MySQL80 -ErrorAction SilentlyContinue
if (-not $svc) {
    $svcArgs = @("--install", "MySQL80")
    if (Test-Path $myIni) { $svcArgs += "--defaults-file=$myIni" }
    & $mysqld @svcArgs
    if ($LASTEXITCODE -ne 0) { Write-Host "BLOCKED: service install failed." -ForegroundColor Red; exit 1 }
    Start-Sleep -Seconds 2
    $svc = Get-Service MySQL80
}
if ($svc.Status -ne "Running") { Start-Service MySQL80; Start-Sleep -Seconds 2 }
$svc.Refresh()
Say "   MySQL80: $($svc.Status)"
if ($svc.Status -ne "Running") { Write-Host "BLOCKED: service did not start. Check the Windows event log." -ForegroundColor Red; exit 1 }

Say ""
Say "== 4. Database + app user ==" "Cyan"

# app password: 24 chars, no shell-hostile characters
$chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
$appPassword = -join (1..24 | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })

$sql = @"
CREATE DATABASE IF NOT EXISTS supplier_schedule_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'yfx_app'@'localhost' IDENTIFIED BY '$appPassword';
ALTER USER 'yfx_app'@'localhost' IDENTIFIED BY '$appPassword';
GRANT SELECT, INSERT, UPDATE, DELETE ON supplier_schedule_manager.* TO 'yfx_app'@'localhost';
FLUSH PRIVILEGES;
"@

$tmp = Join-Path $env:TEMP "yfx_init_$([guid]::NewGuid().ToString('N')).sql"
Set-Content -Path $tmp -Value $sql -Encoding ASCII
$code = Invoke-RootSql -Sql "" -SourceFile $tmp
Remove-Item $tmp -Force -ErrorAction SilentlyContinue
if ($code -ne 0) {
    Write-Host "BLOCKED: could not create the database/app user." -ForegroundColor Red
    Write-Host "         root already has a password and the one supplied was rejected." -ForegroundColor Yellow
    Write-Host "         Re-run with the real password:  .\scripts\db-init.ps1 -RootPassword '<pw>'" -ForegroundColor Yellow
    Write-Host "         Forgot it? See 'Lost root password' in docs/01-setup/RUNBOOK.md." -ForegroundColor Yellow
    exit 1
}
Say "   database supplier_schedule_manager ready"
Say "   user yfx_app created with a generated password"

$schemaFile = Join-Path $root "database\schema.sql"
if (Test-Path $schemaFile) {
    Say "   applying schema from database\schema.sql ..."
    $code = Invoke-RootSql -Sql "" -SourceFile $schemaFile
    if ($code -ne 0) {
        Write-Host "WARN: schema apply reported non-zero ($code); continuing." -ForegroundColor Yellow
    } else {
        Say "   schema applied successfully"
    }
}

Say ""
Say "== 5. Grants ==" "Cyan"
[void](Invoke-RootSql -Sql "SHOW GRANTS FOR 'yfx_app'@'localhost';")

Say ""
Say "== 6. backend\.env ==" "Cyan"
$envPath = Join-Path $root "backend\.env"
if (-not (Test-Path $envPath)) { Copy-Item (Join-Path $root "backend\.env.example") $envPath }
$lines = Get-Content $envPath
$lines = $lines | ForEach-Object {
    if ($_ -match '^DB_USER=')      { 'DB_USER=yfx_app' }
    elseif ($_ -match '^DB_PASSWORD=') { "DB_PASSWORD=$appPassword" }
    elseif ($_ -match '^DB_HOST=')  { 'DB_HOST=127.0.0.1' }
    elseif ($_ -match '^DB_PORT=')  { 'DB_PORT=3306' }
    elseif ($_ -match '^DATABASE_URL=') { "# $_" }
    else                            { $_ }
}
Set-Content -Path $envPath -Value $lines -Encoding UTF8
& icacls $envPath /inheritance:r /grant:r "$($env:USERNAME):(F)" | Out-Null
Say "   DB_USER/DB_PASSWORD written; file ACL restricted to $($env:USERNAME)"

Say ""
Say "== 7. Root password ==" "Cyan"
if ($RotateRoot) {
    $secure = Read-Host "   new root password" -AsSecureString
    $newPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
    $code = Invoke-RootSql -Sql "ALTER USER 'root'@'localhost' IDENTIFIED BY '$newPlain';"
    if ($code -eq 0) { Say "   root password rotated. Store it in your password manager." "Green" }
    else { Write-Host "   FAILED to rotate root; the previous password is unchanged." -ForegroundColor Red }
} else {
    Say "   skipped - verify the app first, then run: .\scripts\db-init.ps1 -RotateRoot" "Yellow"
}

Say ""
Say "== Next ==" "Cyan"
Say "   .\scripts\db-health.ps1        # expect RESULT: HEALTHY"
Say "   .\scripts\verify-full.ps1      # seed + full test suite"
exit 0
