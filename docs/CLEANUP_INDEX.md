# Cleanup Documentation Index

Master index for the 3Layers project directory cleanup (Stages A → B.5 → planned C).

**Project root:** `3Layers_project/`  
**Status checkpoint:** [PROJECT_STATUS.md](../PROJECT_STATUS.md)  
**Last updated:** 2026-06-30

---

## Stage A — Audit & verification (read-only)

| Document | Description |
|----------|-------------|
| [docs/PROJECT_AUDIT_DRAFT.md](PROJECT_AUDIT_DRAFT.md) | Initial ~85 GB project audit: structure, categories, risks |
| [docs/cleanup_stage_A/STAGE_A_SUMMARY.md](cleanup_stage_A/STAGE_A_SUMMARY.md) | Checksum findings, archive candidates, Stage B warnings |
| [docs/cleanup_stage_A/file_inventory.csv](cleanup_stage_A/file_inventory.csv) | 39,695 files (excludes `.venv`/cache) |
| [docs/cleanup_stage_A/checksum_comparison.csv](cleanup_stage_A/checksum_comparison.csv) | 76 targeted duplicate/archive checksums |
| [docs/cleanup_stage_A/layer3_batch_comparison.md](cleanup_stage_A/layer3_batch_comparison.md) | All 6 batch runs; `193319` canonical |
| [docs/cleanup_stage_A/poster_outputs_review.md](cleanup_stage_A/poster_outputs_review.md) | Poster chain and preserve list |
| [docs/cleanup_stage_A/proposed_archive_manifest.csv](cleanup_stage_A/proposed_archive_manifest.csv) | Pre-move archive recommendations |
| [docs/cleanup_stage_A/proposed_active_manifest.csv](cleanup_stage_A/proposed_active_manifest.csv) | Active project core |

---

## Stage B — Controlled archiving (moves only, no deletions)

| Document | Description |
|----------|-------------|
| [docs/cleanup_stage_B/STAGE_B_MOVE_PLAN.md](cleanup_stage_B/STAGE_B_MOVE_PLAN.md) | Pre-move plan (7 folders, ~2 GB) |
| [docs/cleanup_stage_B/move_log.csv](cleanup_stage_B/move_log.csv) | Per-move log; reversible |
| [docs/cleanup_stage_B/STAGE_B_SUMMARY.md](cleanup_stage_B/STAGE_B_SUMMARY.md) | Results, verification, Stage C preview |

**Archive on disk:**

```
archive/2026-06-30_cleanup_stage_B/
├── layer3_superseded_batches/     # 5 superseded Layer 3 batches
└── layer2_5_scratch_archive/      # reevluate_project + outputs/archive
```

---

## Stage B.5 — Git & stability checkpoint

| Document | Description |
|----------|-------------|
| [docs/cleanup_stage_B/STAGE_B_GIT_STATUS.md](cleanup_stage_B/STAGE_B_GIT_STATUS.md) | Branch, modified/untracked counts, commit guidance |
| [docs/cleanup_stage_B/GITIGNORE_REVIEW.md](cleanup_stage_B/GITIGNORE_REVIEW.md) | Recommended `.gitignore` rules (pre-B.6) |
| [docs/cleanup_stage_B/POSTER_REPRO_PATH_CHECK.md](cleanup_stage_B/POSTER_REPRO_PATH_CHECK.md) | Poster script path existence check |
| [PROJECT_STATUS.md](../PROJECT_STATUS.md) | Project-wide status checkpoint |

---

## Stage B.6 — `.gitignore` applied & commit plan

| Document | Description |
|----------|-------------|
| [docs/cleanup_stage_B/STAGE_B6_GITIGNORE_APPLIED.md](cleanup_stage_B/STAGE_B6_GITIGNORE_APPLIED.md) | Exact rules added and deferred |
| [docs/cleanup_stage_B/STAGE_B6_GIT_STATUS_AFTER_IGNORE.md](cleanup_stage_B/STAGE_B6_GIT_STATUS_AFTER_IGNORE.md) | Git status after `.gitignore` update |
| [docs/cleanup_stage_B/STAGE_B6_DELETED_TRACKED_REVIEW.md](cleanup_stage_B/STAGE_B6_DELETED_TRACKED_REVIEW.md) | Per-path decisions for 12 deleted tracked files |
| [docs/cleanup_stage_B/STAGE_B6_COMMIT_PLAN.md](cleanup_stage_B/STAGE_B6_COMMIT_PLAN.md) | Explicit `git add` commands (superseded by B.7 final plan) |

---

## Stage B.7 — Missing export CSV review & final commit plan

| Document | Description |
|----------|-------------|
| [docs/cleanup_stage_B/STAGE_B7_MISSING_EXPORT_CSV_REVIEW.md](cleanup_stage_B/STAGE_B7_MISSING_EXPORT_CSV_REVIEW.md) | `mapping_logic_table.csv` and `joint_overlap_table.csv` investigation |
| [docs/cleanup_stage_B/STAGE_B7_COMMIT_PLAN_FINAL.md](cleanup_stage_B/STAGE_B7_COMMIT_PLAN_FINAL.md) | Final checkpoint commit staging commands |

---

## Recommended Stage C (not started)

1. **Layer 2 archive** — Review and optionally move `Layer2_Motive_Kinematics/outputs/archive/` (~22 GB) after poster submission or session-level hash review.
2. **Apply `.gitignore`** — Add `archive/`, Layer 3 batch output folders, poster binaries (see GITIGNORE_REVIEW.md).
3. **Git commit strategy** — Commit cleanup docs + resolve Stage B tracked deletions vs untracked archive.
4. **Optional slimming** — Strip batch comparison `.npy`/diagnostic `.png` if regeneration proven.
5. **Documentation** — Update root `README.md` Layer 3 status; resolve `671_test_data_des/` export-type question.

---

## Quick reference — canonical paths

| Role | Path |
|------|------|
| Canonical batch | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` |
| Poster CSV inputs | `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` |
| Poster scripts | `scripts/make_poster_final_figures.py`, `scripts/make_poster_671_figures.py` |
| Poster figures | `outputs/poster_final_figures/` |
| Layer 2.5 exports | `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` |
| Deferred (do not move yet) | `Layer2_Motive_Kinematics/outputs/archive/` |

---

## Rules observed across all stages

- No deletions  
- No raw data moves (Stages B–B.5)  
- No analysis code edits (Stages A–B.5)  
- Canonical batch `193319` and poster chain preserved  
