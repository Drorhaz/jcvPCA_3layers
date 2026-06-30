# Stage B Move Plan — Controlled Archiving

**Date:** 2026-06-30  
**Stage:** B — move only (no deletions, no code changes, no raw-data moves)  
**Archive root:** `archive/2026-06-30_cleanup_stage_B/`

---

## Scope summary

| Group | Items | Total size (approx) | Risk |
|-------|-------|---------------------|------|
| A — Superseded Layer 3 batches | 5 folders | ~1.42 GB | Low |
| B — Layer 2.5 scratch/archive | 2 folders | ~656 MB | Medium |
| **Total planned moves** | **7 top-level folders** | **~2.08 GB** | — |

**Explicitly excluded from Stage B** (per instructions + Stage A): Layer 2 `outputs/archive/` (22 GB), raw data, `671_test_data_des/`, poster packages, canonical batch `193319`, source code, workbench folders.

---

## Group A — Superseded Layer 3 batch runs

**Destination base:** `archive/2026-06-30_cleanup_stage_B/layer3_superseded_batches/`

| # | Current path | Destination path | Size | Risk | Reason | Stage A evidence | Reversible | Affects poster | Affects batch 193319 |
|---|--------------|------------------|------|------|--------|------------------|------------|----------------|----------------------|
| A1 | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_174553/` | `archive/2026-06-30_cleanup_stage_B/layer3_superseded_batches/gaga_batch_jcvpca_20260626_174553/` | 91 MB | Low | Failed smoke run: 0/20 completed | `layer3_batch_comparison.md`, `batch_summary.md` | Yes (`mv` back) | No — not in poster script paths | No |
| A2 | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_175138/` | `archive/2026-06-30_cleanup_stage_B/layer3_superseded_batches/gaga_batch_jcvpca_20260626_175138/` | 91 MB | Low | Partial 671-only run (6/20) | `layer3_batch_comparison.md` | Yes | No | No |
| A3 | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_180044/` | `archive/2026-06-30_cleanup_stage_B/layer3_superseded_batches/gaga_batch_jcvpca_20260626_180044/` | 91 MB | Low | Duplicate partial run pattern | `layer3_batch_comparison.md` | Yes | No | No |
| A4 | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193110/` | `archive/2026-06-30_cleanup_stage_B/layer3_superseded_batches/gaga_batch_jcvpca_20260626_193110/` | 780 MB | Low | Superseded full core; `jcvpca_link_results.csv` matches 193319 but lacks downstream reports | `checksum_comparison.csv`, `layer3_batch_comparison.md` | Yes | No — poster uses 193319 + evidence package | No |
| A5 | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193235/` | `archive/2026-06-30_cleanup_stage_B/layer3_superseded_batches/gaga_batch_jcvpca_20260626_193235/` | 371 MB | Low | Partial 671-only run (10/20) | `layer3_batch_comparison.md` | Yes | No | No |

**NOT moving (canonical):** `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` (3.6 GB) — keep active.

---

## Group B — Layer 2.5 scratch/archive folders

**Destination base:** `archive/2026-06-30_cleanup_stage_B/layer2_5_scratch_archive/`

| # | Current path | Destination path | Size | Risk | Reason | Stage A evidence | Reversible | Affects poster | Affects batch 193319 |
|---|--------------|------------------|------|------|--------|------------------|------------|----------------|----------------------|
| B1 | `Layer2.5_Segmentation/reevluate_project/` | `archive/2026-06-30_cleanup_stage_B/layer2_5_scratch_archive/reevluate_project/` | 318 MB | Medium | Scratch re-evaluation; 671 CSV duplicates Layer 1; parquets regeneratable | `checksum_comparison.csv`, `proposed_archive_manifest.csv` | Yes | No — not in poster chain | No |
| B2 | `Layer2.5_Segmentation/outputs/archive/` | `archive/2026-06-30_cleanup_stage_B/layer2_5_scratch_archive/outputs/archive/` | 338 MB | Medium | Superseded Layer 2.5 exports | `proposed_archive_manifest.csv`, `STAGE_A_SUMMARY.md` | Yes | No — active exports remain in `outputs/pre_jvcpca_review/` | No |

**NOT moving:** `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` (active JcvPCA-ready exports, 1.2 GB).

---

## Group C — Deferred (Stage B will NOT move)

| Path | Size | Reason deferred |
|------|------|-----------------|
| `Layer2_Motive_Kinematics/outputs/archive/` | ~22 GB | Older pipeline outputs; not byte-identical to active stage08 — Stage C after poster submission |
| Layer 3 `_workbench_*` folders | ~10 MB | Not in Stage B allowed list |
| Raw data, `671_test_data_des/`, segmentation xlsx | — | Explicit prohibition |

---

## Pre-move verification checklist

- [ ] All 7 source paths exist
- [ ] Canonical batch `193319` exists and will not be moved
- [ ] `poster_ready_evidence_package/` untouched
- [ ] `outputs/poster_final_figures/` untouched
- [ ] Archive destination directories created before move

---

## Post-move verification checklist

- [ ] Each original path no longer exists
- [ ] Each destination path exists
- [ ] `gaga_batch_jcvpca_20260626_193319` still present
- [ ] Poster files still present
- [ ] No raw data paths moved
- [ ] `move_log.csv` complete

---

## Reversal procedure

To undo Stage B, move each folder from `archive/2026-06-30_cleanup_stage_B/...` back to its **original_path** listed above. No renames required.

---

*Move plan written before execution. See `move_log.csv` and `STAGE_B_SUMMARY.md` for results.*
