<!-- SNAPSHOT — DO NOT EDIT IN PLACE.
     source      : /home/poorna/ABHI/AbhiMemories/AuditLogs/2026-10-31-yottaflexai3-spec-compliance.md
     snapshot    : 2026-10-31
     sha256      : 1cffc7712fee1ccc6260a905e657b50e2b29fedf529b00503a13136c639a923a
     authority   : Chandra (Assurance Authority) — Gate 1
     rule        : the original is the source of truth; this file is an immutable copy.
-->

# Gate 1 — Requirement Compliance Matrix

**Project:** `yottaflexai3` — Supplier Acknowledgement and Schedule Impact Manager
**Spec:** Provided problem statement (business context, workflow rules, entities, ID conventions, 10 generation steps, volume, edge cases, validation, evaluation focus, provenance)
**Auditor:** Chandra (Assurance Authority) — evidence-only, read-only
**Date:** 2026-10-31
**Companion:** `2026-10-31-yottaflexai3-chandra-audit.md` (security audit, Gate 5)

---

## VERDICT

```text
Coverage: 31 of 44 spec points fully covered
         8 partial, 5 missing
Hard spec violations: 3   → these are the ones that lose marks
Status: NOT COMPLIANT YET — fixable with a bounded change set (see §5)
```

The build is structurally faithful: correct entities, correct FK direction, correct ID *shapes*, real deterministic generator, real ground-truth separation, real derived metrics. But three requirements the statement states explicitly are **contradicted by the code**, and several coverage items are cosmetic rather than real.

---

## 1. HARD VIOLATIONS (fix these first)

### ❌ V1 — "price changes" are never generated (0 of 3,429)

> Spec: *"Generate 10,000 POs and 15,000 acknowledgement/change events. Include partial acceptance, date slips, **price changes**, supplier silence and multiple revisions."*

**Evidence**
```
data/change_requests.csv → Counter({'QUANTITY': 2658, 'DELIVERY_DATE': 771})   # PRICE: 0, COMBINED: 0
backend/generator.py:261,269  → only change_type = "QUANTITY" | "DELIVERY_DATE" are ever assigned
backend/generator.py:424-429  → the PRICE branch in approval processing is dead code (unreachable)
```
`README.md:7` also advertises "quantity/price change proposals". Partial acceptance (2,126) and date slips (771) are real; price is absent, and `COMBINED` is absent entirely.

**Fix:** add a price-change branch (~10-15% of event lines) with `old_value = unit_price`, `new_value = unit_price * (1 + delta)`, deltas spanning the auto/planner/manager bands; make one `COMBINED` change per ~200 lines. Then verify the distribution and that the approval path applies the price.

---

### ❌ V2 — Approval outcomes are random, not rule-derived

> Spec Step 5/6: *"Generate outcomes and ground-truth labels from documented rules, **not independent random assignment**."* Also Rule 3: *"apply approval thresholds for price/date/quantity changes"*.

**Evidence**
```python
# backend/generator.py:439-442
roll = self.rng.random()
if roll < 0.65:  decision = "APPROVED"
    reviewer = "AUTO_SYSTEM" if not req_appr else "PLN-001"
```
- The threshold engine (`evaluate_approval_requirement`, line 431) is computed, then **only used to pick the reviewer label and a comment string**. The decision itself is a dice roll (65/20/15).
- Result: changes needing `OPERATIONS_MANAGER` sign-off get approved by `PLN-001` whenever the roll lands under 0.65 — 2,244 `APPLIED` changes include ones that policy says require escalation.
- The runtime path is worse: `services.approve_change_request` never calls the threshold engine at all (see audit AUDIT-004).

**Fix:** make the decision a function of `(tier, reviewer_role)`: `AUTO` → approved by `AUTO_SYSTEM`; `PLANNER` → planner decision; `OPERATIONS_MANAGER` → only an operations-manager id may approve, otherwise `PENDING_APPROVAL`. Keep the 65/20/15 distribution as the *planner's* behaviour, not as the rule. Persist `required_tier` + `computed_variance` on the approval row so the outcome is auditable.

---

### ❌ V3 — No SQL seed data, no source manifest

> Spec Step 9: *"Export CSV/JSON/**SQL seed data** plus README, schema/data dictionary, generator command, fixed seed, **source manifest** and validation summary."*

**Evidence**
```
database/schema.sql → 0 INSERT statements (DDL only)
ls | grep -i "manifest|source" → no file
data/ → purchase_orders.{csv,json} … (CSV+JSON only)
```
**Fix:** emit `database/seed.sql` (idempotent `INSERT … ON DUPLICATE KEY UPDATE`, FK-ordered, generated from the same deterministic run) and `data/SOURCE_MANIFEST.json` (generator version, seed `20261022`, scale, row counts, SHA-256 per file, generation command, "synthetic — no external data" provenance statement). Note: spec's public-data clause is satisfied by *not* using external data, but the manifest must say so explicitly.

---

## 2. PARTIAL / SECONDARY GAPS

### ⚠️ P1 — `APR` ID convention breaks at scale and differs between writers
```
Dictionary:  APR-CHG-PO-2026-000001-000001-01   ("APR-" + change-id + 2-digit approval counter)
Spec:        APR-<change-id>-01
Actual data: APR-CHG-PO-2026-000009-000001-02  …  APR-CHG-PO-2026-009999-000001-3427
             suffix widths observed: 2, 3 and 4 digits  → zero-pad convention broken
Runtime:     APR-{change_id}-REV{rev:02d}   (services.py:186) → yet another shape
```
The trailing segment is a **global** counter (generator.py:403-406), not the approval ordinal for that change; it overflows the documented 2-digit field at approval #100. Two different code paths mint `APR` ids with different shapes → "referenced IDs exactly consistent across files" fails for approvals.

**Fix:** per-change ordinal (`APR-<change-id>-01`, always `-01` for the first decision), one shared `id_factory` module used by generator *and* services, plus an ID-format validation rule.

### ⚠️ P2 — `NOT` ID convention broken at runtime
Generator: `NOT-2026-000001` ✓ (spec-compliant). Runtime: `f"NOT-{int(datetime.utcnow().timestamp())}"` (services.py:217,275) → e.g. `NOT-1793456789`. Same factory fix as P1; also removes the same-second PK collision.

### ⚠️ P3 — Lifecycle-transition validation is a stub
Spec Step 8 requires *"lifecycle transitions"* checking. `check_lifecycle_consistency` (validation.py:218-220) increments `passed_checks` and returns — it inspects nothing. Also no validator for `po_status` ↔ `po_line_status` ↔ `change_request.status` coherence. **Fix:** implement a transition table (allowed state graph per entity) and assert every row's status is reachable from its parent's state.

### ⚠️ P4 — Supplier silence exists as data but is not measurable
383 of 12,477 lines (3.07%) have no acknowledgement (`roll < 0.03`, generator.py:223-226). But: no silence exception record, no ground-truth label, no dashboard metric, no notification. `is_supplier_silent()` is only called by a unit test. Spec lists silence as required coverage and demands *measurable outputs*. **Fix:** emit `exception_records` rows (`issue_type = supplier_silence`, `severity = HIGH`, using `SUPPLIER_SILENCE_DAYS`) + an `open_supplier_silence` dashboard metric + a notification.

### ⚠️ P5 — No M:N bridge model; `schedule_impacts` is an undocumented bridge
Spec: *"Use bridge tables for many-to-many relationships… Document cardinality (1:1, 1:N, N:M)."* `DATA_DICTIONARY.md` documents only 1:1 / 1:N / N:1. The genuine M:N (ProductionOrder ↔ POLine) is de-facto bridged by `schedule_impacts`, but it is filed under "Auxiliary and Evaluation Tables" with no M:N cardinality, no uniqueness constraint on `(production_order_id, po_line_id)`, and `schedule_impacts.po_id` is a plain `String`, not an FK (models.py:238). Supplier↔Item (approved-vendor-list) has no bridge at all. **Fix:** document `schedule_impacts` as the M:N bridge with `UNIQUE(production_order_id, po_line_id)`, promote `po_id` to an FK, and add a documented `supplier_items` bridge.

### ⚠️ P6 — Two actor roles have no representation
Spec actors: supplier, planner, carrier/warehouse operator, logistics analyst, operations manager. Present: planner (`PLN-001`), supplier (as `Supplier`), analyst (read-only UI), plus the `AUTO_SYSTEM`/`OPERATIONS_MANAGER` strings in the rules. Missing as data/roles: **carrier/warehouse operator** (no entity, no `available_inventory` source, no dock/receipt concept) and **operations manager** (a tier string, but no role set, no reviewer id range, no escalation path). **Fix:** add a `roles`/`reviewers` reference table (`PLN-###`, `OPS-###`, `WH-###`) and an `inventory_source`/`warehouse` field so `available_inventory` is attributable.

### ⚠️ P7 — "Notify affected planners" is a single hardcoded recipient
`generator.py:556` → every notification goes to `PLN-001`. `services.py:218,276` → the runtime notification goes to the *reviewer*, not to affected planners. Approvals generate **no** notification; only PENDING/REJECTED do. **Fix:** map PO → owning planner(s), notify all affected planners on decision, and include a `notification_type` enum.

### ⚠️ P8 — State changes are mutated in place, not recorded as events
Spec Rule 4: *"Persist state changes as explicit records/events where relevant; do not overwrite history."* Approvals are appended ✓, but `change_requests.status` is overwritten (`PENDING → APPLIED`), `inventory_plans.projected_supply` is overwritten with only `effective_at` retained (previous value lost), and `po_status` never transitions at all. **Fix:** an append-only `change_request_events` / `inventory_plan_history` table, or at minimum a `supply_history` row (`plan_id, old_value, new_value, changed_at, approval_id`) written in the same transaction.

### ⚠️ P9 — Reproducibility demonstrated at dev scale only
`run_reproducibility_test` regenerates at `scale="dev"` (services.py:484-488) — checksums prove the *generator*, not the full 10,000-PO dataset. Additionally the persisted DB rows carry `datetime.now()` (services.py:400) and the report is regenerated on every `GET`. **Fix:** run the dual-generation comparison at the shipped scale (or both), include persisted-row hashes, and derive timestamps from the seed epoch.

### ⚠️ P10 — Validation counter is inflated (35 for 15 rules)
`data/validation_summary.json` → `passed_checks: 35`; docs/UI say 15 rules; the test only asserts `>= 15`. Six rules cannot fail (see audit AUDIT-008). **Fix:** report `rules_total / rules_implemented / rules_passed / rules_failed / rules_skipped` and assert exact values.

### ⚠️ P11 — Ground truth duplicated
`data/ground_truth.{csv,json}` and `data/ground_truth_records.{csv,json}` are identical (4 rows each). Spec asks for "a separate ground_truth.csv/json" — two files invite drift. **Fix:** keep one, document it in the manifest.

---

## 3. FULL COVERAGE MATRIX

| # | Spec point | Verdict | Evidence |
|---|---|---|---|
| 1 | End-to-end workflow: ack → promise → change → approval → supply → impact | ✅ | models.py 13 tables; services + UI pages; `test_17` |
| 2 | Expose key decisions and exceptions | ✅ | Approvals page, Exceptions page, `/api/exceptions` |
| 3 | Measurable outputs | ✅ | 10 dashboard metrics + formulas (services.py:62-73) |
| 4 | Actor: supplier | ✅ | `suppliers` entity, 100 rows |
| 5 | Actor: planner | ✅ | `PLN-001`, `reviewer_id` |
| 6 | Actor: logistics analyst | ✅ | read-only views/exports |
| 7 | Actor: carrier / warehouse operator | ❌ | no entity, no role, `available_inventory` has no source |
| 8 | Actor: operations manager | ⚠️ | tier string in rules only; no role, no reviewer id space |
| 9 | Rule 1: master data first | ✅ | generator order: suppliers → items → POs → lines |
| 10 | Rule 2: dependent records with valid parents | ✅ | FK order + validator FK check |
| 11 | Rule 3a: POs and lines created | ✅ | 10,000 / 12,477 |
| 12 | Rule 3b: acks with accepted/rejected + promised dates | ✅ | 12,599 acks, 4 statuses |
| 13 | Rule 3c: compare proposed vs requested | ✅ | `old_value`/`new_value` + variance math |
| 14 | Rule 3d: **apply approval thresholds** | ❌ | generator: decision is `rng.random()`; runtime: no check at all |
| 15 | Rule 3e: update supply only after approval | ✅ | generator.py:456-466 gated on APPROVED; services.py:202-213; `test_08/25` |
| 16 | Rule 3f: notify affected planners | ⚠️ | single hardcoded `PLN-001`; no notification on APPROVED |
| 17 | Rule 4: persist state changes as records; don't overwrite history | ⚠️ | approvals append-only ✓; supply/status overwritten in place |
| 18 | Rule 5: outcomes from documented rules, not random | ❌ | `roll = self.rng.random()` decides 65/20/15 |
| 19 | Core entity coverage (10) | ✅ | all 10 present + 3 auxiliary |
| 20 | PK for every entity | ✅ | models.py |
| 21 | FK for every relationship | ⚠️ | all core FKs ✓; `schedule_impacts.po_id` and `notifications` join not enforced |
| 22 | Cardinality documented | ✅ | `DATA_DICTIONARY.md` §3.1-3.10 |
| 23 | N:M + bridge tables | ⚠️ | de-facto bridge (`schedule_impacts`), undocumented as M:N, no `supplier_items` |
| 24 | Optional relationships documented | ✅ | nullable columns + dictionary |
| 25 | Effective dates | ✅ | `promise_dates.effective_at`, `inventory_plans.effective_at` |
| 26 | Lifecycle states documented | ✅ | dictionary per entity |
| 27 | Validate all joins | ⚠️ | 11 FK checks; silent lines, `po_id`, notification join unvalidated |
| 28 | Anomalies labelled, not silent corruption | ✅ | ground-truth rows per scenario |
| 29 | ID: `PO-2026-000001` | ✅ | generator.py:131 |
| 30 | ID: `ACK-<PO-id>-01` | ✅ | generator.py:232 (`ACK-PO-2026-000049-02`) |
| 31 | ID: `CHG-<PO-id>-000001` | ✅ | `CHG-PO-2026-000001-000001` |
| 32 | ID: `APR-<change-id>-01` | ❌ | global counter, widths 2/3/4, runtime uses `-REV01` |
| 33 | ID: `NOT-2026-000001` | ⚠️ | generator ✓; runtime uses epoch seconds |
| 34 | Step 1: data dictionary (type, req/opt, allowed, units, uniqueness, validation) | ✅ | DATA_DICTIONARY.md 16 KB, 8-column tables |
| 35 | Step 2: parent → child generation order | ✅ | `generate_all()` sequence |
| 36 | Step 3: deterministic, zero-padded, immutable, consistent | ⚠️ | deterministic ✓; APR/NOT drift breaks consistency |
| 37 | Step 4: 10,000 POs | ✅ | data + `test_27` |
| 38 | Step 4: 15,000 ack/change events | ✅ | 12,599 + 3,429 = **16,028** |
| 39 | Step 4: partial acceptance | ✅ | 2,126 |
| 40 | Step 4: date slips | ✅ | 771 |
| 41 | Step 4: **price changes** | ❌ | **0 rows** |
| 42 | Step 4: supplier silence | ⚠️ | 383 silent lines, unlabelled, unmeasured |
| 43 | Step 4: multiple revisions | ✅ | 503 rev-2 acks |
| 44 | Step 4: fixed seed + parameterised scale | ✅ | `BASE_SEED=20261022`, `dev`/`full` |
| 45 | Step 5: 4 labelled edge cases | ✅ | 4/4 injected, labelled, detected |
| 46 | Step 6: derived values computed | ✅ | totals, statuses, impacts, metrics |
| 47 | Step 7: separate ground truth, never in features | ✅ | own table + files; not read by generator |
| 48 | Step 8: PK uniqueness | ✅ | `check_primary_key_uniqueness` (12 tables) |
| 49 | Step 8: FK integrity | ✅ | 11 checks |
| 50 | Step 8: allowed enums | ✅ | 9 tables |
| 51 | Step 8: date ordering | ⚠️ | detects, but `passed_checks` incremented in both branches |
| 52 | Step 8: arithmetic reconciliation | ✅ | qty + totals |
| 53 | Step 8: **lifecycle transitions** | ❌ | stub (`validation.py:218-220`) |
| 54 | Step 8: duplicate checks | ✅ | ack (line, rev) duplicates |
| 55 | Step 9: CSV export | ✅ | `data/*.csv` |
| 56 | Step 9: JSON export | ✅ | `data/*.json` |
| 57 | Step 9: **SQL seed data** | ❌ | `schema.sql` = 0 INSERTs |
| 58 | Step 9: README | ✅ | 465 lines |
| 59 | Step 9: schema | ✅ | `database/schema.sql` |
| 60 | Step 9: data dictionary | ✅ | `DATA_DICTIONARY.md` |
| 61 | Step 9: generator command | ✅ | README §9.3 (UI, API, CLI) |
| 62 | Step 9: fixed seed documented | ✅ | README §9, §13 |
| 63 | Step 9: **source manifest** | ❌ | no file |
| 64 | Step 9: validation summary | ⚠️ | exists but count inflated (35 vs 15) |
| 65 | Step 10: dual-run reproducibility | ⚠️ | dev scale only; DB timestamps non-deterministic |
| 66 | Eval (a) realistic distributions | ⚠️ | 69% accept / 17% propose / 9% reject / 3% silence plausible; price band missing |
| 67 | Eval (b) consistent IDs, valid joins | ⚠️ | see 32/33/21 |
| 68 | Eval (c) dependency/lifecycle consistency | ⚠️ | lifecycle unvalidated |
| 69 | Eval (d) derived values reconcile | ✅ | qty/price/totals/impact |
| 70 | Eval (e) normal/boundary/failure/exception coverage | ⚠️ | boundary bands (threshold edges) not deliberately sampled |
| 71 | Eval (f) separate ground truth | ✅ | isolated, 4 labels |
| 72 | Eval (g) reproducibility, docs, lawful provenance | ⚠️ | reproducible ✓, docs ✓, provenance statement absent |
| 73 | Public data guidance | ✅ | no external data used (should be stated in manifest) |

---

## 4. WHAT IS ALREADY STRONG

- Entity model, FK direction, `ondelete` semantics, enum domains, unique plan-per-line.
- Deterministic generation with a real fixed seed and dual-run checksum comparison.
- The core invariant "pending/rejected changes never touch projected supply" is enforced in **both** the generator and the runtime, and tested (`test_08`, `test_10`, `test_25`).
- Ground truth is genuinely isolated from inputs.
- Derived values (PO totals, statuses, shortage qty, precision/recall) are computed, not invented.
- Documentation is unusually complete (465-line README + 16 KB dictionary).

---

## 5. MINIMUM CHANGE SET TO REACH FULL COVERAGE

| Priority | Gap | Change | Files |
|---|---|---|---|
| 1 | V2 rule-driven decisions | Replace `rng.random()` decision with tier-based policy; persist `required_tier`, `computed_variance` | `generator.py:439-488`, `services.py:163-236` |
| 2 | V1 price coverage | Add `PRICE` (+ some `COMBINED`) change generation with banded deltas; apply price on approval | `generator.py:252-305`, `services.py:200-213` |
| 3 | P1/P2 ID factory | Single `backend/ids.py` for PO/ACK/CHG/APR/NOT/PRM; per-change approval ordinal; use everywhere | new + `generator.py`, `services.py` |
| 4 | V3 SQL + manifest | `database/seed.sql` emitter + `data/SOURCE_MANIFEST.json` (seed, counts, SHA-256, command, "synthetic only") | new `backend/exporter.py` |
| 5 | P3 lifecycle | Real transition-table validator (PO, line, ack, change, plan) | `validation.py:218-220` |
| 6 | P4 silence | Silence exception rows + metric + notification | `generator.py:223`, `validation.py`, `services.py:23-87` |
| 7 | P5 M:N | Document `schedule_impacts` as bridge, add `UNIQUE(mo,line)`, FK `po_id`, add `supplier_items` | `models.py`, `schema.sql`, `DATA_DICTIONARY.md` |
| 8 | P8 history | `supply_history` append-only rows on approval | `models.py`, `services.py:202-213` |
| 9 | P7 notifications | PO→planner map, notify on decision | `generator.py:549-562`, `services.py` |
| 10 | P6 roles | `reviewers` table (`PLN/OPS/WH`) + warehouse source for `available_inventory` | `models.py`, dictionary |
| 11 | P9/P10/P11 | Full-scale reproducibility, honest rule counters, single ground-truth file | `services.py:479`, `routes.py:418-431` |

Items 1-4 close every ❌ in §3. Items 5-11 close every ⚠️. None of them require redesign — the data model accommodates all of it.

---

## 6. SCOPE NOTE

Read-only review. No project files were modified. The suite could not be executed (no MySQL listener on 3306, Windows-layout `venv/`, FastAPI not importable under `python3`), so all row counts come from the shipped `data/*.csv|json` exports and the code, not from a live run. Where the exports and the README disagree (price changes, validation counts), the exports win — they are artifacts of an actual generation.
