# docs/ — Project Evidence & Setup Documentation

**Owner:** Ajay (content) · Abhi (writes/maintains) · Chandra (verifies)
**Rule:** this folder is a **mirror of evidence**, not a second source of truth.

## Single Source of Truth

| Artifact type | Source of truth | This folder |
|---|---|---|
| Gate 1 / Gate 5 audit reports | `~/ABHI/AbhiMemories/AuditLogs/` | **immutable snapshot** (provenance header + SHA-256) |
| Architecture decisions | this folder (`02-architecture/ADR-*.md`) | authoritative |
| Setup instructions | this folder (`01-setup/`) | authoritative |
| Verification evidence | `03-verification/VERIFICATION-LOG.md` | authoritative, append-only |
| Plan | `~/ABHI/AbhiMemories/Plans/2026-10-31-yottaflexai3/implementation_plan.md` | not copied |

**Never edit a snapshot.** If the original changes, re-snapshot under a new filename and update `SHA256SUMS`.

## Index

| Path | What it answers |
|---|---|
| `00-baseline/chandra-audit-2026-10-31.md` | What is wrong with the build? (Gate 5, 21 findings) |
| `00-baseline/spec-compliance-2026-10-31.md` | Does the build satisfy the problem statement? (Gate 1, 73 checkpoints) |
| `00-baseline/integrity-manifest-2026-10-31.txt` | What exactly was the tree at the baseline commit? |
| `00-baseline/SHA256SUMS` | Are the snapshots unmodified? |
| `01-setup/PREREQUISITES.md` | What must exist before setup starts? |
| `01-setup/SETUP-CHECKLIST.md` | Step-by-step, with expected output and remedies |
| `01-setup/RUNBOOK.md` | Start / stop / reseed / rotate / recover |
| `02-architecture/ADR-0001-config-and-envs.md` | Why `.venv`, one `.env`, pinned deps |
| `02-architecture/ID-CONVENTIONS.md` | Entity ID shapes (incl. known drift) |
| `02-architecture/INVARIANTS.md` | Rules the code must never break |
| `03-verification/VERIFICATION-LOG.md` | Evidence per task, append-only |

## Verify the snapshots

```powershell
cd docs\00-baseline
Get-Content SHA256SUMS | ForEach-Object {
  $h,$f = $_ -split '  ',2
  $actual = (Get-FileHash $f -Algorithm SHA256).Hash.ToLower()
  if ($actual -eq $h) { "OK   $f" } else { "FAIL $f" }
}
```
Expected: `OK` for every line. Any `FAIL` means the file was edited after snapshotting.
