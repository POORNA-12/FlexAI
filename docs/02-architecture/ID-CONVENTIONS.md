# ID CONVENTIONS

Two sources exist today and they disagree. This document records **both**, the authority for each entity, and the drift to be fixed in Phase B.

## Documented convention (`DATA_DICTIONARY.md` §2)

| Entity | Pattern | Example |
|---|---|---|
| Supplier | `SUP-0001` | `SUP-0001` |
| Item | `ITM-00001` | `ITM-00001` |
| Purchase Order | `PO-2026-000001` | `PO-2026-000001` |
| PO Line | `<po-id>-L01` | `PO-2026-000001-L01` |
| Acknowledgement | `ACK-<po-id>-<nn>` | `ACK-PO-2026-000001-01` |
| Promise Date | `PRM-<ack-id>-<nn>` | `PRM-ACK-PO-2026-000001-01-01` |
| Change Request | `CHG-<po-id>-<nnnnnn>` | `CHG-PO-2026-000001-000001` |
| Approval | `APR-<change-id>-<nn>` | `APR-CHG-PO-2026-000001-000001-01` |
| Inventory Plan | `PLAN-<po-line-id>` | `PLAN-PO-2026-000001-L01` |
| Production Order | `PRD-2026-000001` | `PRD-2026-000001` |
| Notification | `NOT-2026-000001` | `NOT-2026-000001` |
| Schedule Impact | `IMP-PRD-2026-000001-01` | `IMP-PRD-2026-000001-01` |
| Exception | `EXP-2026-000001` | `EXP-2026-000001` |

## Actual behaviour (measured)

| Entity | Generator | Runtime (services) | Status |
|---|---|---|---|
| PO / PO Line / Plan / PRD / IMP / EXP | matches | n/a (read-only) | ✅ |
| ACK | `ACK-{po_id}-{line_counter:02d}` | n/a | ✅ shape matches |
| CHG | `CHG-{po_id}-{line_counter:06d}` | n/a | ✅ shape matches (counter is a per-PO line index, not a change sequence — cosmetic) |
| **APR** | `APR-{change_id}-{global_counter:02d}` | `APR-{change_id}-REV{rev:02d}` | ❌ **two shapes, and the trailing number is a global counter** |
| **NOT** | `NOT-2026-{counter:06d}` | `NOT-{epoch_seconds}` | ❌ **runtime breaks the convention** |

### Evidence of the APR drift

```
first approvals : APR-CHG-PO-2026-000009-000001-02
                  APR-CHG-PO-2026-000010-000001-03
last approvals  : APR-CHG-PO-2026-009999-000001-3427
                  APR-CHG-PO-2026-010000-000002-3429
suffix widths   : {2, 3, 4}          ← 2-digit field overflows at approval #100
```

The trailing segment is the **global** approval index (`generator.py:403-406`), so `-3429` on the 3,429th approval says nothing about that change. The specification's `APR-<change-id>-01` and the dictionary's "2-digit approval counter" both imply a **per-change ordinal** (always `-01` for a first decision).

## Rules (authoritative going forward)

1. IDs are **immutable** once written.
2. Counters are **zero-padded and scoped**: `-01` is the first child of that parent, not the first child in the dataset.
3. A parent id is embedded verbatim; never re-derive it by splitting on `-`.
4. Generator and runtime must share **one** id factory (Phase B: `backend/ids.py`).
5. Any new entity must add its pattern here **before** code.

## Phase B work items

- [ ] `backend/ids.py` with `po()`, `po_line()`, `ack()`, `promise()`, `chg()`, `apr()`, `notif()`, `impact()`, `exception()`
- [ ] per-change approval ordinal
- [ ] runtime notification ids from the factory
- [ ] ID-format validation rule in `validation.py`
- [ ] regenerate `data/` and refresh `ground_truth` labelling
