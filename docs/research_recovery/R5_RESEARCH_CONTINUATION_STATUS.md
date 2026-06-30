# R5 — Research Continuation Status

**Date:** 2026-06-30  
**Mode:** Research continuation (poster complete)  
**Stages completed:** R1–R5 (this document)

---

## What is now safe to use

| Asset | Path | Status |
|-------|------|--------|
| Canonical Layer 3 batch | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | **Intact** — primary analysis source |
| Poster evidence CSVs | `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | **Intact** |
| Poster figures + audit tables | `outputs/poster_final_figures/` | **Intact** |
| Layer 2.5 exports | `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | **Intact** — Layer 3 input |
| Active Layer 2 sessions | `Layer2_Motive_Kinematics/outputs/*_Take_*/` | **Intact** (~31 GB) |
| Layer 2 export bundle | `Layer2_Motive_Kinematics/outputs/layer2_exports/` | **Intact** |
| Raw data | `Layer1_.../data/`, `Layer2_.../data/` | **Untouched** |
| Path registry | `config/paths.yaml` | **New** — not yet wired to code |
| Working structure | `results/*` | **Empty placeholders** |

---

## What was moved outside the repo

| Item | External path | Size | Restore |
|------|---------------|------|---------|
| Top-level cleanup archive (B.10) | `../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/` | ~2 GB | See B.10 move log |
| Layer 2 historical archive (R1) | `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` | ~22 GB | See [`R1_LAYER2_ARCHIVE_EXTERNAL_MOVE.md`](R1_LAYER2_ARCHIVE_EXTERNAL_MOVE.md) |

**Total off-repo:** ~24 GB. Project repo is ~22 GB lighter than pre-R1 for Layer 2 archive alone.

---

## What remains messy

| Item | Issue | Mitigation |
|------|-------|------------|
| Git working tree | ~45 modified tracked files + ~60 untracked (L2.5/L3 code) | Separate "analysis code" commit when ready |
| Git legacy outputs | 775+ tracked files under Layer 2 outputs; 389 deleted archive paths in index | `git rm --cached` pass |
| Hard-coded batch ID | 22 scripts reference `193319` directly | R6 path loader + refactor |
| `671_test_data_des/` | 232 MB; export type undocumented | Manual review |
| Layer 2.5 `_archive/` snapshot | ~300 MB inside repo | Optional external move later |
| Dual output locations | Canonical results in Layer folders + empty `results/` | Symlink phase R6+ |
| Untracked Layer 3 scripts/src | Full L2.5/L3 automation not in Git | Commit 2 when reviewed |

---

## What should not be touched (without explicit plan)

| Category | Paths |
|----------|-------|
| Canonical batch | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` |
| Poster chain | evidence package + `outputs/poster_final_figures/` |
| Active L2.5 exports | `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` (671/252 g4 windows) |
| Active L2 sessions | `Layer2_Motive_Kinematics/outputs/*_Take_*/` |
| Raw data | all `**/data/**`, `671_test_data_des/` |
| External archives | `../gaga_psylo_external_archive/` (move, don't delete) |
| Segmentation xlsx | `Layer2.5_Segmentation/segmentation/*.xlsx` |

---

## Before running new participants

1. **Read** `config/paths.yaml` and confirm Layer 2/2.5 output roots.
2. **Run Layer 2** for new sessions → active `outputs/*_Take_*` (not external archive).
3. **Refresh** `Layer2.5_Segmentation/outputs/session_index.csv` via notebook/controller discovery.
4. **Export** new g4 windows under `pre_jvcpca_review/<participant>/`.
5. **Run batch** via `run_gaga_batch_jcvpca.py --layer25-root ... --output-dir ...` (new timestamped folder — do not overwrite `193319` unless intentional).
6. **Update** `config/paths.yaml` `canonical_batch_id` when promoting a new canonical run.
7. **Document** new batch in `results/archive_index/` when automation matures.

---

## Recommended next coding stage (R6+)

| Stage | Task | Outcome |
|-------|------|---------|
| **R6** | `project_paths.py` loader + unit test | Single source of path truth |
| **R7** | Refactor Layer 3 scripts to use loader | New batches without find-replace |
| **R8** | Symlinks in `results/active/` | Cleaner navigation |
| **R9** | `results/archive_index/external_archives.yaml` | Discoverable off-repo archives |
| **R10** | Git untrack legacy outputs | Clean `git status` |
| **R11** | Commit Layer 2.5/3 source + tests | Reproducible automation in remote |
| **R12** | CLI wrapper `run_research_batch.sh` | Scalable participant onboarding |

**Do not start heavy re-analysis** until path refactor (R6–R7) is in place for new batch IDs.

---

## Documentation index (research recovery)

| Document | Purpose |
|----------|---------|
| [`R1_LAYER2_ARCHIVE_EXTERNAL_MOVE.md`](R1_LAYER2_ARCHIVE_EXTERNAL_MOVE.md) | R1 move log |
| [`R2_TARGET_WORKING_STRUCTURE.md`](R2_TARGET_WORKING_STRUCTURE.md) | Folder design |
| [`R3_CANONICAL_PATHS.md`](R3_CANONICAL_PATHS.md) | Path roles |
| [`R4_HARDCODED_PATHS_REVIEW.md`](R4_HARDCODED_PATHS_REVIEW.md) | Config migration map |
| [`R5_RESEARCH_CONTINUATION_STATUS.md`](R5_RESEARCH_CONTINUATION_STATUS.md) | This file |
| [`../../config/paths.yaml`](../../config/paths.yaml) | Machine-readable paths |

Historical cleanup: `docs/cleanup_stage_A/` through `docs/cleanup_stage_C/`, `docs/cleanup_stage_B/`.

---

*Poster protection mode ended. Research continuation mode active as of 2026-06-30.*
