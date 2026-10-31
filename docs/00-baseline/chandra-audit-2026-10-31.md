<!-- SNAPSHOT — DO NOT EDIT IN PLACE.
     source      : /home/poorna/ABHI/AbhiMemories/AuditLogs/2026-10-31-yottaflexai3-chandra-audit.md
     snapshot    : 2026-10-31
     sha256      : 68ace125ec8a7fe79c0b5c51eb7e4db8493ecdd3e71e7f402048d27a7b23176c
     authority   : Chandra (Assurance Authority) — Gate 5
     redaction   : live DB password literal replaced with <REDACTED-DB-PASSWORD>
     rule        : the original is the source of truth; this file is an immutable copy.
-->

# Gate 5 — Chandra Repository Audit

**Project:** `yottaflexai3` — Supplier Acknowledgement and Schedule Impact Manager
**Path:** `/home/poorna/Kowshik/yottaflexai3/yottaflexai3` (107 MB, incl. Windows `venv/`)
**Auditor:** Chandra (Assurance Authority)
**Date:** 2026-10-31
**Scope:** Repository-wide security + architectural audit (`chandra-repository-audit`), 13 phases
**Mode:** Read-only inspection. No files in the project were modified.

---

## 0. VERDICT

```text
Status: REJECTED
Gate: Gate 5 (Defensive Review) — FAILED
Return to: Gate 3 (implementation defects) + Gate 2 (missing auth/trust-boundary design)
Blocking findings: 3 Critical, 6 High
```

The application is a competent functional prototype (10 ORM entities, 13 tables, ~70k deterministic rows, 30 tests declared) but it is **not a secure or auditable system**. Three properties the README explicitly sells — *"auditable platform"*, *"enforce strict approval thresholds"*, and *"100% precision/recall anomaly detection"* — are **contradicted by the code**.

---

## 1. FINDINGS SUMMARY

| ID | Title | Severity | Status |
|---|---|---|---|
| AUDIT-001 | Zero authentication/authorization on every endpoint; reviewer identity is client-supplied | **Critical** | OPEN |
| AUDIT-002 | Unauthenticated destructive reseed endpoint (wipes 69,844 rows), reachable by drive-by CSRF | **Critical** | OPEN |
| AUDIT-003 | MySQL root credential hardcoded in source + real `.env` shipped in the project folder | **Critical** | OPEN |
| AUDIT-004 | Approval thresholds never enforced at decision time | **High** | OPEN |
| AUDIT-005 | Only `QUANTITY` changes are applied; `PRICE`/`DELIVERY_DATE`/`COMBINED` are marked `APPLIED` with no effect | **High** | OPEN |
| AUDIT-006 | `ScheduleImpact` is never recalculated on approval (imported, never called) | **High** | OPEN |
| AUDIT-007 | Approval concurrency: no row lock, no idempotency key, timestamp-based notification PK | **High** | OPEN |
| AUDIT-008 | Validation engine: 6 of 15 "rules" can never fail; Scenario-4 detection is a sentinel check | **High** | OPEN |
| AUDIT-009 | Internal exception text returned to clients (`detail=str(exc)`) | **High** | OPEN |
| AUDIT-010 | Unbounded export + N+1 queries + CPU-heavy endpoint, no limits | Medium | OPEN |
| AUDIT-011 | Backend dependencies unpinned (`>=` only), no lockfile or hashes | Medium | OPEN |
| AUDIT-012 | `passed_validation_checks` reports 35 for 15 rules; tests assert `>= 15` | Medium | OPEN |
| AUDIT-013 | Dual schema truth (`schema.sql` vs ORM `create_all`) with drift | Medium | OPEN |
| AUDIT-014 | No rate limiting / payload caps; `/docs` + `/health` exposed | Medium | OPEN |
| AUDIT-015 | Deprecated naive `utcnow()` + `datetime.now()` in seed path breaks row-level determinism | Medium | OPEN |
| AUDIT-016 | `SET FOREIGN_KEY_CHECKS=0` on a pooled connection during reseed | Medium | OPEN |
| AUDIT-017 | `PaginatedResponse.items: List[Any]` disables response validation | Low | OPEN |
| AUDIT-018 | CORS `allow_credentials=True` with wildcard methods/headers | Low | OPEN |
| AUDIT-019 | Documentation/count inconsistencies (20 vs 30 tests, 15 vs 35 checks) | Low | OPEN |
| AUDIT-020 | Test suite depends on a live 10k-row MySQL; `test_11` passes vacuously | Low | OPEN |
| AUDIT-021 | Zero knowledge artifacts (ADR / lessons / patterns) — INV-007 | Low | OPEN |

---

## 2. CRITICAL FINDINGS

### AUDIT-001 — No authentication or authorization anywhere

```text
ID: AUDIT-001
Title: Complete absence of authentication, authorization and actor identity
Severity: Critical
Component: FastAPI backend (all routes) + React client
Affected Files: backend/main.py:46-78, backend/routes.py:19-537, backend/schemas.py:107-109,
                frontend/src/pages/Approvals.jsx:60-72
```

**Evidence**
- `backend/routes.py:19` — `router = APIRouter(prefix="/api")`, then every handler depends only on `get_db` (`Depends(get_db)` at lines 24, 36, 76, 109, 129, 172, 214, 232, 252 …). No `Depends(security)` exists.
- Grep for `authorization|bearer|jwt|oauth|api[_-]?key|token|session|cookie|rate.?limit|login` over `backend/*.py` and `frontend/src` returns **zero** auth hits (only SQLAlchemy `sessionmaker` and the DB password string).
- `backend/schemas.py:107-109` — `ApprovalActionRequest` carries `reviewer_id: str = "PLN-001"` **from the request body**.
- `frontend/src/pages/Approvals.jsx:63,69` — the client hardcodes `reviewer_id: 'PLN-001'`; nobody authenticates as that planner.
- `backend/main.py:46-53` — the app is created with no auth middleware, no dependency overrides; `/docs`, `/redoc` open.

**Impact**
Every business action is anonymous: approve a supplier price/quantity change, reject it, resolve an exception, export the full dataset, or replace the database. The `approvals.reviewer_id` column — the audit trail the product exists to provide — is an attacker-controlled string. Any value can be written (e.g. `reviewer_id: "CFO-001"`), and the `APR-…` record will look legitimate. This is a complete authorization bypass, not a misconfiguration.

**Attack Scenario**
1. Attacker (any process/user on the machine, any site in the developer's browser, or *anyone at all* once the README's §17 custom-domain deployment happens) issues `POST /api/change-requests/CHG-PO-2026-000123-01/approve` with body `{"reviewer_id":"OPS-MGR-01","comments":"approved"}`.
2. `services.approve_change_request` writes an `APPROVED` approval row and mutates `inventory_plans.projected_supply` (services.py:189-226).
3. The dashboard, exports, and "audit" trail all show a legitimate operations-manager approval. No user, no password, no role check occurred.

**Recommendation**
Introduce an identity layer before any further feature work: an auth dependency (`Depends(require_user)` / `require_role("PLANNER","OPERATIONS_MANAGER")`), server-side derivation of `reviewer_id` from the authenticated principal (never from the body), role enforcement on approve/reject/resolve/seed, and an `audit_log` table recording actor, action, entity, before/after values, and source IP. Until then, treat the deployment as non-production.

**Verification**
`grep -rn "Depends(security\|require_role\|require_user\|Authorization" backend/` must return non-empty; approve/reject must return 401 without credentials and 403 for a role below the required tier; an approval row's `reviewer_id` must match the authenticated principal, not the request body.

---

### AUDIT-002 — Unauthenticated destructive reseed endpoint

```text
ID: AUDIT-002
Title: Destructive full-database reseed is an anonymous, CSRF-triggerable POST
Severity: Critical
Component: Data generation endpoint + seed service
Affected Files: backend/routes.py:350-369, backend/services.py:375-453,
                frontend/src/api.js:148-150
```

**Evidence**
- `routes.py:350-369` — `POST /api/data-generator/seed` needs only `scale` and `confirm=true`. There is no auth dependency, no ownership check, no dry-run.
- `services.py:416-425` — the seed path executes `SET FOREIGN_KEY_CHECKS = 0;` and deletes **all** rows from 14 tables before reinserting.
- The endpoint takes **no request body and only query parameters**, so it is a CORS *simple request*: a malicious page can fire it cross-origin without a preflight, and does not need to read the response.

**Impact**
One anonymous request destroys/corrupts the operational dataset (69,844 rows). Approval decisions, resolution history, and notifications are unrecoverable — there is no backup, no soft delete, no snapshot. A single malicious web page visited by the developer can trigger it against `127.0.0.1:8000`.

**Attack Scenario**
1. Developer browses any site containing `<form action="http://127.0.0.1:8000/api/data-generator/seed?scale=full&confirm=true" method="POST">` + auto-submit JS (no preflight: no custom headers, no JSON content type).
2. The browser sends the POST; the API answers 200 after wiping and regenerating data.
3. All planner decisions made that day are gone. The attacker may also repeatedly trigger it for resource exhaustion (each call regenerates ~70k rows).

**Recommendation**
Remove the endpoint from the runtime API or gate it behind an admin role + an out-of-band confirmation token; make reseeding an explicit CLI operation (`scripts/reseed.py`) intended for non-production. Add `X-Requested-With`/CSRF tokens and a `SameSite` policy so localhost APIs are not drive-by reachable. Require a typed confirmation phrase, not `confirm=true`.

**Verification**
`POST /api/data-generator/seed?scale=full&confirm=true` without auth returns 401/403; a cross-site form POST cannot change row counts; reseed only runs from an explicit admin action with an audit record.

---

### AUDIT-003 — Database superuser credential in source and in the shipped folder

```text
ID: AUDIT-003
Title: MySQL root password hardcoded as a code default and present in .env
Severity: Critical
Component: Database configuration
Affected Files: backend/database.py:18-29, .env:1-6, backend/.env
```

**Evidence**
- `backend/database.py:21` — `DB_PASSWORD = os.getenv("DB_PASSWORD", "<REDACTED-DB-PASSWORD>")`. The real password is the **fallback in a tracked source file**, so it survives deletion of `.env`.
- `.env:4` and `backend/.env:4` contain `DB_PASSWORD=<REDACTED-DB-PASSWORD>` with `DB_USER=root` (`.env:3`), i.e. full-privilege MySQL credentials.
- `.gitignore:2-3` correctly excludes `.env`, but the folder is distributed as a zip (no `.git` present), so the secret travels with it. `route`/`schema` scripts also embed the DB name from env.

**Impact**
Anyone holding a copy of this folder owns the local MySQL instance: read/modify every database on the server (`root`), or reuse the same password on the developer's other services if reused. If this password is reused anywhere else (very common for local dev), it is a credential-reuse breach.

**Attack Scenario**
1. Attacker obtains the folder (zip, USB, chat, repo history).
2. `mysql -h <host> -u root -p<REDACTED-DB-PASSWORD>` — full server access; drop any schema, read any table.

**Recommendation**
Rotate the password now. Delete the literal default (`DB_PASSWORD = os.getenv("DB_PASSWORD")` + fail fast if unset), create a least-privilege app user (`GRANT SELECT,INSERT,UPDATE,DELETE ON supplier_schedule_manager.*`), and add a secret-scanning pre-commit hook. Treat `.env` as compromised material and purge it from any shared archive.

**Verification**
`grep -rn "<REDACTED-DB-PASSWORD>" .` returns nothing; unset `DB_PASSWORD` must abort startup with a clear error; the app user must not have `GRANT`/`DROP` privileges.

---

## 3. HIGH FINDINGS

### AUDIT-004 — Approval thresholds are never enforced

```text
ID: AUDIT-004
Title: Business-rule threshold engine is used only during data generation, never at decision time
Severity: High
Component: Approval workflow
Affected Files: backend/services.py:163-236, backend/business_rules.py:42-94, backend/generator.py:431
```

**Evidence**
- `business_rules.evaluate_approval_requirement` (threshold tiers AUTO / PLANNER / OPERATIONS_MANAGER) is called **exactly once**, at `generator.py:431`, i.e. when fabricating synthetic data.
- `services.approve_change_request` (services.py:163-236) contains no call to it and no threshold comparison. The only precondition is `chg.status == "PENDING_APPROVAL"` (line 181).
- `README.md:14` claims: *"Enforce strict approval thresholds before unapproved supplier changes affect inventory supply plans."*

**Impact**
A +400% price increase or a −90% quantity reduction is approved with the same code path as a 0-unit change. `PLANNER_APPROVE_*` / `AUTO_APPROVE_*` env thresholds are decorative at runtime. The product's stated control objective is unmet.

**Attack Scenario**
Planner (or anonymous caller, see AUDIT-001) approves a 90% quantity cut; no tier check rejects it, no manager sign-off is required, and `projected_supply` drops immediately.

**Recommendation**
At decision time, load the referenced line/ack, compute variances with `business_rules`, evaluate the required tier, and compare against the *authenticated* role. Persist `required_tier`, `computed_variance`, and `policy_version` on the approval row. Auto-approve only when tier == `AUTO`.

**Verification**
Unit tests: change with +12% price → 409/403 for a planner, 200 for operations manager; change within AUTO band → applied without a reviewer.

---

### AUDIT-005 — Non-quantity change types are "applied" without being applied

```text
ID: AUDIT-005
Title: Only QUANTITY changes mutate state; PRICE/DELIVERY_DATE/COMBINED are silently no-ops
Severity: High
Component: Approval service
Affected Files: backend/services.py:200-213, backend/models.py:139-151
```

**Evidence**
- services.py:204 — `if plan and chg.change_type == "QUANTITY":` — the block that updates `projected_supply`, `status`, `effective_at` is skipped for every other type.
- services.py:200 — `chg.status = "APPLIED"` is set unconditionally, then committed (line 226).
- `PurchaseOrder.status` is never advanced (`CHANGE_PENDING` → `APPROVED`) and `po_lines.status` is never updated.

**Impact**
The audit trail asserts "applied" for changes that changed nothing. Price changes never reach `po_lines.unit_price`/`purchase_orders.total_amount`; delivery-date changes never reach `promise_dates`; `COMBINED` applies no component. Downstream MRP reads stale values while the UI reports success.

**Attack Scenario**
A supplier price increase is approved → `approvals.decision = APPROVED`, `change_requests.status = APPLIED`, unit price unchanged. Month-end reconciliation shows approved-but-unapplied changes; there is no way to distinguish them from applied ones.

**Recommendation**
Implement per-type application (price → line price + PO total recompute; date → new promise revision; combined → all applicable), commit all effects in the same transaction as the approval row, and reject at the service boundary any type without an implemented applier.

**Verification**
Integration test per change type asserting the target column changed and the approval row exists; `SELECT` after approval must show the new price/date.

---

### AUDIT-006 — Schedule impact is never recomputed on approval

```text
ID: AUDIT-006
Title: Docstring promises ScheduleImpact recalculation; code never calls it
Severity: High
Component: Downstream impact engine
Affected Files: backend/services.py:18, 176, 522; docstring services.py:174
```

**Evidence**
- services.py:174 states step *"5. Recalculates ScheduleImpact."*
- services.py:18 imports `calculate_schedule_impact`; a grep shows **no call site** in `services.py` (only `generator.py:522` uses it).
- services.py:163-236 contains no write to `models.ScheduleImpact`.

**Impact**
After an approval mutates `projected_supply`, `schedule_impacts.shortage_qty` / `impact_status` remain the generator's values. The "Downstream Schedule Impact" page and its shortage counts are frozen in time — the core value proposition ("evaluate supplier promises against manufacturing need dates") is not wired to the workflow.

**Attack Scenario**
Approve a quantity reduction that creates a real shortage; `/api/schedule-impacts` still reports `ON_TIME`; production plans on phantom supply.

**Recommendation**
In the approval transaction, recompute every affected `ScheduleImpact` row (join line → production orders), persist `delay_days`, `shortage_qty`, `impact_status`, `updated_at`, and emit a notification when status transitions to `CONFIRMED_SHORTAGE`.

**Verification**
Approving a shortage-inducing change must change `schedule_impacts.impact_status` for the affected PO lines within the same transaction.

---

### AUDIT-007 — Approval concurrency, idempotency and PK collisions

```text
ID: AUDIT-007
Title: Check-then-act approval without row lock; notification IDs collide by second
Severity: High
Component: Approval service
Affected Files: backend/services.py:163-236 (esp. 181, 185-197, 217)
```

**Evidence**
- services.py:177-182 — reads status, then acts; the query has no `with_for_update()`, so two concurrent requests both observe `PENDING_APPROVAL`. Sync handlers run in FastAPI's threadpool, so this is genuinely concurrent.
- services.py:186 — `appr_id = f"APR-{change_id}-REV{revision_no:02d}"` — the second concurrent approval hits a duplicate PK, raising `IntegrityError`, which the generic `except` (line 234) converts to `RuntimeError` → HTTP 500. Correct outcome, wrong contract (should be 409 already-decided).
- services.py:217 — `notification_id = f"NOT-{int(datetime.utcnow().timestamp())}"` — two approvals in the same second generate the **same** notification PK → the second approval fails with 500 even when the change is legitimate. This is a functional bug reachable from normal use (bulk approvals).
- services.py:203-204 — if the inventory plan is missing, the approval still commits as `APPLIED` with no supply update (silent invariant hole).

**Impact**
Non-deterministic 500s under concurrency and under bulk use; audit rows can be lost to rollback; "applied but not applied" states accumulate. No idempotency key means a client retry after a network timeout produces a 500 instead of a stable result.

**Attack Scenario**
Two planners approve different changes within the same second → second request returns 500, its approval is rolled back, notification lost; the UI shows a failure for a valid operation. Repeated → planner loses trust and retries, compounding.

**Recommendation**
`SELECT … FOR UPDATE` (or optimistic `WHERE status='PENDING_APPROVAL'` update) before applying; derive notification IDs from a UUID/ULID or a sequence; return 409 for already-decided changes; require a client idempotency key; make "plan missing" a hard error.

**Verification**
Two parallel approvals of the same change → exactly one 200 and one 409, one approval row. Two approvals in the same second → both succeed. Approve with a deleted plan → 409/422, no `APPLIED` status.

---

### AUDIT-008 — The validation engine does not validate (6 no-ops + rigged detection)

```text
ID: AUDIT-008
Title: Validation "15 rules" include always-passing stubs and a sentinel that only detects revision 0
Severity: High
Component: Validation engine + anomaly metrics
Affected Files: backend/validation.py:143-180, 218-247, 249-274, 331-337,
                backend/generator.py:655-674, data/validation_summary.json
```

**Evidence**
1. **Always-pass stubs** — bodies contain only `self.summary["passed_checks"] += 1`:
   - `check_lifecycle_consistency` (validation.py:218-220) — Rule 7 never inspects anything.
   - `check_notification_relationships` (validation.py:331-333) — Rule 14 never inspects anything.
   - `check_schedule_impact_calculations` (validation.py:335-337) — Rule 15 never inspects anything.
2. **Guaranteed pass** — `check_date_ordering` increments `passed_checks` in *both* branches (validation.py:176-180).
3. **Outcome ignored** — `check_approval_consistency` collects `unapproved_updates` then unconditionally `passed_checks += 1` (validation.py:222-247).
4. **Sentinel, not detection** — `check_revision_ordering` flags only `revision_no <= 0` (validation.py:262-263). The generator's "older revision overwrites newer" scenario is implemented by *setting the revision number to 0* (generator.py:662). The validator therefore detects the mutation, not the business condition.
5. **Executed PoC (this audit)** — a line where rev 2 exists and rev 1 arrives afterwards (the real defect) produces `anomalies: []`, `failed_checks: 0`.
6. **Circular metric** — ground truth is produced by the same generator that the validator is scoring, in the same run (`validation.py:339-369`). "Precision 1.0 / Recall 1.0" measures generator↔validator agreement on hand-placed records, not detection capability.

**Impact**
The claimed "15 validation checks, 0 failures, 100% precision/recall" is not evidence of data quality. Six rules cannot fail; one cannot detect the condition it names; the score is self-referential. Any reviewer relying on `/api/data-quality/summary` is being told the dataset is clean by construction.

**Attack Scenario**
A real chronology regression (acknowledgement rev 1 arriving after rev 2 and overwriting it) is loaded into the database. All 15 checks pass, Precision stays 1.0, the Exceptions page shows nothing, and downstream consumers trust a corrupted revision chain.

**Recommendation**
Replace stubs with real assertions or delete them from the "15 rules" count (do not keep fake passes). Implement revision regression detection via `(po_line_id, revision_no, effective_at)` ordering and revision-chain continuity. Score precision/recall against an **independently authored** ground-truth fixture, not against records the same generator mutated. Publish `rules_implemented` vs `rules_stubbed` in the API response.

**Verification**
Re-run the audit PoC against the fixed validator → anomaly detected. Inject 5 unlabeled real defects into a fixture → recall must be computable and < 1.0 if any are missed.

---

### AUDIT-009 — Internal exception text returned to clients

```text
ID: AUDIT-009
Title: HTTP 500 handlers echo raw exception strings (SQL/ORM internals) to the caller
Severity: High
Component: Error handling
Affected Files: backend/routes.py:224-225, 242-243, 368-369, 439-440, 507-508, 536-537
```

**Evidence**
- `routes.py:225` — `raise HTTPException(status_code=500, detail=str(exc))` in `approve_change`.
- `routes.py:243`, `369`, `440`, `508`, `536` — same pattern for reject, seed, reproducibility, export, synthetic export.
- `services.py:236`, `294`, `451` wrap the underlying driver/ORM exception into `RuntimeError(f"... {exc}")`, so SQL text, table/column names, and driver messages propagate to the HTTP layer.

**Impact**
Information disclosure of schema internals, SQL fragments, file paths, and (on connection errors) DSN/host details — useful reconnaissance for injection or targeted abuse. It also makes the API's failure semantics unstable for clients.

**Recommendation**
Log the full exception server-side with a correlation ID; return a generic message + that ID. Never interpolate `str(exc)` into a response. Add a global exception handler with a typed error envelope.

**Verification**
Force a DB error (stop MySQL) → response body contains a correlation ID only, no SQL, no file paths, no credentials; server log contains the detail.

---

## 4. MEDIUM FINDINGS

### AUDIT-010 — Unbounded export + N+1 queries + CPU-heavy endpoint

**Files:** `backend/services.py:571-592`, `backend/routes.py:443-537`, `434-440`
`export_operational_dataset` calls `.all()` with no cap (10,000 POs, 12,477 lines, 15,319 imports/revisions) and then `len(r.lines)` per PO (services.py:589) — one extra query per row (10,001 queries per export). `/api/data-quality/reproducibility` (routes.py:434-440) runs **two full generator passes per request** with no caching. No auth, no rate limit. Impact: trivial memory/CPU exhaustion and slow responses; `?search=` runs unbounded `%term%` scans. Recommendation: stream exports with a hard row cap, `selectinload`/aggregate `lines_count` in one query, gate exports by role, and cache or precompute reproducibility. Verification: 10k-row export completes with a bounded query count (`echo` of SQL / `EXPLAIN`); concurrent 5 exports do not exceed memory budget.

### AUDIT-011 — Unpinned backend dependencies

**Files:** `backend/requirements.txt` (all `>=`, no upper bounds, no lockfile, no hashes); `run.bat:75` installs them at first run.
Impact: non-reproducible installs and supply-chain exposure (a compromised or breaking release is pulled silently); `--system-site-packages` in `run.bat:62` leaks host packages into the venv. Recommendation: pin exact versions with hashes (`pip-compile` / `uv lock`), commit the lockfile, drop `--system-site-packages`, and add `pip-audit` to the validation profile. Verification: two fresh installs produce identical `pip freeze`; `pip-audit` reports no known CVEs.

### AUDIT-012 — Inflated validation metric

**Files:** `data/validation_summary.json` (`passed_checks: 35`), `backend/routes.py:372-431`, `tests/test_project.py:402-403`, `README.md:339`.
The UI/README advertise "15 validation rules" and "15/15 passed"; the actual counter reports **35** (12 PK tables + 11 FK checks + 13 others), and the test only asserts `>= 15`. Impact: meaningless quality indicator that cannot regress visibly. Recommendation: report `rules_total`, `rules_implemented`, `rules_passed`, `rules_failed`, `rules_skipped` as separate integers and assert exact values. Verification: a deliberately broken fixture makes `rules_failed > 0`.

### AUDIT-013 — Dual schema truth

**Files:** `database/schema.sql` (201 lines) vs `backend/models.py`; runtime uses `Base.metadata.create_all` (`database.py:77-85`).
Drift already exists: schema.sql declares `idx_supplier_status`, `DEFAULT`s on `created_at` handling, and `ON UPDATE CASCADE` clauses that the ORM models do not (models.py:23-38); enum type names are declared in the ORM but are inline in SQL. Impact: a manual `schema.sql` apply and an ORM `create_all` produce different databases; migrations are impossible to reason about. Recommendation: choose one source of truth (Alembic migrations derived from models) and delete or auto-generate the SQL file. Verification: fresh DB created by either path produces identical `SHOW CREATE TABLE` output.

### AUDIT-014 — No rate limiting, payload caps, or attack-surface reduction

**Files:** `backend/main.py:46-53` (docs/redoc enabled), `71-78` (`/health` discloses DB connectivity), no middleware for limits.
Impact: enumeration of the whole dataset by paging, regex/wildcard scan abuse via `search`, resource exhaustion, and public API documentation on a system with no auth. Recommendation: disable `/docs` unless `ENV=dev`, add rate limiting (e.g. slowapi) and max page/body sizes, and reduce `/health` to liveness only. Verification: 100 rapid requests → 429; `/docs` 404 when `ENV=prod`.

### AUDIT-015 — Non-deterministic seed path

**Files:** `backend/services.py:400` (`datetime.now()` for `exception_records.detected_at`), `185/257` (`datetime.utcnow()`), `217/275` (timestamp-based IDs).
The generator is seeded and reproducible **in memory**, but the persisted rows carry wall-clock timestamps and timestamp-derived IDs, so two seeds at different times produce different table contents. Impact: the reproducibility claim (README §13) holds only for the in-memory `generate_all()` comparison, not for the database; `utcnow()` is deprecated on Python 3.12+ and naive. Recommendation: derive all timestamps from the fixed seed epoch, use `datetime.now(UTC)` at the API boundary only, and add a DB-level reproducibility test (row hash of the whole table). Verification: seed → dump → drop → seed again → identical row hashes including `detected_at`.

### AUDIT-016 — FK checks disabled on a pooled connection

**Files:** `backend/services.py:416-425, 444-451`
`SET FOREIGN_KEY_CHECKS = 0` is a **session** variable; if the process dies (or an exception path misses the reset) between disable and re-enable, the connection returns to the pool with FK enforcement off, silently permitting orphan rows for later requests. Recommendation: use a dedicated short-lived engine/connection for reseed, wrap with `try/finally` at the connection level, and verify `@@FOREIGN_KEY_CHECKS = 1` before returning the connection (or `engine.dispose()` after reseed). Verification: kill the process mid-reseed, restart, insert an orphan child row → must fail.

---

## 5. LOW FINDINGS

- **AUDIT-017** — `schemas.py:11-16` `PaginatedResponse.items: List[Any]` bypasses response-model validation for every list endpoint; `from_orm` (routes.py:114, 257, 274, 293, 314, 341) is deprecated under Pydantic v2 (`model_validate` is the correct call). Impact: contract drift goes undetected.
- **AUDIT-018** — `main.py:59-65`: `allow_credentials=True` combined with `allow_methods=["*"]`, `allow_headers=["*"]`. Safe today only because origins are explicit; a single `CORS_ORIGINS=*` misconfiguration silently breaks the credential model. Impact: latent misconfiguration.
- **AUDIT-019** — Doc drift: `tests/test_project.py:3` says "20 required test criteria" while 30 exist; `README.md:148` says "20 automated pytest test cases"; `README.md:339` says 30; validation count is 15 in docs, 35 in data. Impact: reviewers cannot trust stated numbers.
- **AUDIT-020** — Tests require live MySQL and a pre-seeded 10k dataset (`test_project.py:367-389`), so they cannot run in CI or on a fresh clone. `test_11` (lines 152-160) wraps the assertion in `if applied_chg:` — with an empty DB it passes vacuously. Current environment confirms this: no MySQL listener on 3306, no runnable venv (Windows `venv/Scripts`), `python3 -c "import fastapi"` → `ModuleNotFoundError`. The "30 passed" claim is **not reproducible here**.
- **AUDIT-021** — Zero knowledge artifacts: no ADR, no `DECISIONS.md`, no lessons/patterns, no CI config, no lint/type config (no Ruff, no Pyrefly, no mypy). INV-007 blocker if this project is ever proposed for Gate 6.

---

## 6. WHAT IS ACTUALLY GOOD

Stated so the audit stays honest, not one-sided:

- **Domain model is well-formed.** 13 tables, correct FK direction, `ondelete` semantics, enum domains, sensible indexes; `inventory_plans.po_line_id` is `unique` (models.py:182) which structurally prevents duplicate plans.
- **Transaction discipline exists** in the approval path: `db.add` → commit → `rollback()` on exception (services.py:184-236). The *shape* is right; the locks and validations are missing.
- **Reject path genuinely preserves supply** (services.py:272) — the core invariant "rejected changes must not touch projected supply" is respected in the reject handler.
- **Deterministic generation** is real (fixed seed, `random.Random(seed)`, dual-run checksum comparison in `run_reproducibility_test`), limited only by the timestamp issue in AUDIT-015.
- **Exports are genuine** (`openpyxl` XLSX, `utf-8-sig` CSV) with a whitelist (`services.py:531-544`), no path traversal in the synthetic branch (routes.py:511-517).
- **`.gitignore` is correct** about `.env`, `venv/`, `node_modules/`, `data/*.csv|json`.

---

## 7. EVIDENCE AUDIT

| # | Claim | Evidence | Verdict |
|---|---|---|---|
| 1 | "Enforce strict approval thresholds before changes affect supply" (README:14) | `evaluate_approval_requirement` called only at `generator.py:431`; `services.py:163-236` has no threshold logic | ❌ CONTRADICTED |
| 2 | "Auditable platform" (README:11) | `reviewer_id` accepted from request body (`schemas.py:107-109`, `Approvals.jsx:63`); no auth anywhere | ❌ CONTRADICTED |
| 3 | "15 validation rules … 15/15 passed, 0 failures" (README:339, `/api/data-quality/summary`) | 6 rules cannot fail (`validation.py:176-180, 218-220, 222-247, 331-337`); counter actually reports 35 (`data/validation_summary.json`) | ❌ CONTRADICTED |
| 4 | "Detects regressed revision / older revision overwrites newer" (README:325) | `check_revision_ordering` tests `revision_no <= 0` (`validation.py:262`); generator writes `0` (`generator.py:662`); PoC on a real rev2→rev1 regression returned `anomalies: []` | ❌ CONTRADICTED |
| 5 | "Precision 1.0 / Recall 1.0 / F1 1.0" (README:331-333) | Computed in-run from generator-authored ground truth against the same run's detections (`validation.py:339-369`); circular | ❌ CONTRADICTED (as evidence of detection ability) |
| 6 | "Transactional approval with rollback" | commit/rollback present (`services.py:226, 235`), but no row lock, no idempotency, timestamp-PK collisions (`services.py:217`) | ⚠️ PARTIAL |
| 7 | "Rejected changes leave plans unchanged" | `services.py:272` deliberately skips the plan update; `test_10` asserts it | ✅ VERIFIED |
| 8 | "Genuine .xlsx export, not renamed CSV" | `openpyxl.Workbook` + MIME type (`services.py:796-839`); `test_22` parses with openpyxl | ✅ VERIFIED |
| 9 | "Deterministic, reproducible dataset (seed 20261022)" | In-memory dual-run checksum (`services.py:479-527`) ✅; persisted rows use `datetime.now()` (`services.py:400`) and timestamp IDs → DB not reproducible | ⚠️ PARTIAL / ❌ at row level |
| 10 | "30 automated tests pass (25.74s)" (README:378) | Not reproducible in this environment: no MySQL listener, no Linux venv, `fastapi` not importable | ⚠️ UNVERIFIED |
| 11 | "Local-only, safe deployment" | `run.bat:154` binds `127.0.0.1` ✅, but no auth + drive-by CSRF on body-less POSTs | ⚠️ PARTIAL |
| 12 | "Credentials come from `.env`" | `database.py:21` hardcodes the real password as a code default | ❌ CONTRADICTED |
| 13 | "Approval recalculates ScheduleImpact" (services.py:174 docstring) | `calculate_schedule_impact` imported at `services.py:18`, never called | ❌ CONTRADICTED |
| 14 | "4 negative scenarios detected with 0 false positives" | Scenario-4 detection is sentinel-based (see #4); Scenario-1 is a value-equality heuristic (`validation.py:238`) | ⚠️ UNVERIFIED |
| 15 | "All 10 entity tables + audit tables, schema in SQL" | `schema.sql` and ORM models diverge (indexes, defaults, cascades) | ⚠️ PARTIAL |

---

## 8. REQUIRED FIX ORDER (Gate 3 → re-audit)

1. **Rotate the DB password**; remove the hardcoded default; provision a least-privilege DB user. *(AUDIT-003)*
2. **Add the identity layer**: auth dependency, server-derived `reviewer_id`, role checks on approve/reject/resolve/seed, audit-log table with before/after. *(AUDIT-001)*
3. **Remove or gate the reseed endpoint** behind admin role + CSRF protection; move it to a CLI. *(AUDIT-002)*
4. **Enforce thresholds** at decision time and persist `required_tier` + `computed_variance`. *(AUDIT-004)*
5. **Implement per-type application** and **recompute ScheduleImpact** inside the approval transaction. *(AUDIT-005, AUDIT-006)*
6. **Lock + idempotency + UUID notification IDs + 409 semantics.** *(AUDIT-007)*
7. **Rewrite the validator**: real assertions or explicit `rules_skipped`; independent ground truth; real revision-regression detection. *(AUDIT-008)*
8. **Sanitize error responses** with correlation IDs. *(AUDIT-009)*
9. Then the Medium/Low batch: export caps + eager loading, pinned deps, single schema source, rate limits, deterministic timestamps, connection hygiene.

**Re-audit triggers:** items 1-6 must land together (they are one trust-boundary change). Items 7-8 can ship independently.

---

## 9. SCOPE & LIMITATIONS

- Read-only static review + one executed PoC (`backend/validation.py` imported directly; no project files modified).
- **Not executed:** the pytest suite and any live API calls — no MySQL on 3306, no Linux-runnable venv (`venv/` is a Windows layout), FastAPI not installed for `python3`. All runtime-behaviour findings are code-derived, not observed.
- The `data/*.json` artifacts were inspected but not independently regenerated.
- Frontend reviewed for XSS sinks and secret handling (grep for `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `localStorage`, `document.cookie` → no hits); a full UI review was out of scope.

**Auditor sign-off:** Chandra — Gate 5 REJECTED. This implementation may not proceed to Gate 6.
