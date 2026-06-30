# Stage B.5 — Git Status Report

**Date:** 2026-06-30  
**Branch inspected:** `main`  
**Purpose:** Checkpoint before Stage C; no commits made in this stage.

---

## Repository snapshot

| Metric | Count |
|--------|-------|
| Tracked files (index) | **1,367** |
| Working-tree changes (`git status --short`) | **199 lines** |
| — Modified tracked (`M`) | **45** |
| — Deleted tracked (`D`) | **12** |
| — Untracked not ignored (`??`) | **142** (status lines; many are directories) |
| Untracked files not ignored (`git ls-files -o --exclude-standard`) | **~33,084** |
| Ignored untracked files | **~98,455** |

---

## Current branch

```
main
```

No branch switch was performed during cleanup Stages A–B.

---

## Modified tracked files (45)

These are **real code/doc changes** pending commit, not Stage B archive moves:

| Area | Examples |
|------|----------|
| Layer 2.5 source | `app_controller.py`, `export_window.py`, `joint_overlap.py`, … |
| Layer 2.5 dashboard | `dashboard_state.py`, `pre_jvcpca_dashboard.py`, pages |
| Layer 2.5 notebooks | `post_layer2_segmentation_review.ipynb`, `pre_jvcpca_review.ipynb` |
| Layer 2.5 tests | 5 test files |
| Layer 2.5 outputs (small tracked JSON/MD) | `pre_jvcpca_review/671/.../window_export_manifest.json`, etc. |
| Layer 2 indices | `Layer2_Motive_Kinematics/outputs/stage*_index.{csv,md}` (16 files) |
| Layer 3 | `README.md`, `references/JcvPCA and JsvCRP.pdf`, `src/layer3_jcvpca/viz.py` |

---

## Deleted tracked files (12) — Stage B side effect

Stage B **moved** folders off their original paths. Git now shows deletions for paths that were previously tracked:

### Moved to `archive/.../layer2_5_scratch_archive/reevluate_project/` (9 files)

- `Layer2.5_Segmentation/reevluate_project/artifact_events.csv`
- `Layer2.5_Segmentation/reevluate_project/gaps_over_0p2s.csv`
- `Layer2.5_Segmentation/reevluate_project/gaps_over_0p5s.csv`
- `Layer2.5_Segmentation/reevluate_project/layer1_segmentation_notebook_manifest.json`
- `Layer2.5_Segmentation/reevluate_project/layer2_qc_link_manifest.csv`
- `Layer2.5_Segmentation/reevluate_project/layer2_qc_session_manifest.json`
- `Layer2.5_Segmentation/reevluate_project/qc_mask.csv`
- `Layer2.5_Segmentation/reevluate_project/qc_mask_intervals.csv`
- `Layer2.5_Segmentation/reevluate_project/revised_pre_jvcpca_review_tables.md`

**Important:** Files still exist on disk under `archive/2026-06-30_cleanup_stage_B/layer2_5_scratch_archive/reevluate_project/`, but that archive tree is **untracked**. Committing deletions alone would remove these paths from the repository index without recording the new archive location.

### Other deletions (3)

| Path | Notes |
|------|-------|
| `Layer2.5_Segmentation/671_ex_segmentatios_frames.xlsx` | Old location; files now exist as untracked `Layer2.5_Segmentation/segmentation/671_ex_segmentatios_frames.xlsx` |
| `.../mapping_logic_table.csv` | Under pre_jvcpca_review export |
| `.../joint_overlap_table.csv` | Under pre_jvcpca_review/671/ |

---

## Large untracked folders (not ignored)

| Path | Approx. size | Notes |
|------|--------------|-------|
| `Layer3_JcvPCA/outputs/` | **~3.6 GB** | Canonical batch `193319`, evidence package, workbench previews |
| `archive/2026-06-30_cleanup_stage_B/` | **~2.0 GB** | Stage B moves (superseded batches + Layer 2.5 scratch) |
| `Layer2_Motive_Kinematics/outputs/` | large | Active 671/252 session outputs + **22 GB archive** (deferred) |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | **~1.2 GB** | Active JcvPCA-ready exports |
| `outputs/poster_final_figures/` | **~13 MB** | Final poster deliverables |
| `docs/cleanup_stage_A/` | **~8 MB** | Stage A inventory CSV |
| `scripts/make_poster_*.py` | small | Poster generators (untracked) |

Top untracked file-count prefixes (`git ls-files -o --exclude-standard`):

1. `Layer3_JcvPCA/outputs` — ~24,377 files  
2. `archive/2026-06-30_cleanup_stage_B` — ~7,379 files  
3. `Layer2.5_Segmentation/outputs` — ~513 files  
4. `Layer2_Motive_Kinematics/outputs` — ~410 files  

---

## Is `archive/` tracked?

| Question | Answer |
|----------|--------|
| Any files under `archive/` in git index? | **No** (`git ls-files archive/` is empty) |
| Ignored by `.gitignore`? | **No** — no rule matches `archive/` today |
| Status | **Untracked-not-ignored** (~2 GB, ~7,400 files) |

Stage B archive content is on disk but **outside git history** unless explicitly added or ignored.

---

## Are generated outputs ignored by `.gitignore`?

**Partially.** Current rules cover:

| Category | Ignored? | Rule |
|----------|----------|------|
| `.venv/`, `__pycache__/`, `.pytest_cache/` | Yes | Standard Python |
| `*.parquet`, `*.npy`, `*.npz` | Yes | Global |
| Raw Motive CSVs in `data/` | Yes | Path-specific |
| Large Layer 2 frame CSVs (stages 05–08) | Yes | Path-specific |
| `**/*.avi`, video formats | Yes | Global |
| `**/outputs/archive/` | Yes | **Only** paths named `outputs/archive/` |
| Layer 3 batch folders (`gaga_batch_*`) | **No** | Only `.npy`/`.parquet` inside ignored |
| Root `archive/2026-06-30_cleanup_stage_B/` | **No** | Not covered |
| `poster_final_figures/`, PNG/PDF outputs | **No** | Not covered |
| `poster_ready_evidence_package/` CSVs | **No** | Small CSVs not matched |
| `reevluate_project/` (old path) | Rule exists but folder **moved** | Stale path in `.gitignore` line 62 |

Most heavy generated data is ignored via `*.npy` / `*.parquet` / large CSV patterns, but **many summary CSVs, MD reports, PNG plots, and the new `archive/` tree are not ignored**.

---

## Recommended files to commit now

**Safe documentation checkpoint (recommended):**

- `PROJECT_STATUS.md`
- `docs/PROJECT_AUDIT_DRAFT.md`
- `docs/CLEANUP_INDEX.md`
- `docs/cleanup_stage_A/*` (audit + manifests)
- `docs/cleanup_stage_B/*` (move plan, log, summaries, this file, gitignore review, poster check)

**Recommended source/doc commits (if ready for review):**

- `scripts/make_poster_final_figures.py`, `scripts/make_poster_671_figures.py`
- Layer 2.5 / Layer 3 source, test, and dashboard changes (the 45 modified tracked files)
- Layer 2 stage index updates (if intentional)
- `Layer3_JcvPCA/README.md`, scope/docs additions

**Segmentation annotations (scientifically important, currently untracked):**

- `Layer2.5_Segmentation/segmentation/671_ex_segmentatios_frames.xlsx`
- `Layer2.5_Segmentation/segmentation/252_ex_segmentatios_frames.xlsx`

**Resolve before commit:**

- Stage B deletion entries for `reevluate_project/` — either document archive location in commit message and accept index removal, or add `archive/` policy first
- `671_ex_segmentatios_frames.xlsx` path change (deleted at old path, present under `segmentation/`)

---

## Recommended files to keep untracked (or ignore in Stage C)

| Category | Examples | Reason |
|----------|----------|--------|
| Raw data | `Layer1/.../data/`, `Layer2/.../data/`, `671_test_data_des/*_Take*.csv` | Already gitignored; never commit |
| Large intermediates | `**/08_filtered_rotvecs/*.csv`, `*.npy`, `*.parquet` | Regeneratable; gitignored |
| Layer 3 batch outputs | `gaga_batch_jcvpca_20260626_193319/` bulk | ~3.6 GB; keep local, ignore via future rule |
| Stage B archive | `archive/2026-06-30_cleanup_stage_B/` | Local archive; ignore or store off-repo |
| Poster figure binaries | `outputs/poster_final_figures/*.{pdf,png,svg}` | Regeneratable; optional small CSV/MD tracking |
| Virtual environments | `.venv/` | Already ignored |
| Layer 2 `outputs/archive/` (22 GB) | Deferred Stage C | Do not commit |

---

## Git hygiene warnings before any commit

1. **Do not commit raw data or 22 GB Layer 2 archive** even if accidentally staged.
2. **Stage B created 9 tracked deletions** — files live in untracked `archive/`; coordinate commit message with `move_log.csv`.
3. **`archive/` is not gitignored** — `git add .` could stage ~2 GB; use path-specific adds.
4. **33k+ untracked files** — prefer explicit staging, not blanket `git add -A`.

---

*Inspection only. No commits, no `.gitignore` edits in Stage B.5.*
