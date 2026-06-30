# Project Status — 3Layers JcvPCA Pipeline

**Last updated:** 2026-06-30  
**Mode:** **Research continuation** (poster complete)  
**Cleanup:** Stages A–B.10 + C.0 complete; checkpoint commits on `main`  
**Latest:** Stage R1 — Layer 2 archive moved external (~22 GB)

---

## Current cleanup stage

| Stage | Status | Summary |
|-------|--------|---------|
| **A** | Complete | Audit, checksums, manifests — `docs/cleanup_stage_A/` |
| **B** | Complete | Moved ~2 GB superseded/scratch folders to `archive/2026-06-30_cleanup_stage_B/` |
| **B.5** | Complete | Git status, `.gitignore` review, poster path check |
| **B.6** | Complete | `.gitignore` applied; git status after ignore; commit plan prepared |
| **B.7** | Complete | Missing export CSV review; accept deletions; final commit plan prepared |
| **B.8–B.10** | Complete | Checkpoint commits; external cleanup archive (B.10) |
| **C.0** | Complete | Layer 2 archive review/plan (no move in C.0) |
| **R1** | Complete | Layer 2 `outputs/archive/` moved external (~22 GB) |
| **R2–R5** | Complete | Working structure, `config/paths.yaml`, path reviews |
| **Commit 2** | Pending | Layer 2.5/3 code, indices, notebooks (explicit staging only) |
| **R6+** | Planned | Path loader, script refactor, `results/active` symlinks |

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

Superseded batches moved to (external):

```
../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/layer3_superseded_batches/
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
| Layer 2 archive (external) | `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` (~22 GB) |

---

## Archived outside repo

**Parent:** `../gaga_psylo_external_archive/`

| Folder | Size | Moved |
|--------|------|-------|
| `archive_2026-06-30_cleanup_stage_B/` | ~2 GB | Stage B.10 |
| `layer2_outputs_archive_2026-06-30/` | ~22 GB | Stage R1 |

**Former in-repo location (Stage B):** `archive/2026-06-30_cleanup_stage_B/` (~2.0 GB)

| Group | Contents |
|-------|----------|
| `layer3_superseded_batches/` | 5 batch runs: `174553`, `175138`, `180044`, `193110`, `193235` |
| `layer2_5_scratch_archive/` | `reevluate_project/`, `outputs/archive/` (from Layer 2.5) |

Reversible via `docs/cleanup_stage_B/move_log.csv`.

---

## What remains risky

| Item | Size | Issue |
|------|------|-------|
| Git legacy output tracking | 775+ files | Layer 2 outputs still in index; plan `git rm --cached` |
| Hard-coded batch paths | 22 scripts | Migrate to `config/paths.yaml` (R6+) |
| `671_test_data_des/` CSV | 243 MB | Not duplicate of Layer 1/Layer 2 exports — export type unclear |
| Git tracked deletions | 12 paths | Stage B moves show as deletions; archive is untracked |
| Off-repo backup | — | External archive parent exists; verify backup policy |

---

## Open questions

1. Is `671_test_data_des/` CSV a unique full raw export that must be kept separately from Layer 1/Layer 2 copies?
2. Should poster figure binaries be tracked in git or only regenerated from CSV sources?
3. When to commit Layer 2.5 / Layer 3 source changes relative to cleanup docs?
4. ~~Is off-repo backup confirmed before Stage C moves Layer 2 archive?~~ **Resolved:** R1 move complete; verify long-term backup policy for `../gaga_psylo_external_archive/`.
5. Should segmentation `.xlsx` files be committed from new `segmentation/` path (old root path deleted in git)?

---

## Research continuation mode

Poster submission complete. Project is transitioning from poster-protection to active research and automation scaling.

| Resource | Purpose |
|----------|---------|
| [`config/paths.yaml`](config/paths.yaml) | Canonical path registry (not yet wired to code) |
| [`docs/research_recovery/R5_RESEARCH_CONTINUATION_STATUS.md`](docs/research_recovery/R5_RESEARCH_CONTINUATION_STATUS.md) | Current status and next coding stages |
| [`docs/research_recovery/R1_LAYER2_ARCHIVE_EXTERNAL_MOVE.md`](docs/research_recovery/R1_LAYER2_ARCHIVE_EXTERNAL_MOVE.md) | Layer 2 archive move log |
| [`docs/research_recovery/R4_HARDCODED_PATHS_REVIEW.md`](docs/research_recovery/R4_HARDCODED_PATHS_REVIEW.md) | Config migration priorities |
| `results/active/`, `results/reports/`, … | Placeholder folders for future curated outputs |

**Safe to continue analysis** using canonical batch `193319`, Layer 2.5 exports, and active Layer 2 sessions. **Do not overwrite** `193319` when running new batches — use timestamped output dirs.

---

## Key documentation

| Document | Purpose |
|----------|---------|
| [docs/CLEANUP_INDEX.md](docs/CLEANUP_INDEX.md) | Master index of all cleanup artifacts |
| [docs/research_recovery/R5_RESEARCH_CONTINUATION_STATUS.md](docs/research_recovery/R5_RESEARCH_CONTINUATION_STATUS.md) | Research continuation status and next stages |
| [docs/research_recovery/R3_CANONICAL_PATHS.md](docs/research_recovery/R3_CANONICAL_PATHS.md) | Path registry documentation |
| [docs/PROJECT_AUDIT_DRAFT.md](docs/PROJECT_AUDIT_DRAFT.md) | Initial project audit |
| [docs/cleanup_stage_B/STAGE_B_SUMMARY.md](docs/cleanup_stage_B/STAGE_B_SUMMARY.md) | Stage B move results |
| [docs/cleanup_stage_B/STAGE_B_GIT_STATUS.md](docs/cleanup_stage_B/STAGE_B_GIT_STATUS.md) | Git checkpoint |
| [README.md](README.md) | Pipeline overview (**note:** Layer 3 status still says "planned" — update when ready) |

---

## Participants and scope

- **671** — poster flagship participant; full T1/T2/T3 × R1/R2  
- **252** — batch cohort; same timepoint structure  
- **Movement focus:** Group 4 (curvilinear exploration); V1 JcvPCA scope per `Layer3_JcvPCA/docs/LAYER3_SCOPE.md`
