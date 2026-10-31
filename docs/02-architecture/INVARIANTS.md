# INVARIANTS — rules the system must never break

Verified against `backend/models.py`, `backend/services.py`, `backend/validation.py`, `backend/generator.py` on 2026-10-31.

| ID | Invariant | Enforced where | Test |
|---|---|---|---|
| INV-1 | A pending or rejected change never modifies `inventory_plans.projected_supply` | `services.reject_change_request` (deliberate no-op), `generator._process_approvals_and_apply_plans` (gated on APPROVED) | `test_08`, `test_10`, `test_25` |
| INV-2 | Only an `APPROVED` decision may set a change to `APPLIED` | `services.approve_change_request:181` (status precondition) | `test_11` |
| INV-3 | An approval is recorded once per change/revision (PK `APR-<change>-<rev>`) | `approvals.approval_id` PK | `test_11` |
| INV-4 | One inventory plan per PO line | `inventory_plans.po_line_id` UNIQUE + `uselist=False` | schema + `test_02` |
| INV-5 | Every child row has a resolvable parent | FK constraints + `check_foreign_key_integrity` | `test_02` |
| INV-6 | Ground truth is never an input to generation | `ground_truth_records` written after rows are built; not read by the generator | `test_18` |
| INV-7 | Dataset is reproducible from `BASE_SEED = 20261022` | `random.Random(seed)` + `run_reproducibility_test` | `test_19` |
| INV-8 | Rejected changes preserve the original effective value | `services.reject_change_request:272` comment + code | `test_10` |
| INV-9 | Acceptance/rejection quantities reconcile with the ordered quantity | `check_quantity_reconciliation` | `test_04` |

## Known violations (tracked, not yet fixed)

| ID | Violation | Evidence | Phase |
|---|---|---|---|
| V-1 | `approved` price/date changes are marked `APPLIED` but never applied | `services.py:204` applies only `QUANTITY` | B |
| V-2 | `ScheduleImpact` is never recomputed after an approval | `calculate_schedule_impact` imported, never called | B |
| V-3 | Approval is not idempotent under concurrency (no row lock) | `services.py:177-182` read-then-act | B |
| V-4 | Supply value is overwritten without history | `services.py:206` | B |
| V-5 | Runtime `APR`/`NOT` IDs do not follow the documented convention | `services.py:186,217` | B |
| V-6 | Validation rules 7, 14, 15 always pass; rule 9 detects only `revision_no <= 0` | `validation.py:218,262,331,335` | B |

## Non-goals

- INV-1 does **not** claim referential integrity for the deliberately injected anomalies; those rows are labelled in `ground_truth_records` by design (problem statement Step 5).
