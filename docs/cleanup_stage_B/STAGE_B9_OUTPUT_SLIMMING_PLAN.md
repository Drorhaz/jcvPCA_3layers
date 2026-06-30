# Stage B.9 — Output Folder Slimming Plan

**Date:** 2026-06-30  
**Scope:** Audit and recommendations only — **no moves, deletions, or commits**  
**Data source:** [`STAGE_B9_OUTPUT_FOLDER_AUDIT.csv`](STAGE_B9_OUTPUT_FOLDER_AUDIT.csv)  
**Git baseline:** checkpoint `393fb68`, docs `c6cc222`

---

## Executive summary

The project’s visual weight is dominated by **generated outputs on disk**, not by Git-tracked content. After Stage B.6 `.gitignore`, most large folders are **ignored** but still occupy space.

| Tier | Approx. size | Primary paths |
|------|-------------|---------------|
| **Tier 1 (critical)** | ~3.6 GB + ~1 MB | Canonical batch `193319`, poster evidence package |
| **Tier 2 (active pipeline)** | ~32 GB + ~1.2 GB | Layer 2 active sessions, Layer 2.5 exports |
| **Tier 3 (relocatable archive)** | ~24 GB | Top-level `archive/` (~2 GB) + Layer 2 `outputs/archive/` (~22 GB) |
| **Tier 4 (review)** | ~232 MB | `671_test_data_des/` |

**Audited folders ≥50 MB:** 22 rows in CSV (~130 GB if summed naively — paths overlap; unique disk total remains ~85 GB project-wide per Stage A inventory).

---

## Important: `.gitignore` ≠ smaller folders

**`.gitignore` prevents files from being tracked by Git; it does not remove them from disk or reduce folder size.**

Stage B.6 successfully stopped ~33k generated files from appearing in `git status`, but:

- `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` (~3.6 GB) is still on disk
- `archive/` (~2 GB) is still on disk
- `Layer2_Motive_Kinematics/outputs/` (~54 GB) is still on disk and **775 files remain in the Git index** from before ignore rules

Slimming requires **physical relocation or deletion** (with backup), not gitignore alone.

---

## Scan methodology

Directories scanned for names containing or equal to:

`outputs`, `output`, `figures`, `plots`, `reports`, `batch`, `_workbench`, `_archive`, `archive`, `poster`

**Threshold for CSV rows:** ≥50 MB (meaningful parent folders; nested `plots/` subfolders excluded to avoid thousands of duplicate rows).

**Git status labels:**

| Label | Meaning |
|-------|---------|
| `ignored` | `git check-ignore` matches; no tracked files under path |
| `tracked(N)` | N files in Git index under path |
| `mixed_*` | Some tracked legacy files + gitignore for new adds |
| `untracked_visible` | Not ignored, not in index |

---

## Group A — Must keep visible in active project

These paths support poster reproduction, canonical analysis, or active pipeline inputs.

| Path | Size | Role |
|------|------|------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | **3,608 MB** | Canonical Layer 3 batch — hard-coded in `make_poster_*.py` |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | **~1 MB** | Primary poster CSV source (below 50 MB; not in CSV) |
| `outputs/poster_final_figures/` | **~13 MB** | Poster scripts output; CSV/MD tracked, binaries gitignored |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` (active 671/252 exports) | **~906 MB** active portion of 1,206 MB tree | Layer 3 matrix inputs |
| `Layer2_Motive_Kinematics/outputs/*_Take_*/` (12 active sessions) | **~31,346 MB** aggregate | Upstream kinematics for Layer 2.5 |
| `Layer2_Motive_Kinematics/outputs/layer2_exports/` | **1,049 MB** | Parquet bundle for Layer 2.5 (gitignored) |

**Recommendation:** Keep on disk through poster submission. Do not move or delete without verified regeneration chain.

**Risk:** **High** if disturbed before poster.

---

## Group B — Keep on disk but hide/ignore from Git

Useful generated outputs that should not inflate Git; mostly already gitignored in B.6.

| Path | Size | Notes |
|------|------|-------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | 3,608 MB | Ignored; Group A for science, Group B for Git hygiene |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/` and `252/` | bulk of L2.5 tree | Gitignored export trees |
| `Layer2_Motive_Kinematics/outputs/layer2_exports/` | 1,049 MB | Gitignored |
| `Layer2_Motive_Kinematics/outputs/*_Take_*/` (252 sessions) | ~14 GB of aggregate | Gitignored for new files |
| `Layer3_JcvPCA/outputs/_workbench_*` (8 dirs) | **~6 MB total** | Exploratory workbench runs; gitignored |
| `Layer1_motive_qc/motive_qc/outputs/runs/` and `batch_runs/` | portion of 68 MB tree | Gitignored; 234 legacy tracked files remain at parent |

**Follow-up (not B.9):** Optional second commit to **untrack** legacy Layer 1/Layer 2 output files still in index (`git rm --cached` with explicit paths) — reduces Git noise without changing disk.

**Risk:** **Low–medium** for Git cleanup; **high** if disk copies deleted.

---

## Group C — Move to internal archive

Already archived or superseded; safe to consolidate under an external backup root **after documentation**.

| Path | Size | Notes |
|------|------|-------|
| `archive/` (top-level) | **2,059 MB** | Stage B moves; gitignored |
| `archive/2026-06-30_cleanup_stage_B/layer3_superseded_batches/` | 1,403 MB | 5 superseded batches |
| `archive/2026-06-30_cleanup_stage_B/layer2_5_scratch_archive/` | 656 MB | reevluate + old L2.5 scratch |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/_archive/` | 300 MB | 2026-06-26 refresh snapshot + tar.gz |

**Recommendation:** Move together to an external `_project_archive/` folder outside the repo (Stage B.10). Keep `move_log.csv` pointer updated.

**Risk:** **Low** — superseded or snapshot-only; canonical paths unaffected.

---

## Group D — Move outside the project directory

Very large; useful as backup/history but dominate project size and IDE file trees.

| Path | Size | Priority |
|------|------|----------|
| `Layer2_Motive_Kinematics/outputs/archive/` | **22,543 MB** | **Stage C** — largest single win |
| `archive/` (top-level) | **2,059 MB** | **Stage B.10** — quick win, already isolated |
| Superseded Layer 3 batches (if not moved with `archive/`) | 1,403 MB | Included in top-level `archive/` |

**Layer 2 `outputs/archive/` specifics:**

- 852 files, mostly `.csv` filtered rotvecs (~18.6 GB) and `.parquet` (~3.9 GB)
- **389 files still tracked in Git** — must plan `git rm --cached` or accept index bloat before/after move
- Distinct from active 12 session trees (Group A)
- Stage A and Stage B explicitly deferred this move

**Risk:** **Medium** — historical audit reruns; not needed for poster if active sessions intact.

---

## Group E — Manual review required

| Path | Size | Issue |
|------|------|-------|
| `671_test_data_des/` | **232 MB** | Stage A: **not** duplicate of Layer 1/Layer 2 exports; export type undocumented; **3 files tracked in Git** |
| `Layer2_Motive_Kinematics/outputs/` (Git legacy) | 54,939 MB total | 775 tracked files in index despite `*_Take_*/` gitignore — untrack strategy needed before Stage C |
| `Layer1_motive_qc/motive_qc/outputs/` | 68 MB | 234 tracked QC outputs; partial gitignore |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/_archive/` vs active exports | 300 MB vs ~906 MB | Confirm active exports supersede snapshot before moving `_archive/` |

**Risk:** **High** until export-type and Git-legacy questions resolved.

---

## Specific evaluations (requested paths)

### `Layer2_Motive_Kinematics/outputs/` — **54,939 MB**

| Component | Size | Recommendation |
|-----------|------|----------------|
| Active `*_Take_*` sessions (12) | ~31,346 MB | **Keep** (Group A) until poster |
| `outputs/archive/` | ~22,543 MB | **Move outside repo** (Group D / Stage C) |
| `layer2_exports/` | ~1,049 MB | **Keep on disk**, gitignored (Group B) |
| Stage index CSV/MD | small | Keep; consider separate code commit |

Largest files: `filtered_relative_rotation_vectors.csv` (~800–990 MB per session).

### `Layer3_JcvPCA/outputs/` — **3,623 MB**

| Component | Size | Recommendation |
|-----------|------|----------------|
| `gaga_batch_jcvpca_20260626_193319/` | 3,608 MB | **Keep active** (Group A) |
| `_workbench_*` (8 folders) | ~6 MB | **Archive/move** when convenient (Group C) |
| `poster_ready_evidence_package/` | ~1 MB | **Keep active** (Group A) |
| `671_g4_validation_001/` | small | Gitignored validation scratch |
| `movement_organization_question_report/` | untracked, small | Generated report; keep until poster review done |
| `nullspace_link_stability_review/` | untracked, small | Same |

Batch dominated by `.parquet` (2.1 GB), `.csv` (1.0 GB), `.npy` (334 MB), `.png` (105 MB).

### Root-level `outputs/` — **~13 MB**

| Component | Recommendation |
|-----------|----------------|
| `poster_final_figures/*.csv`, `*.md` | **Tracked** — keep (Group A) |
| `poster_final_figures/*.{pdf,png,svg}` | Gitignored binaries — optional relocate with poster assets |

Below 50 MB audit threshold but **scientifically important** for poster.

### `poster_ready_evidence_package/` — **~1 MB**

- **Role:** Poster evidence (Group A)
- **Git:** Untracked visible (not gitignored)
- **Recommendation:** **Keep until poster submission**; do not move
- Referenced as primary CSV source in `POSTER_REPRO_PATH_CHECK.md`

### `_workbench` folders — **~6 MB total**

| Folder | Approx |
|--------|--------|
| `_workbench_comparability` | small |
| `_workbench_dataset_preview` | small |
| `_workbench_full` | 1.6 MB |
| `_workbench_inventory_preview` | small |
| `_workbench_phase6/7/9` | ~1.2 MB each |
| `_workbench_preflight` | small |

All gitignored. **Recommendation:** Move to internal archive with superseded batches (Group C) — low priority due to small size.

### `_archive` folders

| Path | Size | Recommendation |
|------|------|----------------|
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/_archive/` | 300 MB | Move to internal/external archive after confirming active exports (Group C) |
| Nested `_archive` under moved scratch | in `archive/` | Move with top-level `archive/` (Group D) |

### Top-level `archive/` — **2,059 MB**

- Created Stage B (2026-06-30); gitignored
- Contains superseded Layer 3 batches (~1.4 GB) + Layer 2.5 scratch (~656 MB)
- **Recommendation:** **Move outside repo** (Stage B.10) — lowest-risk size reduction
- Documented in `docs/cleanup_stage_B/move_log.csv`

---

## Size reduction roadmap (conservative)

| Stage | Action | Approx. savings | Risk |
|-------|--------|-----------------|------|
| **B.10** | Move top-level `archive/` outside repo | ~2 GB | Low |
| **C** | Move `Layer2_Motive_Kinematics/outputs/archive/` outside repo | ~22 GB | Medium |
| **Post-poster** | Optional: regenerate vs keep batch `193319` | up to ~3.6 GB | Medium–high |
| **Post-poster** | Optional: prune Layer 2 intermediate stage CSVs per session | variable | High |
| **Git hygiene** | Untrack legacy output files in index | 0 disk; cleaner Git | Low |

**Do not delete** without external backup. All moves should update `move_log.csv` and `PROJECT_STATUS.md`.

---

## Folders below 50 MB (not in CSV but noted)

| Path | Size | Group |
|------|------|-------|
| `outputs/poster_final_figures/` | ~13 MB | A |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | ~1 MB | A |
| `Layer3_JcvPCA/docs/figures/` | ~0.8 MB | Keep (source schematic SVG) |
| `Layer3_JcvPCA/outputs/_workbench_*` | ~6 MB total | C |

---

## Recommended next step

### **Manual review first**

Before any physical move (B.10 or Stage C), resolve:

1. **`671_test_data_des/`** — document export type; decide track/untrack/move (Stage A open item).
2. **Layer 2 Git legacy** — 775 tracked files under `Layer2_Motive_Kinematics/outputs/`; plan explicit `git rm --cached` for session/archive paths before Stage C move.
3. **Layer 2.5 `_archive/` vs active exports** — confirm snapshot is superseded (likely yes per B.7 export refresh).

**Then**, in order:

1. **Stage B.10** — move top-level `archive/` (~2 GB) outside repo (low risk, already gitignored).
2. **Stage C** — move `Layer2_Motive_Kinematics/outputs/archive/` (~22 GB) after backup + Git untrack plan.

Stage D (clean active-results structure) is useful **after** physical slimming — e.g. symlink `active_results/` → canonical batch + evidence package — but does not reduce disk by itself.

---

## Related documents

| Document | Relevance |
|----------|-----------|
| [`STAGE_B9_OUTPUT_FOLDER_AUDIT.csv`](STAGE_B9_OUTPUT_FOLDER_AUDIT.csv) | Full ≥50 MB folder table |
| [`docs/cleanup_stage_A/STAGE_A_SUMMARY.md`](../cleanup_stage_A/STAGE_A_SUMMARY.md) | Layer 3 canonical batch, 671_test_data_des flag |
| [`POSTER_REPRO_PATH_CHECK.md`](POSTER_REPRO_PATH_CHECK.md) | Poster path dependencies |
| [`STAGE_B_MOVE_PLAN.md`](STAGE_B_MOVE_PLAN.md) | Prior move scope (Layer 2 archive deferred) |

---

*Documentation only. No files moved, deleted, staged, or committed in Stage B.9.*
