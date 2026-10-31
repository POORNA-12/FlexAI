# HANDOFF — yottaflexai3 (FlexAI) · 2026-10-31

**Reader:** Any engineer, collaborator, or friend setting up or resuming this project on their machine.  
**Writer:** Abhi (Execution Authority & Strategic Assistant)  
**Status:** ✅ **T09 UNBLOCKED & PASSED** — MySQL 8.0 recovered, 14 InnoDB tables created, 10,000 POs seeded, verify-full 39/39 PASS.  
**Remote Repository:** `https://github.com/POORNA-12/FlexAI`

---

## 1. Quick Start: How to Set Up This Project on a New Machine

Follow these exact steps to get the entire stack (FastAPI + Vite React + MySQL 8.0) up and running from scratch.

### Prerequisites
* **OS:** Windows 10 / 11 (PowerShell 5.1+ or PowerShell 7+)
* **Python:** 3.12.x (installed and available in PATH)
* **Node.js:** LTS v20+ / npm v10+
* **MySQL:** MySQL Server 8.0 installed as Windows service `MySQL80` (default port 3306)

---

### Step-by-Step Setup Runbook

#### 1. Clone the repository
```powershell
git clone https://github.com/POORNA-12/FlexAI C:\dev\yottaflexai3
cd C:\dev\yottaflexai3
```

#### 2. Bootstrap Python virtual environment & tooling
In a regular PowerShell terminal:
```powershell
.\scripts\setup.ps1
```
This creates `.venv` (Python 3.12), installs all pinned dependencies from `requirements.lock`, and installs frontend npm packages.

#### 3. Initialize MySQL Database & Users (Run as Administrator)
Open **PowerShell as Administrator** (Right-click PowerShell → Run as Administrator):
```powershell
cd C:\dev\yottaflexai3

# Scenario A: If you already know your MySQL root password:
.\scripts\db-init.ps1 -RootPassword 'YourRootPassword'

# Scenario B: If root password is forgotten/unknown:
.\scripts\db-init.ps1 -ResetRoot -NewRootPassword 'ChooseAStrongPassword!2026'
```

**What `db-init.ps1` automatically does:**
1. Connects to MySQL 8.0 with administrative privileges.
2. Creates the target database: `supplier_schedule_manager`.
3. Creates a dedicated, least-privilege application user: `yfx_app` (with randomized secure password).
4. Grants only required DML permissions (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) on `supplier_schedule_manager.*`.
5. Executes `database/schema.sql` as root to provision all 14 InnoDB tables with proper keys and constraints.
6. Writes `DB_USER=yfx_app` and `DB_PASSWORD` into `backend/.env` with strict file ACLs.

#### 4. Verify Database & Run Test Suite (Normal Terminal)
Close the Administrator PowerShell window. In your **regular user terminal**:
```powershell
cd C:\dev\yottaflexai3

# Check database connectivity, tables, and permissions:
.\scripts\db-health.ps1
# Expect: RESULT: HEALTHY (14 tables, yfx_app connected)

# Run full verification (seeds dataset & runs test suite):
.\scripts\verify-full.ps1
# Expect: 39/39 tests PASS
```

#### 5. Launch the Application
```cmd
.\run.bat
```
* **Backend API:** `http://127.0.0.1:8000` (Docs at `/docs`)
* **Frontend UI:** `http://127.0.0.1:5173`

---

## 2. Issues Encountered & How They Were Resolved

During setup on the initial reference workstation, Task T09 encountered a blocking issue with an existing MySQL 8.0 install. Here is how each failure point was diagnosed and permanently resolved:

### 1. Pre-existing MySQL Root Password Lockout
* **Problem:** Machine had a pre-existing MySQL 8.0 datadir from 2024 with an unknown root password, blocking creation of `supplier_schedule_manager` and `yfx_app`.
* **Fix:** Upgraded `scripts/db-init.ps1` to support automated root recovery using Oracle’s official standard: `--init-file`. This bypasses authentication safely during server startup, changes the password to the requested value, and cleanly restarts the normal service.

### 2. PowerShell Argument Quoting & Path Spaces
* **Problem:** MySQL was installed in `C:\Program Files\MySQL\MySQL Server 8.0` and config in `C:\ProgramData\MySQL\MySQL Server 8.0`. PowerShell 5.1 stripped quotes when passing arguments to `Start-Process`, causing `mysqld.exe` to crash on startup trying to open `C:\ProgramData\MySQL\MySQL`.
* **Fix:** Explicitly escaped parameter strings (`"--defaults-file=..."`, `"--init-file=..."`, `"--log-error=..."`) passed to `Start-Process`.

### 3. MySQL 8.0 TCP Networking Disabling
* **Problem:** Using `--skip-grant-tables` in MySQL 8.0 automatically enables `--skip-networking`, preventing TCP/IP connections on port 3306.
* **Fix:** Replaced `--skip-grant-tables` entirely with `--init-file`, which retains normal TCP networking.

### 4. Brittle Port Checking (CIM/WMI Exceptions)
* **Problem:** `Get-NetTCPConnection` in PowerShell 5.1 threw CIM security exceptions on restricted host policies, causing the readiness loop to bail early.
* **Fix:** Replaced CIM calls with `Test-PortOpen` helper using direct `.NET` socket probes (`System.Net.Sockets.TcpClient`).

### 5. Least-Privilege User DDL Denial
* **Problem:** `yfx_app` is intentionally restricted to DML (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) with no `CREATE TABLE` permissions. Because the database was initialized without applying the schema first, runtime `init_db()` failed with `CREATE command denied`.
* **Fix:** `scripts/db-init.ps1` now automatically applies `database/schema.sql` using root credentials during step 4 before handing over connection credentials to `yfx_app`.

### 6. Stale `DATABASE_URL` in `backend/.env`
* **Problem:** `backend/.env` contained a stale uncommented `DATABASE_URL=mysql+pymysql://root:...` line which took precedence over `DB_USER=yfx_app`.
* **Fix:** Commented out `DATABASE_URL` and updated `scripts/db-init.ps1` to ensure `DATABASE_URL` is commented out when generating `.env`.

---

## 3. Verified System & Task State

| Task | State | Details |
|---|---|---|
| **T01** git baseline | ✅ PASS | Baseline commit recorded |
| **T02** docs skeleton | ✅ PASS | Structure initialized |
| **T03** audit snapshots | ✅ PASS | Baseline audit reports preserved |
| **T04** integrity manifest | ✅ PASS | File manifest hashed |
| **T05** relocation to `C:\dev` | ✅ PASS | Clean Windows file tree |
| **T06** Python 3.12 + `.venv` | ✅ PASS | Python 3.12.10 virtualenv configured |
| **T07** hashed lock | ✅ PASS | 38 packages pinned in `requirements.lock` |
| **T08** config hardening | ✅ PASS | `backend/config.py` validated |
| **T09** MySQL service | ✅ PASS | MySQL 8.0 recovered, 14 InnoDB tables created |
| **T10** verify harness | ✅ PASS | `verify-fast.ps1` and `verify-full.ps1` (39/39 tests) green |
| **T11** tooling + hook | ✅ PASS | Ruff linter & test harness active |
| **T12** docs content | ✅ PASS | Architecture & handoff documented |
| **T13** launcher | ✅ PASS | `run.bat` static check passed |
| **T14** cold start | ⏳ READY | Ready for end-to-end UI launch |

---

## 4. Transaction Integrity Verification

MySQL transactions and constraints were rigorously tested on the active database:
* **Storage Engine:** `InnoDB` across all 14 tables.
* **Isolation Level:** `REPEATABLE-READ` with manual transaction scoping (`autocommit=0`).
* **ACID Commit:** Verified persistent across independent sessions.
* **ACID Rollback:** Verified zero state leakage when rolling back uncommitted inserts.
* **Foreign Keys:** Enforced with active cascade rules across PO lines, supplier items, and schedule impacts.
