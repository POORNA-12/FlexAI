# SETUP CHECKLIST — `yottaflexai3` on Windows

**Rule:** every step has a **command** and **expected output**. If output differs, use the remedy — do not skip.
**Time:** ~20 min cold, ~2 min warm. **Admin:** needed only at Step 6.
Tick `[x]` as you go; the file is evidence.

```text
Project root : C:\dev\yottaflexai3
Python       : 3.12.x  (via py launcher)
DB           : MySQL 8.0 service "MySQL80" on 127.0.0.1:3306
App user     : yfx_app (SELECT/INSERT/UPDATE/DELETE only)
```

---

## Step 0 — Open the right shell

```powershell
cd C:\dev\yottaflexai3
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
```

**Expected:** prompt returns silently (no error). `Get-Location` shows `C:\dev\yottaflexai3`.
**Remedy:** if `Set-ExecutionPolicy` is blocked by policy, use `powershell -ExecutionPolicy Bypass -File .\scripts\verify-fast.ps1` for every script call.

☐ done

---

## Step 1 — Verify prerequisites

```powershell
py -3.12 --version
node -v
npm -v
git --version
```

**Expected:**
```
Python 3.12.x
v18.0.0  (or higher — host has v25.8.2)
9.0.0    (or higher)
git version 2.4x
```
**If `py` is not found →** Step 2. **If node/npm missing →** install Node LTS from nodejs.org (AR-1 note: host Node 25 is non-LTS but works).

☐ done

---

## Step 2 — Install Python 3.12 (per-user, no admin)

```powershell
winget install --id Python.Python.3.12 -e --scope user --accept-package-agreements --accept-source-agreements
```

**Close and reopen the terminal** (the installer updates PATH; an already-open shell keeps the old one), then:

```powershell
py -0p
py -3.12 --version
```

**Expected:**
```
 -V:3.12  C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe
Python 3.12.x
```

**Remedy — `'py' is not recognized` even in a new terminal:** call the interpreter directly.
The winget install places it at (verified on this machine):
```
C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe
```
Use that absolute path wherever `py -3.12` appears below, e.g.
`& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv`.
`scripts\setup.ps1` already tries `py` first and falls back to this path automatically.

**Remedy (no winget):** download `python-3.12.10-amd64.exe` from python.org → run → tick **"Add python.exe to PATH"** and **"py launcher"** → *Install for me only*.

⚠️ Do **not** use the Microsoft Store alias (`WindowsApps\python.exe`) for the venv — it is a 2-byte stub and auto-updates.

☐ done

---

## Step 3 — Create the virtualenv

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -V
python -c "import sysconfig,sys;print(sysconfig.get_path('purelib'));print(sys.prefix)"
```

**Expected:** `Python 3.12.x`, and both paths point inside `C:\dev\yottaflexai3\.venv\`.
**Remedy:** if activation is refused → Step 0's execution policy. If `pyvenv.cfg` shows `include-system-site-packages = true`, delete `.venv` and re-run without `--system-site-packages` (default is false).

```powershell
Get-Content .venv\pyvenv.cfg
```
**Expected:** `home = C:\Users\<you>\AppData\Local\Programs\Python\Python312` and `include-system-site-packages = false`.
**This is the check that would have caught the broken `C:\Users\kowshik` venv.**

☐ done

---

## Step 4 — Install dependencies (hashed lock)

```powershell
python -m pip install --upgrade pip
python -m pip install --require-hashes -r backend\requirements.lock
python -c "import fastapi, sqlalchemy, pydantic, pymysql, openpyxl, pandas, dotenv; print('imports OK')"
```

**Expected:** `imports OK` and pip exits 0.
**Remedy:**
- `No matching distribution` → a wheel is missing for your Python build. `python -m pip install -r backend\requirements.txt` (unpinned) to unblock, then re-freeze (T07) and report.
- Hash mismatch → the lock and index disagree (supply-chain signal). Stop and escalate to Chandra.

☐ done

---

## Step 5 — Configure secrets

```powershell
Copy-Item backend\.env.example backend\.env
notepad backend\.env      # set DB_PASSWORD (real value) and DB_USER / DB_HOST / DB_PORT
icacls backend\.env /inheritance:r /grant:r "$env:USERNAME:(F)"
```

**Expected:** `icacls` prints `Successfully processed 1 files`.
**Verify the file is not tracked:**

```powershell
git check-ignore -v backend\.env
```
**Expected:** `.gitignore:3:backend/.env  backend/.env`

**Verify no credential is hardcoded:**

```powershell
Get-ChildItem -Recurse -File -Include *.py,*.bat,*.ps1 |
  Select-String -Pattern "Aqswdefr" -SimpleMatch
```
**Expected:** no output.
**Remedy:** if it matches, you are on a pre-T08 commit — `git reset --hard` is not the fix; restore `backend\config.py` changes (T08).

☐ done

---

## Step 6 — MySQL 8.0 service (ADMIN once)

Open **PowerShell as Administrator** in `C:\dev\yottaflexai3`:

```powershell
$MYSQL = "C:\Program Files\MySQL\MySQL Server 8.0\bin"
$DATA  = "C:\ProgramData\MySQL\MySQL Server 8.0\Data"

# 6a. initialize only if the data dir is empty
if (-not (Test-Path "$DATA\mysql")) {
  & "$MYSQL\mysqld.exe" --initialize-insecure --datadir="$DATA" --console
}

# 6b. register + start the service
& "$MYSQL\mysqld.exe" --install MySQL80 --defaults-file="C:\ProgramData\MySQL\MySQL Server 8.0\my.ini"
Start-Service MySQL80
Get-Service MySQL80
```

**Expected:** `Status = Running`; `ERROR 1060` is gone.
**Remedy:**
- `Access is denied` → you are not elevated.
- `The service already exists` → `sc.exe delete MySQL80` then repeat 6b.
- Port 3306 busy → `Get-NetTCPConnection -LocalPort 3306`; if MySQL 8.4 took it, `Stop-Service` that one and re-run.

```powershell
& "$MYSQL\mysql.exe" -u root --skip-password -e "SELECT VERSION();"
```
**Expected:** `8.0.x`.

☐ done

---

## Step 7 — Least-privilege app user + root rotation

Still in the elevated shell (root password is created here):

```powershell
$MYSQL = "C:\Program Files\MySQL\MySQL Server 8.0\bin"
& "$MYSQL\mysql.exe" -u root --skip-password -e @"
CREATE DATABASE IF NOT EXISTS supplier_schedule_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'yfx_app'@'localhost' IDENTIFIED BY '<APP_PASSWORD>';
GRANT SELECT, INSERT, UPDATE, DELETE ON supplier_schedule_manager.* TO 'yfx_app'@'localhost';
FLUSH PRIVILEGES;
"@

& "$MYSQL\mysql.exe" -u root --skip-password -e "SHOW GRANTS FOR 'yfx_app'@'localhost';"
```

**Expected — exactly two GRANT lines, 4 privileges, no DDL:**
```
GRANT USAGE ON *.* TO `yfx_app`@`localhost`
GRANT SELECT, INSERT, UPDATE, DELETE ON `supplier_schedule_manager`.* TO `yfx_app`@`localhost`
```

**Verify the app can connect as `yfx_app` BEFORE touching root:**

```powershell
& "$MYSQL\mysql.exe" -u yfx_app -p"<APP_PASSWORD>" -e "SELECT 1 FROM supplier_schedule_manager.purchase_orders LIMIT 1;" 2>&1
```
A "table doesn't exist" error is **success** (connect + grant work). `Access denied` is failure.

**Only now** rotate root:

```powershell
& "$MYSQL\mysql.exe" -u root --skip-password -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '<NEW_ROOT_PASSWORD>';"
```

**Remedy:** if anything fails before the rotation, root is still passwordless — repeat. After rotation, the old value is dead; update `backend\.env` only for `yfx_app`.

☐ done

---

## Step 8 — Frontend dependencies

```powershell
cd frontend
npm ci
cd ..
```

**Expected:** `added N packages` and `frontend\node_modules` exists. `npm ci` is used (not `npm install`) so `package-lock.json` is authoritative.

☐ done

---

## Step 9 — Verify (fast, then full)

```powershell
.\scripts\verify-fast.ps1
```
**Expected:** `.venv python 3.12.x` · `imports OK` · `ruff` runs · `pytest --collect-only` OK · smoke tests pass · `RESULT: PASS`.
**This step must pass with MySQL stopped** — it proves the environment is sound without the DB.

```powershell
.\scripts\verify-full.ps1
```
**Expected:** DB health OK → seed (if empty) → `30 passed` → `RESULT: PASS`.

☐ done

---

## Step 10 — Run the application

```powershell
.\run.bat
```
**Expected:** backend console on `127.0.0.1:8000`, Vite on `5173`; `http://localhost:8000/health` → `{"status":"healthy","database_connected":true,...}`.

Stop with `.\stop.bat`.

☐ done

---

## Step 11 — Record evidence

Append to `docs\03-verification\VERIFICATION-LOG.md`:

```markdown
### <date> — cold start by <name>
- py -3.12 --version : Python 3.12.x
- verify-fast.ps1    : PASS
- verify-full.ps1    : PASS (30 passed)
- deviations         : none | <list>
```

☐ done

---

## Troubleshooting quick table

| Symptom | Cause | Fix |
|---|---|---|
| `python` opens Microsoft Store | Store alias wins PATH | use `py -3.12`; reorder PATH; disable App Execution Aliases |
| `venv\Scripts\activate` not found | a foreign/Windows-other-user venv | delete `.venv`, Step 3 |
| `ERROR 2003 (10061)` | no service on 3306 | Step 6 |
| `ERROR 1045 Access denied` | wrong creds in `backend\.env` | Step 5/7 |
| `ModuleNotFoundError: backend` | wrong cwd | run from project root |
| PowerShell blocks `.ps1` | execution policy | Step 0 |
| Port 8000 in use | stale uvicorn | `.\stop.bat` |
