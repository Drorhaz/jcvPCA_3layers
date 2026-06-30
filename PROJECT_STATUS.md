# Project Status — 3Layers JcvPCA Pipeline

**Last updated:** 2026-06-30  
**Cleanup stage:** **B.6 complete** (`.gitignore` applied; commit plan prepared, not committed)  
**Next stage:** **Commit checkpoint** (manual, per `STAGE_B6_COMMIT_PLAN.md`) then **Stage C** — Layer 2 `outputs/archive/` (~22 GB)

---

## Current cleanup stage

| Stage | Status | Summary |
|-------|--------|---------|
| **A** | Complete | Audit, checksums, manifests — `docs/cleanup_stage_A/` |
| **B** | Complete | Moved ~2 GB superseded/scratch folders to `archive/2026-06-30_cleanup_stage_B/` |
| **B.5** | Complete | Git status, `.gitignore` review, poster path check |
| **B.6** | Complete | `.gitignore` applied; git status after ignore; commit plan prepared |
| **B.7** | Complete | Missing export CSV review; accept deletions; final commit plan prepared |
| **Commit** | Pending | Manual execution per `STAGE_B7_COMMIT_PLAN_FINAL.md` |
| **C** | Planned | Layer 2 archive physical move; optional batch slimming |

---

## Canonical Layer 3 batch

**Single source of truth:**

```
Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/
```

- 20/20 core comparisons completed  
- 72 comparison directories (includes directional-robustness grid)  
- 14 interpretive MD reports (integrated review, directional robustness, NV, joint heatmaps, poster planning)  
- Hard-coded in `scripts/make_poster_final_figures.py` and `scripts/make_poster_671_figures.py`

Superseded batches moved to:

```
archive/2026-06-30_cleanup_stage_B/layer3_superseded_batches/
```

---

## Poster reproduction chain

```text
Layer 2.5 pre_jvcpca_review/  (parquet matrices)
        ↓
gaga_batch_jcvpca_20260626_193319/  (canonical batch)
        ↓
poster_ready_evidence_package/  (curated CSV inputs)
        ↓
scripts/make_poster_final_figures.py
scripts/make_poster_671_figures.py
        ↓
outputs/poster_final_figures/  (final PDF/PNG/SVG + plot tables)
```

**Stage B.5 check:** All input paths exist; poster reproduction appears **safe** (see `docs/cleanup_stage_B/POSTER_REPRO_PATH_CHECK.md`).

---

## Do not touch (without explicit approval)

| Category | Paths |
|----------|-------|
| Raw data | `Layer1_motive_qc/motive_qc/data/`, `Layer2_Motive_Kinematics/data/`, `671_test_data_des/` |
| Video | `Layer2_Motive_Kinematics/data/252/**/*.avi` |
| Manual annotations | `Layer2.5_Segmentation/segmentation/*.xlsx` |
| Active exports | `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` |
| Canonical batch | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` |
| Poster inputs | `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` |
| Poster outputs | `outputs/poster_final_figures/` |
| Analysis code | All `src/`, `scripts/`, `tests/`, notebooks (no drive-by edits) |
| Layer 2 archive (deferred) | `Layer2_Motive_Kinematics/outputs/archive/` (~22 GB) |

---

## Archived so far (Stage B)

**Location:** `archive/2026-06-30_cleanup_stage_B/` (~2.0 GB)

| Group | Contents |
|-------|----------|
| `layer3_superseded_batches/` | 5 batch runs: `174553`, `175138`, `180044`, `193110`, `193235` |
| `layer2_5_scratch_archive/` | `reevluate_project/`, `outputs/archive/` (from Layer 2.5) |

Reversible via `docs/cleanup_stage_B/move_log.csv`.

---

## What remains risky

| Item | Size | Issue |
|------|------|-------|
| `Layer2_Motive_Kinematics/outputs/archive/` | ~22 GB | Older pipeline outputs; stage08 differs from active |
| `671_test_data_des/` CSV | 243 MB | Not duplicate of Layer 1/Layer 2 exports — export type unclear |
| Git tracked deletions | 12 paths | Stage B moves show as deletions; archive is untracked |
| `archive/` not in `.gitignore` | 2 GB | Risk of accidental staging |
| Off-repo backup | — | Not verified in Stages A–B.5 |

---

## Open questions

1. Is `671_test_data_des/` CSV a unique full raw export that must be kept separately from Layer 1/Layer 2 copies?
2. Should poster figure binaries be tracked in git or only regenerated from CSV sources?
3. When to commit Layer 2.5 / Layer 3 source changes relative to cleanup docs?
4. Is off-repo backup confirmed before Stage C moves Layer 2 archive?
5. Should segmentation `.xlsx` files be committed from new `segmentation/` path (old root path deleted in git)?

---

## Key documentation

| Document | Purpose |
|----------|---------|
| [docs/CLEANUP_INDEX.md](docs/CLEANUP_INDEX.md) | Master index of all cleanup artifacts |
| [docs/PROJECT_AUDIT_DRAFT.md](docs/PROJECT_AUDIT_DRAFT.md) | Initial project audit |
| [docs/cleanup_stage_B/STAGE_B_SUMMARY.md](docs/cleanup_stage_B/STAGE_B_SUMMARY.md) | Stage B move results |
| [docs/cleanup_stage_B/STAGE_B_GIT_STATUS.md](docs/cleanup_stage_B/STAGE_B_GIT_STATUS.md) | Git checkpoint |
| [README.md](README.md) | Pipeline overview (**note:** Layer 3 status still says "planned" — update when ready) |

---

## Participants and scope

- **671** — poster flagship participant; full T1/T2/T3 × R1/R2  
- **252** — batch cohort; same timepoint structure  
- **Movement focus:** Group 4 (curvilinear exploration); V1 JcvPCA scope per `Layer3_JcvPCA/docs/LAYER3_SCOPE.md`
