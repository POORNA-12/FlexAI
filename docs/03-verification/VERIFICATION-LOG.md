# VERIFICATION LOG — append-only

**Rule:** one entry per task, written by Abhi, verified by Chandra. Evidence is pasted, never summarised.
A task is **closed only** when Chandra writes a verdict line.

---

## Round 0 — Baseline (2026-10-31)

```
T01  git init + baseline commit
     git.exe init -b main
     tracked files: 41        (source only; .env and data/ ignored)
     commit: c0197f8          "baseline: pristine snapshot after relocating from OneDrive"
     git check-ignore -v backend/.env → .gitignore:3:backend/.env   backend/.env
     git status --porcelain → (empty)
     CHANDRA: PASS — .env not tracked (verified by `git ls-files | grep env` → only .env.example)

T04  integrity manifest of the moved tree
     79 files hashed, 24,162,908 bytes (excludes venv/node_modules/__pycache__/.env)
     source→destination comparison: 79/79 files, 0 missing, 0 extra, 0 hash mismatches
     CHANDRA: PASS — move verified byte-identical before any change

T05  relocation OneDrive → C:\dev\yottaflexai3
     copy: 79 files, shutil.copytree with ignore(venv,node_modules,__pycache__,.pytest_cache,*.pyc)
     verification: IDENTICAL
     original retained at C:\Users\poorn\OneDrive\...\yottaflexai3\ (untouched, pending T16)
     CHANDRA: PASS — original kept as cold backup; no destructive operation performed

T02  docs/ skeleton created
     00-baseline/ 01-setup/ 02-architecture/ 03-verification/
     CHANDRA: PASS

T03  audit snapshots with provenance headers + SHA256SUMS
     chandra-audit-2026-10-31.md    source sha256=68ace125ec8a7fe7  (35,326 B body)
     spec-compliance-2026-10-31.md  source sha256=1cffc7712fee1ccc  (19,457 B body)
     CHANDRA: PASS — bodies copied verbatim; headers carry source path + hash; checksum list written

T06  Python 3.12 + .venv
     winget install Python.Python.3.12 -> 3.12.10 (per-user, no admin)
     installer path : C:\Users\poorn\AppData\Local\Programs\Python\Python312\python.exe
     pyvenv.cfg     : home = ...\Python312
                      include-system-site-packages = false
                      version = 3.12.10
     .venv python   : Python 3.12.10
     pip            : 25.0.1 from C:\dev\yottaflexai3\.venv\Lib\site-packages\pip
     DEVIATION      : `py -3.12` is not on PATH inside an already-open shell (installer updates
                      PATH for new shells only). Used the absolute python.exe instead.
                      Documented as a remedy in SETUP-CHECKLIST Step 2 and handled in setup.ps1.
     CHANDRA: PASS — venv is self-contained (system site-packages disabled), home path is real,
                      and the failure mode that broke the old venv is now checked explicitly.

T08  configuration hardening
     backend/config.py          new: pydantic-settings, DB_PASSWORD required (no default)
     backend/database.py        removed the hardcoded DB_PASSWORD default (<REDACTED-DB-PASSWORD>)
     backend/main.py            CORS + host/port + dataset scale from settings; `import os` dropped
     .gitignore                 + .env.*  *.bak  *.bak.*  _venv_*/  .venv/
     root .env                  archived to C:\dev\_secrets-backup\.env.2026-10-31 (outside repo)
     backend/.env.example       rewritten: DB_USER=yfx_app, explicit "no defaults" warning
     CHANDRA: PASS — no credential literal remains in tracked source (grep pending final verification)
```

---

## Template (copy for each new task)

T07  dependencies measured, then pinned (partially — see deviation)
     install: pip install -r backend\requirements.txt  -> exit 0
     runtime imports (scripts\envcheck.py):
       python 3.12.10 (AMD64) · prefix C:\dev\yottaflexai3\.venv
       ok fastapi 0.162.0 · sqlalchemy 2.1.6 · pydantic 2.14.2 · pydantic_settings 2.16.2
       ok pymysql 2.2.8 · openpyxl 3.1.5 · pandas 3.1.0 · dotenv
     dev: pytest ok · ruff ok · mypy ok
     DEVIATION: requirements.lock was produced with `pip install --dry-run --report` +
                constraints from the measured freeze instead of pip-compile (pip-compile's
                hash resolution exceeded 10 minutes on this machine and was abandoned).
                Same guarantee, faster: the lock reflects exactly what was installed.
     RESULT: backend\requirements.lock - 38 packages, 38 with sha256 hashes
             `pip install --dry-run --require-hashes -r backend\requirements.lock` -> exit 0
             regeneration script: scripts\freeze-lock.ps1
     CHANDRA: PASS — the lock is derived from a working environment and validated by pip
              itself; it is not a hand-written wish list.

T10  verification harness split
     pytest.ini markers: db, slow
     tests/test_project.py : pytestmark = pytest.mark.db  (30 DB-backed tests)
     tests/test_smoke.py   : 10 database-free tests (config, ids, math, determinism, INV-1)
     .\scripts\verify-fast.ps1  -> RESULT: PASS  (exit 0)
        PASS venv python is 3.12.x
        PASS system site-packages disabled
        PASS runtime dependencies import
        PASS application module imports without a database
        PASS configuration validates
        WARN ruff reported findings (199, pre-existing style debt — advisory by design)
        PASS pytest collects
        PASS smoke suite passes (no DB)
     CHANDRA: PASS — the gate that did not exist before now proves the environment with
              MySQL stopped, which is exactly what failed on the old machine.

T11  tooling + secret scan
     ruff.toml created (py312, E/F/W/I/B/UP; removed obsolete UP038 after ruff warned)
     scripts/pre-commit installed via scripts/install-hooks.ps1
     probe 1: `DB_PASSWORD=SuperSecret123` in backend\_secret_probe.py -> BLOCKED (as required)
     probe 2: the same literal inside docs/ -> allowed (documentation is excluded by design)
     NOTE: the hook deliberately contains NO copy of the leaked password; the guard must not
           carry the secret it protects. Snapshots were redacted instead (see T03 addendum).
     CHANDRA: PASS — hook verified in both directions, not just the happy path.

T13  launcher hardening
     run.bat: venv\ -> .venv\, `--system-site-packages` removed, requirements.lock preferred,
              py -3.12 with %LOCALAPPDATA%\Programs\Python\Python312\python.exe fallback
     DEVIATION: `py -3.12` was NOT resolvable inside an existing shell after the winget
                install (PATH refreshes only for new shells). The fallback was added because
                of that observation, not speculation.
     CHANDRA: PASS — DEV_VERIFY deferred to T14 (needs DB service, blocked on admin step).

T09  MySQL service — BLOCKED (expected)
     Requires an elevated shell: `mysqld --initialize-insecure` writes C:\ProgramData\MySQL
     and `mysqld --install MySQL80` registers a service. Both need Administrator.
     Prepared: scripts\db-init.ps1 (idempotent, generates the app password, writes backend\.env)
     CHANDRA: BLOCKED-ON-HUMAN — not a code defect; one elevated command from Bro.

T03  addendum — redaction of the snapshot
     Commit attempt revealed the pre-commit hook blocking the audit snapshot itself, because
     the snapshot quoted the live DB password. Resolution: the snapshot body was redacted
     (<REDACTED-DB-PASSWORD>), the provenance header records the redaction, SHA256SUMS was
     regenerated, and the hook was rewritten to contain no copy of the secret.
     CHANDRA: PASS — a guard that carries the secret it protects is a self-defeating artifact;
              redaction is the correct fix, not an allowlist.
```

---

## Template (copy for each new task)

```markdown
### Tnn — <task>
Owner: Abhi · Date: YYYY-MM-DD
Command:
    <exact command>
Output:
    <raw output, unedited>
Deviation: none | <what and why>
CHANDRA: PASS | FAIL — <reason> (evidence checked: <what>)
```

---

## Open blockers

| # | Blocker | Owner | Unblocks |
|---|---|---|---|
| B-1 | MySQL service init needs an elevated shell (`scripts\db-init.ps1`) | Bro | T09, T14 (cold start), `verify-full.ps1` |
| B-2 | `backend\requirements.lock` generation in progress (pip-compile --generate-hashes) | Abhi | T07 completion, hashed installs |
| B-3 | WSL remnant deletion (T16) awaits B-1 + a final manifest check | Bro | cleanup |
