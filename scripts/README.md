# scripts/ — operational tooling

All scripts are **Windows PowerShell** (ADR-0001 D0/D6). None of them change application logic.

| Script | Needs admin? | Changes state? | Purpose |
|---|---|---|---|
| `preflight.ps1` | no | **no** | report every dependency (python, node, git, MySQL service, data dir, ports, secrets) |
| `setup.ps1` | no | yes | idempotent provisioner: `.venv`, deps, `backend\.env`, frontend `node_modules` |
| `verify-fast.ps1` | no | no | environment gate that **passes with MySQL stopped** |
| `verify-full.ps1` | no | yes (seeds if empty) | DB health → seed → full pytest suite |
| `db-init.ps1` | **yes** | yes | initialise MySQL 8.0, register `MySQL80`, create DB + least-privilege `yfx_app`, write `backend\.env` |
| `db-health.ps1` | no | no | service, version, connectivity, schema, row counts, grants |
| `freeze-lock.ps1` | no | yes | regenerate `backend\requirements.lock` from the measured environment (ADR-0001 D5) |
| `install-hooks.ps1` | no | yes | install the versioned pre-commit secret scan |
| `pre-commit` | no | no | the hook itself: blocks hardcoded credentials, private keys, tracked `.env` |
| `envcheck.py` | no | no | interpreter + import report (used when shell quoting makes `-c` awkward) |

## Typical sequence

```powershell
.\scripts\preflight.ps1          # see what is missing
.\scripts\setup.ps1              # create .venv, install deps, seed .env
.\scripts\verify-fast.ps1        # must pass with no database
# PowerShell as Administrator:
.\scripts\db-init.ps1            # MySQL service + database + app user
.\scripts\verify-full.ps1        # seed + 30 tests
.\run.bat                        # start the app
```

## Conventions

- Exit code `0` = success, `1` = blocked. Blocking errors print `BLOCKED:` and what to do.
- Secrets are **never** echoed; `db-init.ps1` generates the app password and writes it straight into `backend\.env`.
- Scripts read configuration only from `backend\.env` (via `backend/config.py` for Python, direct parsing for PowerShell).
