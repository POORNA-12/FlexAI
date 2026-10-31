# PREREQUISITES — what must exist before setup

**Platform:** Windows 10/11 (x64). WSL is review-only and cannot run this project.
**Measured on:** `poorn` machine, 2026-10-31.

## 1. Hard requirements

| # | Component | Required | Why | Check command | Expected |
|---|---|---|---|---|---|
| P1 | Windows | 10 19045+ / 11 | `run.bat` uses `netstat`/`taskkill`; PowerShell scripts used for verification | `[System.Environment]::OSVersion.Version` | 10.0.19045 or higher |
| P2 | Python | **3.12.x** (3.11.9 works but is unpinned; 3.13/3.14 unverified) | `.python-version` = 3.12; wheels for pandas/numpy/cryptography are stable here | `py -3.12 --version` | `Python 3.12.x` |
| P3 | `py` launcher | present | selects 3.12 deterministically instead of PATH order | `py -0p` | lists 3.12 with a path |
| P4 | Node.js | **≥ 18** (host has 25.8.2, non-LTS — accepted risk AR-1) | Vite 6 / React 19 toolchain | `node -v` | `v18+` |
| P5 | npm | ≥ 9 | `npm ci` from `package-lock.json` | `npm -v` | `9+` |
| P6 | Git | ≥ 2.40 | baseline commit as the rollback anchor | `git --version` | `2.4x+` |
| P7 | MySQL Server | **8.0.x**, service `MySQL80`, port 3306 | schema is MySQL 8.0 DDL; app is MySQL-only (PyMySQL) | `Get-Service MySQL80` | `Running` |
| P8 | `mysql` client | 8.0 `bin` on disk | service init + grant verification | `& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" --version` | `Ver 8.0.x` |
| P9 | Disk | ≥ 1 GB free on `C:` | venv ~120 MB, node_modules ~64 MB, DB ~200 MB | `Get-PSDrive C` | Free > 1 GB |
| P10 | Ports | 8000, 5173, 3306 free | backend, vite, MySQL | `Get-NetTCPConnection -LocalPort 8000,5173,3306 -ErrorAction SilentlyContinue` | no output (or only MySQL) |

## 2. Installed-on-this-machine state (2026-10-31, measured)

| Item | Status |
|---|---|
| Python | **Store alias only** (`…\WindowsApps\python.exe`, 2-byte stub → 3.11.9); no `py` launcher, no python.org install |
| MySQL binaries | ✅ `C:\Program Files\MySQL\MySQL Server 8.0` **and** `8.4`, plus Shell 8.4 + Workbench 8.0 |
| MySQL service | ❌ **does not exist** (`sc query MySQL80` → FAILED 1060) |
| MySQL data dir | ⚠️ `C:\ProgramData\MySQL\MySQL Server 8.0\Data` exists but is **empty** → never initialized |
| MySQL port | ❌ 3306 refused (`ERROR 2003 (10061)`) |
| Node.js / npm | ✅ v25.8.2 / 11.11.1 |
| Git | ✅ 2.55.0.windows.3 (`user.name = Purna-Ajay`) |
| Docker | installed in WSL only — **not** a Windows prerequisite |
| Project location | ✅ `C:\dev\yottaflexai3` (relocated out of OneDrive) |

## 3. Accounts & privileges

| Need | Scope | Who provides |
|---|---|---|
| Python 3.12 per-user install | no admin | winget / python.org installer |
| `pip install` into `.venv` | no admin | user |
| `mysqld --initialize-insecure` + `mysqld --install` | **Administrator** (writes `C:\ProgramData\MySQL`) | Bro — one elevated PowerShell |
| `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` | current user | user |
| MySQL root password | known (see `backend/.env`, rotate per RUNBOOK) | Bro |

## 4. Explicit non-prerequisites

- No Docker required on Windows (fallback only).
- No WSL required to run.
- No cloud account, no external dataset, no network at runtime (only at install time for pip/npm/winget).
- No admin rights for anything except the MySQL service step.
