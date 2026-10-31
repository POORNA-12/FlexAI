# RUNBOOK — operate, reset, recover

**Root:** `C:\dev\yottaflexai3` · **Backend:** uvicorn `127.0.0.1:8000` · **Frontend:** Vite `5173` · **DB:** MySQL 8.0 `127.0.0.1:3306`

## Start / stop

```powershell
.\run.bat          # checks python/node/npm → .venv → deps → DB probe → uvicorn + vite
.\stop.bat         # kills whatever listens on 8000 and 5173
```

Partial start (backend only):

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Health probe:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
# expect: status=healthy, database_connected=True
```

## Database

```powershell
Get-Service MySQL80                        # Running?
Start-Service MySQL80                      # (admin)
.\scripts\db-health.ps1                    # version + schema + row counts
```

**First-time init** (only if `C:\ProgramData\MySQL\MySQL Server 8.0\Data` has no `mysql` folder) — see `SETUP-CHECKLIST.md` Step 6. Do not `--initialize` a populated data dir; it will refuse or destroy state.

## Reseed (destructive)

```powershell
# requires confirm — replaces ALL operational rows, keeps the schema
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/data-generator/seed?scale=full&confirm=true"
```

Scale options: `full` (10,000 POs, ~70k rows, ~13 s) · `dev` (200 POs).

⚠️ **Known defect (Audit AUDIT-002):** this endpoint has no authentication and is reachable by a drive-by POST from any web page while the dev server runs. Until Phase B fixes it: do not leave the backend running while browsing untrusted sites.

## Credentials

| Secret | Where | Rotation |
|---|---|---|
| `yfx_app` DB password | `backend\.env` (`DB_PASSWORD`) | change in MySQL, then update `.env`, restart backend |
| `root` DB password | not stored in the project | rotate via `ALTER USER 'root'@'localhost' IDENTIFIED BY '…'` |
| Browser/API tokens | none yet (no auth layer) | n/a |

```powershell
# rotate the app user's password
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -e "ALTER USER 'yfx_app'@'localhost' IDENTIFIED BY '<new>';"
# then edit backend\.env and restart
```

**If a secret is committed by accident:**

```powershell
git log --oneline -- backend/.env          # must be empty
git rm --cached backend/.env               # untrack
# rotate the credential — removing the file is not enough
```

## Lost root password (MySQL 8.0 on Windows)

`db-init.ps1` stops with `ERROR 1045 Access denied for user 'root'@'localhost'` when the data
directory was initialised earlier with a password nobody remembers. Recover it like this —
**Administrator shell required**.

```powershell
cd C:\dev\yottaflexai3
.\scripts\db-init.ps1 -ResetRoot -NewRootPassword 'NewRootPass123'
```

That is the whole procedure. It stops the service, starts a temporary `--skip-grant-tables`
instance, sets the password, shuts it down cleanly, restores ACLs, restarts `MySQL80`, then
creates the database and `yfx_app`.

**Why it needs two extra steps under the hood (and why a naive attempt fails):** the data
directory is owned by `LocalSystem` (the service account) and is not accessible to an
interactive administrator. An elevated user can *run* `mysqld.exe`, but the process cannot
open the data files. The script therefore grants the current user temporary access and
removes it afterwards:

```powershell
$DATA = "C:\ProgramData\MySQL\MySQL Server 8.0\Data"
icacls $DATA /grant "$($env:USERNAME):(OI)(CI)F" /T     # before
# ... recovery ...
icacls $DATA /remove:g "$($env:USERNAME)" /T            # after
```

Manual equivalent, if you ever need it:

```powershell
$BIN = "C:\Program Files\MySQL\MySQL Server 8.0\bin"
$INI = "C:\ProgramData\MySQL\MySQL Server 8.0\my.ini"
$DATA = "C:\ProgramData\MySQL\MySQL Server 8.0\Data"

Stop-Service MySQL80
icacls $DATA /grant "$($env:USERNAME):(OI)(CI)F" /T
Start-Process "$BIN\mysqld.exe" -ArgumentList "--defaults-file=$INI","--skip-grant-tables","--log-error=C:\dev\_tmp\reset.err" -PassThru | Out-Null
Start-Sleep -Seconds 8

& "$BIN\mysql.exe" -u root --protocol=TCP -h 127.0.0.1 -P 3306 -e "FLUSH PRIVILEGES; ALTER USER 'root'@'localhost' IDENTIFIED BY 'NewRootPass123';"
& "$BIN\mysqladmin.exe" -u root --protocol=TCP -h 127.0.0.1 -P 3306 shutdown

icacls $DATA /remove:g "$($env:USERNAME)" /T
Start-Service MySQL80
```

⚠️ `--skip-grant-tables` accepts **any** connection while it runs. Keep it to seconds, and
never leave the temporary instance running. This resets the password; it does not recover it.
The ACL grant must be removed afterwards, or an ordinary user gains write access to the
database files.

## Backup / restore (before any reseed or schema change)

```powershell
$MYSQL = "C:\Program Files\MySQL\MySQL Server 8.0\bin"
& "$MYSQL\mysqldump.exe" -u root -p --single-transaction --routines supplier_schedule_manager > "C:\dev\_backups\ssm-$(Get-Date -f yyyyMMdd-HHmm).sql"

# restore
& "$MYSQL\mysql.exe" -u root -p supplier_schedule_manager < "C:\dev\_backups\ssm-20261031-0900.sql"
```

## Verify

```powershell
.\scripts\verify-fast.ps1     # no DB needed: interpreter, imports, lint, collect, smoke
.\scripts\verify-full.ps1     # DB + full pytest
```

## Recovery scenarios

| Symptom | First action | If that fails |
|---|---|---|
| App won't start, DB warning in console | `Get-Service MySQL80` → `Start-Service` | `scripts\db-health.ps1`; check `my.ini` port |
| `ModuleNotFoundError` | `.\.venv\Scripts\python.exe -m pip install --require-hashes -r backend\requirements.lock` | recreate `.venv` (checklist Step 3) |
| Venv looks wrong (`pyvenv.cfg` points elsewhere) | delete `.venv`, recreate | — |
| Bad local change | `git status` → `git restore <file>` | `git reset --hard c0197f8` (baseline) |
| Port busy | `.\stop.bat` | `Get-NetTCPConnection -LocalPort 8000 \| Select OwningProcess` → `Stop-Process -Id <pid>` |
| Reseeded by accident | restore latest `mysqldump` | reseed `full` (deterministic seed 20261022 → reproducible rows) |

## Known limitations (carry into Phase B)

- No authentication/authorisation on any endpoint (AUDIT-001).
- Destructive reseed is anonymous (AUDIT-002).
- Approval thresholds not enforced at decision time (AUDIT-004); `ScheduleImpact` never recomputed (AUDIT-006).
- Price change requests are never generated (spec V1); approval decisions are random (spec V2); no SQL seed / manifest (spec V3).
