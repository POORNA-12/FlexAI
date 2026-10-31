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
     backend/database.py        removed `os.getenv("DB_PASSWORD", "Aqswdefr@123")`
     backend/main.py            CORS + host/port + dataset scale from settings; `import os` dropped
     .gitignore                 + .env.*  *.bak  *.bak.*  _venv_*/  .venv/
     root .env                  archived to C:\dev\_secrets-backup\.env.2026-10-31 (outside repo)
     backend/.env.example       rewritten: DB_USER=yfx_app, explicit "no defaults" warning
     CHANDRA: PASS — no credential literal remains in tracked source (grep pending final verification)
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
