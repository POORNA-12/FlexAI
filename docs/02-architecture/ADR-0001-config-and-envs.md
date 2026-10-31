# ADR-0001 — Environment, configuration and dependency policy

- **Status:** Accepted
- **Date:** 2026-10-31
- **Deciders:** Bro (owner), Ajay (architecture), Chandra (assurance), Abhi (execution)
- **Context:** the project was relocated from WSL to Windows. The only venv belonged to another user (`C:\Users\kowshik`, Python 3.14.6, `--system-site-packages`), the host has only a Microsoft Store Python alias, MySQL is installed but has no service, and dependencies were unpinned. Setup was therefore neither reproducible nor executable.

## Decisions

### D0 — Windows is the only run/build target
WSL is review-only. Rationale: the working toolchain (Node, Git, MySQL binaries, Workbench) is on Windows; a Windows venv cannot run under Linux.
**Consequence:** every instruction, script and verification command is PowerShell/`cmd`, not bash.

### D1 — Project lives outside OneDrive (`C:\dev\yottaflexai3`)
Installs write tens of thousands of files; OneDrive locks them mid-write, which corrupts packages and `.git`.
**Fallback:** stay in OneDrive and exclude `.venv`, `node_modules`, `.git`, `__pycache__` from sync, pausing sync during setup (accepted risk AR-2).
**Reversible:** move back.

### D2 — Python 3.12 from python.org, `.venv` created by `py -3.12 -m venv .venv`
The Store alias is a 2-byte stub that auto-updates; the previous venv's `home` pointed at a non-existent profile. `include-system-site-packages=false` so the environment is closed.
**Rejected:** repairing the existing venv (its base interpreter path does not exist); `--system-site-packages` (leaks an unknown third-party surface).

### D3 — MySQL 8.0 owns 3306, registered as the `MySQL80` service
Schema is MySQL 8.0 DDL. 8.4 is installed but must not be serviced on 3306.
**Rejected:** Docker on Windows (no daemon configured on the host; adds a dependency), MySQL 8.4 (unverified against the DDL).

### D4 — One authoritative config file: `backend\.env`
`config.py` (pydantic-settings) validates required keys and **fails fast**; no credential default exists in source. The root `.env` is archived outside the repo.
**Rejected:** `os.getenv` scattered with implicit defaults (the current behaviour that hid a hardcoded password).

### D5 — Pin by measurement
Install → import smoke → `pip freeze` → `requirements.lock` with hashes; `requirements-dev.txt` for ruff/mypy/pytest.
**Rejected:** pinning from memory or from a container that never ran the code (fabricated reproducibility).

### D6 — PowerShell verification scripts, two tiers
`verify-fast.ps1` (no DB) and `verify-full.ps1` (DB). `make` is not available on Windows.
**Why two tiers:** proves the environment without MySQL, which is exactly what could not be proven before.

### D7 — `docs/` holds immutable snapshots, not originals
Gate 1/5 reports live in `~/ABHI/AbhiMemories/`; copies carry a provenance header and `SHA256SUMS`.

## Consequences

- Positive: one-command provision, a provable "setup complete", secrets out of source, rollback via git.
- Negative: an extra interpreter install; MySQL service registration needs one elevated shell.
- Neutral: `DB_PORT` becomes explicit (3306); the app now refuses to start with a missing password instead of silently defaulting.

## Compliance

Consistent with the problem statement's Step 9 ("README, schema/data dictionary, generator command, fixed seed, source manifest and validation summary") — this ADR adds the *environment* half of that contract.
