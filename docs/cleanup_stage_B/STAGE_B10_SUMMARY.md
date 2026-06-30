# Stage B.10 — Summary

**Date:** 2026-06-30  
**Stage:** B.10 complete — external archive move  
**Commit:** Not performed (per B.10 rules)

---

## What was moved

| Item | Detail |
|------|--------|
| **Source** | `archive/` (repository root) |
| **Destination** | `../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/` |
| **Size** | ~2.0 GB |
| **Files** | 8,432 |
| **Contents** | Stage B cleanup archive: superseded Layer 3 batches + Layer 2.5 scratch |

**Active project directory reduction:** ~2 GB removed from `3Layers_project/` tree (folder now lives sibling to project under `gaga_psylo_external_archive/`).

---

## What was not moved

| Path | Size (approx) | Notes |
|------|---------------|-------|
| `Layer2_Motive_Kinematics/outputs/archive/` | ~22 GB | **Stage C** — explicitly untouched |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | ~3.6 GB | Canonical batch |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | ~1 MB | Poster CSVs |
| `outputs/poster_final_figures/` | ~13 MB | Poster deliverables |
| Raw data (`**/data/**`, `671_test_data_des/`) | — | Not touched |
| Layer 2 active session outputs | ~31 GB | Not touched |
| Layer 2.5 active exports | ~1.2 GB | Not touched |

No files deleted. No code edited.

---

## Active analysis and poster paths

All verified **intact** after move:

| Path | Status |
|------|--------|
| Canonical batch `193319` | OK |
| `poster_ready_evidence_package/` | OK |
| `outputs/poster_final_figures/` | OK |
| Layer 2 `outputs/archive/` | OK (unchanged, still in repo) |

Poster reproduction does not depend on the moved external archive.

---

## Stage C

**Not started.** Layer 2 `outputs/archive/` (~22 GB) remains in the project; deferred per prior cleanup plan.

---

## Documentation created (uncommitted)

| File | Purpose |
|------|---------|
| `STAGE_B10_MOVE_PLAN.md` | Pre-move plan and safety analysis |
| `STAGE_B10_MOVE_LOG.md` | Commands, verification, restore |
| `STAGE_B10_SUMMARY.md` | This summary |

---

## Recommended next steps

1. **Optional doc commit** — stage B.10 documentation only (explicit paths; no `git add .`).

2. **Manual review** (from B.9) — resolve `671_test_data_des/` export type and Layer 2 Git legacy (775 tracked output files) before Stage C.

3. **Stage C** (later) — move `Layer2_Motive_Kinematics/outputs/archive/` (~22 GB) outside repo after backup and untrack plan.

4. **Optional** — add pointer in `PROJECT_STATUS.md` / `CLEANUP_INDEX.md` to external archive location when committing B.10 docs.

---

*Stage B.10 complete. Recoverable via restore command in `STAGE_B10_MOVE_LOG.md`.*
