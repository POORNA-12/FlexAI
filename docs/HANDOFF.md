# HANDOFF — yottaflexai3 · 2026-10-31 05:30 UTC

**Reader:** any agent or engineer resuming this work (Antigravity session or later).
**Writer:** Abhi (Execution Authority) · `~/AGENTS.md` governance
**Status:** ⛔ **T09 blocked** — MySQL root password is lost. Nothing else is blocked.

---

## 1. Read this first — two copies of the tree exist

| Tree | Path | Role |
|---|---|---|
| **REAL RUN TARGET** | `C:\dev\yottaflexai3` | Windows. Working here. Edit **only** this. |
| Stale remnant | `~/Kowshik/yottaflexai3` (WSL) | Pre-relocation copy, **incomplete** (no `backend/`, no `scripts/`). Do not work here. Slated for deletion at T16. |

Original cold backup: `C:\Users\poorn\OneDrive\...\yottaflexai3\` (untouched, delete only after T14 passes).

**Git:** branch `main`, HEAD `49bcce3`, working tree **clean**.

```
49bcce3 fix(db-init): -ResetRoot grants/restores datadir ACL (LocalSystem-owned) and reports the error log
7d40136 fix(db-init): -ResetRoot automates lost-root recovery; db-health hints at the right next command
4497a6a fix(db-init): support existing root password (-RootPassword + secure prompt); runbook: lost-root recovery
fded5b7 docs: execution status log, AR-1 correction (Node LTS on Windows), preflight hardened
7f98a59 T07: hashed requirements.lock (38 pkgs) + freeze-lock script; verification log complete
```

---

## 2. Task state

| Task | State | Note |
|---|---|---|
| T01 git baseline | ✅ PASS | `c0197f8`, 41 files |
| T02 docs skeleton | ✅ PASS | |
| T03 audit snapshots | ✅ PASS (redacted) | |
| T04 integrity manifest | ✅ PASS | 109 files hashed |
| T05 relocation to `C:\dev` | ✅ PASS | 79/79 identical |
| T06 Python 3.12 + `.venv` | ✅ PASS | 3.12.10 |
| T07 hashed lock | ✅ PASS | 38 packages |
| T08 config hardening | ✅ PASS | `backend/config.py`, no credential default |
| **T09 MySQL service** | ⛔ **BLOCKED** | **root password lost — see §3** |
| T10 verify harness | ✅ PASS | `verify-fast.ps1` green with MySQL stopped |
| T11 tooling + hook | ✅ PASS | |
| T12 docs content | ✅ PASS | |
| T13 launcher | ✅ PASS (static) | |
| T14 cold start | ⏳ PENDING | needs T09 |
| T15 | n/a | |
| T16 delete WSL remnant | ⏳ PENDING | needs T14 + Bro's go |

---

## 3. The blocker, proven

**It is not a connectivity problem.** MySQL 8.0 is running and 3306 is open. Every attempt is rejected
at **authentication**, because the data directory predates this project.

```
Get-Service MySQL*            → MySQL80  Running  Automatic
netstat -ano | :3306          → TCP 0.0.0.0:3306 LISTENING 5772     (service PID 25072, LocalSystem)
Test-NetConnection 127.0.0.1 -Port 3306 → TcpTestSucceeded : True

mysql -u root --skip-password             → ERROR 1045 (28000): Access denied ... (using password: NO)
mysql -u root  (backend\.env password)    → ERROR 1045 (28000): Access denied ... (using password: YES)
.venv\Scripts\python.exe -m backend.check_db
    → (pymysql.err.OperationalError) (1045, "Access denied for user 'root'@'localhost' (using password: YES)")
    → [ERROR] Could not connect to MySQL at localhost:3306. ... User: root          exit=1

Data directory CreationTime → 2024-02-16 22:12:28      (pre-existing install, not ours)
backend\.env               → DB_USER=root             (db-init step 6 would have written yfx_app)
icacls "C:\ProgramData\MySQL\MySQL Server 8.0\Data" → Access is denied   (no leftover ACL grant)
```

**What that means:** the 2024 installation set a root password nobody remembers. `db-init.ps1` offers
only "no password" and "type the password", so it stops before step 4 completes:

```
BLOCKED: could not create the database/app user.
```

Consequently `supplier_schedule_manager` and `yfx_app` **do not exist**, `backend\.env` still points at
`root`, `run.bat` step 9 aborts, and there is **no schema** loaded.

**No dangerous residue:** no temporary `--skip-grant-tables` instance is running, and the datadir ACL is
still closed to the interactive user (`poorn`), so an aborted reset did not leave write access behind.

---

## 4. The single next action (needs an elevated shell)

```powershell
# Right-click PowerShell → Run as administrator
cd C:\dev\yottaflexai3
.\scripts\db-init.ps1 -ResetRoot -NewRootPassword 'PickSomethingStrong!2026'
```

The script then: stops `MySQL80` → grants itself temporary datadir ACL → starts a `--skip-grant-tables`
instance → `FLUSH PRIVILEGES; ALTER USER root` → clean `mysqladmin shutdown` → **revokes the ACL** →
restarts `MySQL80` → creates `supplier_schedule_manager` + `yfx_app` (SELECT/INSERT/UPDATE/DELETE only)
→ writes `DB_USER=yfx_app` + generated password into `backend\.env` → prints grants.

Then prove it:

```powershell
.\scripts\db-health.ps1     # expect RESULT: HEALTHY, version 8.0.x, grants = 4 DML privs
.\scripts\verify-full.ps1   # expect 30/30 green
```

### Do not
- Run `--initialize` against a populated datadir (refuses, or destroys state).
- Rotate root with `-RotateRoot` before `db-health.ps1` passes as `yfx_app`.
- Run any of this without elevation — it will silently fail at the service step.
- Commit `backend\.env` (ignored, and must stay ignored).

### Risks to weigh before running
| Risk | Why it matters |
|---|---|
| Shared, pre-existing instance (2024 datadir) | Other apps on this machine may depend on this MySQL. Resetting root affects them all. `SHOW PROCESSLIST` needs root, so this cannot be checked beforehand. |
| `--skip-grant-tables` window | Any local process can connect unauthenticated for a few seconds. Keep it short; never leave that instance running. |
| Alternative (fresh datadir) | Cleaner, but destroys unknown 2024 data — not recommended blind. |

---

## 5. Known defects — fix after the unblock (Gate 3)

1. `scripts/db-init.ps1:243` prints grants with `--skip-password`; guaranteed `ERROR 1045` once root has
   a password. Should go through `Invoke-RootSql`.
2. `scripts/db-init.ps1:95` assigns to `$args`, shadowing PowerShell's automatic variable. Rename to
   `$initArgs`.
3. `-ResetRoot` never connect-verifies the new password before proceeding to step 4; a silent rotation
   failure surfaces much later as a confusing step-4 abort.
4. `backend\.env` still stores the dead root password in plaintext (untracked, mode-restricted by
   `db-init` step 6 only after a successful run).
5. That same password exists in **git history** at `16ad28e` (docs + scripts), removed from HEAD but not
   from history. Standard hygiene: the value is dead, so rotate-if-reused rather than rewrite history.

Carried into Phase B (unchanged): AUDIT-001 no auth on endpoints, AUDIT-002 anonymous destructive reseed,
AUDIT-004 thresholds not enforced, AUDIT-006 `ScheduleImpact` never recomputed, spec V1/V2/V3.

---

## 6. Pending decisions from Bro

- (a) Approve root-password reset on the shared 2024 MySQL instance (or choose the fresh-datadir route).
- (b) Approve Python 3.12 per-user — **done in T06**, keep recorded.
- (c) Approve `MySQL80` service registration + root rotation — service already registered; rotation still outstanding.
- (d) Approve deleting the WSL remnant after T14 (T16).

Governance note: `implementation_plan.md` still shows `Gate 2 PENDING` while T01–T13 have executed.
That inconsistency is recorded, not resolved — resolve it at the next Gate 2 review rather than editing history.

---

## 7. Canonical references

| What | Where |
|---|---|
| Plan (active context) | `~/ABHI/AbhiMemories/Plans/2026-10-31-yottaflexai3/implementation_plan.md` |
| This diagnosis (full evidence) | `~/ABHI/AbhiMemories/AuditLogs/2026-10-31-bootup-check.md` |
| Setup steps | `docs/01-setup/SETUP-CHECKLIST.md` |
| Start/stop/recover | `docs/01-setup/RUNBOOK.md` → "Lost root password (MySQL 8.0 on Windows)" |
| Evidence | `docs/03-verification/VERIFICATION-LOG.md` → Round 1 |
| Baseline audit | `docs/00-baseline/chandra-audit-2026-10-31.md` |
| Config contract | `docs/02-architecture/ADR-0001-config-and-envs.md` |
