# Project Audit Draft — 3Layers JcvPCA Research Pipeline

**Audit date:** 2026-06-30  
**Auditor role:** Read-only inspection (no files moved, renamed, deleted, or modified except this report)  
**Project path:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project`

---

## Executive summary

This repository is a **multi-layer motion-capture analysis pipeline** for Gaga movement data from a psilocybin study. It spans raw Motive marker QC (Layer 1) through kinematic feature extraction (Layer 2), segmentation and JcvPCA-ready matrix export (Layer 2.5), and JcvPCA batch analysis with poster figure generation (Layer 3).

**Total on-disk size:** ~**85 GB** across ~**40,000 files** (excluding `.venv` internals).

The directory is **functionally rich but structurally messy** after exploratory analysis. The main issues are:

1. **Massive duplicated intermediates** — especially Layer 2 session outputs (54 GB) and an archive folder (22 GB) that mirrors active runs.
2. **Multiple copies of the same raw/session data** across Layer 1, Layer 2, Layer 2.5, and a root test folder.
3. **Six timestamped Layer 3 batch runs** on 2026-06-26 (~5 GB combined); only one appears to be the canonical full run.
4. **Root README is stale** — still lists Layer 3 as "planned" though it is implemented with extensive outputs.
5. **Git tracks ~1,367 files** but **~33,000 files are untracked**, mostly generated outputs and local data.

**Participants in active analysis:** **671** (poster/example focus) and **252** (batch cohort).  
**Timepoints:** T1, T2, T3. **Repetitions:** R1, R2. **Movement group focus:** Group 4 (curvilinear exploration).

---

## 1. Current directory overview

### 1.1 Top-level layout

| Path | Size | Role |
|------|------|------|
| `Layer2_Motive_Kinematics/` | **76 GB** | Layer 2 — quaternion → filtered rotation vectors |
| `Layer3_JcvPCA/` | **5.5 GB** | Layer 3 — JcvPCA analysis, batch runs, poster evidence |
| `Layer2.5_Segmentation/` | **2.6 GB** | Segmentation review, pre-JcvPCA matrix export |
| `Layer1_motive_qc/` | **1.5 GB** | Layer 1 — raw marker QC |
| `671_test_data_des/` | **232 MB** | Sample raw CSV + data-description sidecar |
| `outputs/` | **13 MB** | Root-level poster final figures |
| `scripts/` | **192 KB** | Root poster figure generation scripts |
| `3_layers_Matser_plan_Full/` | **116 KB** | Master plan, pseudocode (canonical at root) |
| Root audit reports | ~**150 KB** | `LAYER1_RAW_MARKER_QC_AUDIT_REPORT.md`, `LAYER2_5_PROGRAM_AUDIT_REPORT.md`, etc. |
| `.cursor/`, `.pytest_cache/`, `.git/` | small–medium | IDE plans, test cache, version control |

**Note:** Four separate `.venv` directories add ~**2.3 GB** (Layer 1: 296 MB, Layer 2: 733 MB, Layer 2.5: 701 MB, Layer 3: 546 MB). These are already gitignored.

### 1.2 Pipeline architecture (intended data flow)

```text
Raw Motive marker CSV
  → Layer 1 QC (gaps, artifacts, qc_mask)
  → Motive mixed CSV (global bone quaternions)
  → Layer 2 stages 00–08 (filtered relative rotation vectors)
  → Layer 2.5 segmentation + window export (parquet matrices)
  → Layer 3 JcvPCA batch comparisons (A vs B, NV baseline)
  → Poster figures + numeric reports
```

### 1.3 Git state snapshot

| Metric | Count |
|--------|-------|
| Tracked files | 1,367 |
| Untracked files (excluding `.gitignore` rules) | ~33,062 |
| Modified tracked files (uncommitted) | ~45+ (Layer 2.5, Layer 2 indices, Layer 3 README/PDF) |
| Deleted tracked files (not yet committed) | 3 (`671_ex_segmentatios_frames.xlsx` at old path, `mapping_logic_table.csv`, `joint_overlap_table.csv`) |

The repository is a **monorepo** absorbing formerly nested subprojects. Most heavy outputs and raw data are intentionally untracked via `.gitignore`.

---

## 2. File and folder categories

### 2.1 Category inventory (estimated)

| Category | Approx. count | Primary locations | Notes |
|----------|---------------|-------------------|-------|
| **Python source (`.py`)** | ~27,000* | `*/src/`, `*/scripts/` | *Most `.py` hits are inside `.venv`; project source is ~200 files |
| **CSV** | ~20,000 | All layers | Mix of raw (100MB+), summaries (<1 MB), and reports |
| **JSON** | ~10,700 | Layer 2.5 exports, Layer 3 manifests, QC reports | Manifests, validation reports |
| **PNG** | ~3,800 | Layer 1 QC plots, Layer 3 batch comparisons | Diagnostic/plot outputs |
| **NPY** | ~3,200 | Layer 3 batch `comparisons/` | PCA arrays; gitignored |
| **Parquet** | ~1,300 | Layer 2.5 `pre_jvcpca_review/`, Layer 3 | JcvPCA-ready matrices; gitignored |
| **Markdown (`.md`)** | ~870 | Docs, reports, audit outputs | Scientific narrative + implementation notes |
| **SVG** | ~95 | Poster figures, workflow schematic | Publication-ready vector graphics |
| **PDF** | ~55 | Poster figures, reference papers | |
| **Notebooks (`.ipynb`)** | **4** | Layer 1 (2), Layer 2.5 (2) | Interactive QC and segmentation review |
| **Video (`.avi`)** | **13** | `Layer2_Motive_Kinematics/data/252/` | Camera exports; 1.2–1.7 GB each; gitignored |
| **Excel (`.xlsx`)** | **2** | `Layer2.5_Segmentation/segmentation/` | Manual segmentation frame annotations |
| **Zip** | **1** | `Layer2_Motive_Kinematics/Archive.zip` (380 KB) | Small archive artifact |
| **Unknown / misc** | few | `.DS_Store` (51 files), `.gitkeep`, HTML plans | Low scientific value |

### 2.2 Per-layer breakdown

#### Layer 1 — `Layer1_motive_qc/motive_qc/` (~1.5 GB)

| Subfolder | Size | Category |
|-----------|------|----------|
| `data/` | ~550 MB | **Raw Motive marker CSVs** (671 + 252 sessions; also flat copies at data root) |
| `outputs/runs/` | ~65 MB | **Generated QC reports** (HTML, plots, summary CSVs) |
| `outputs/batch_runs/` | ~2.6 MB | **Generated batch QC** (untracked, new) |
| `src/`, `scripts/`, `tests/`, `docs/`, `notebooks/` | small | **Active analysis code** |
| `.venv/` | 296 MB | Local environment (ignore) |

#### Layer 2 — `Layer2_Motive_Kinematics/` (~76 GB)

| Subfolder | Size | Category |
|-----------|------|----------|
| `outputs/` (active sessions) | ~32 GB | **Processed/interim + generated** — per-session stage folders 00–08 |
| `outputs/archive/` | **22 GB** | **Likely redundant** — archived copies of 671 session outputs + audit reruns |
| `data/252/` | **20 GB** | **Raw + video** — Motive CSVs + 13 AVI camera files (~1.2–1.7 GB each) |
| `data/671/` | 1.3 GB | **Raw Motive mixed CSVs** (6 sessions: T1–T3 × R1/R2) |
| `outputs/layer2_exports/` | 1.0 GB | **Interim exports** for downstream use |
| `src/`, `scripts/`, `tests/`, `docs/`, `configs/` | ~2 MB | **Active analysis code + specs** |

Each active session output (~2.3–2.8 GB) contains stage subfolders; the largest files are:
- `08_filtered_rotvecs/filtered_relative_rotation_vectors.csv` (~700–990 MB)
- `07_rotation_vectors/relative_rotation_vectors.csv` (~500–530 MB)

#### Layer 2.5 — `Layer2.5_Segmentation/` (~2.6 GB)

| Subfolder | Size | Category |
|-----------|------|----------|
| `outputs/pre_jvcpca_review/` | **1.2 GB** | **Processed JcvPCA-ready exports** (parquet, manifests, validation JSON) |
| `outputs/archive/` | 338 MB | Older/superseded exports |
| `reevluate_project/` | 318 MB | **Exploratory scratch** — duplicate parquet + single raw CSV + QC tables |
| `input/Layer2_Kinematics/` | 134 MB | **Symlink-like staging copies** of Layer 2 outputs for review |
| `input/Layer1_QC/` | 1.6 MB | Layer 1 QC summaries for review |
| `segmentation/` | small | **Scientifically important** — `671_ex_segmentatios_frames.xlsx`, `252_ex_segmentatios_frames.xlsx` |
| `src/`, `dashboard/`, `notebooks/`, `scripts/`, `tests/` | ~3 MB | **Active analysis code** |
| `data_description/` | 36 KB | Session metadata sidecars |

Participants **671** and **252** each have full T1/T2/T3 × R1/R2 window exports under `outputs/pre_jvcpca_review/{671,252}/`.

#### Layer 3 — `Layer3_JcvPCA/` (~5.5 GB)

| Subfolder | Size | Category |
|-----------|------|----------|
| `outputs/gaga_batch_jcvpca_20260626_193319/` | **3.6 GB** | **Primary batch run** — 20 comparisons, full numeric reports |
| `outputs/gaga_batch_jcvpca_20260626_193110/` | 780 MB | Earlier/superseded batch attempt |
| `outputs/gaga_batch_jcvpca_20260626_193235/` | 371 MB | Earlier/superseded batch attempt |
| `outputs/gaga_batch_jcvpca_20260626_{174553,175138,180044}/` | ~91 MB each | Early/smoke batch runs |
| `outputs/_workbench_*` | ~10 MB total | **Exploratory workbench previews** (preflight, phase6–9, inventory) |
| `outputs/671_g4_validation_001/` | 1.7 MB | **First real validation run** (documented in README) |
| `outputs/poster_ready_evidence_package/` | 908 KB | **Poster-curated evidence tables/reports** |
| `outputs/nullspace_link_stability_review/` | 872 KB | Exploratory review output |
| `outputs/movement_organization_question_report/` | 20 KB | Exploratory report |
| `src/` (31 modules), `scripts/` (23 scripts), `tests/`, `config/`, `docs/` | ~3 MB | **Active analysis code** |
| `references/` | 9.4 MB | Paper reference data + PDFs |
| `3_layers_Matser_plan_Full/` | 96 KB | **Duplicate** of partial root master plan |

Primary batch run contents (`193319`):
- ~2,400 `.npy`, ~800 `.parquet`, ~2,600 `.png` files
- Root-level CSV/MD reports (directional robustness, joint heatmaps, PC focus, integrated review)
- `comparisons/` subfolders named by participant + comparison type (e.g. `671_A_L2_T1_vs_T3`, `671_A_I_T1_R1_vs_R2`)

#### Root-level additions (outside layer folders)

| Path | Category |
|------|----------|
| `671_test_data_des/` | **Raw data sample** — 232 MB raw CSV + DataDescriptions sidecar (README says CSV gitignored) |
| `outputs/poster_final_figures/` | **Poster figures** — 48 files, 13 MB (PDF/PNG/SVG + plot tables + captions) |
| `scripts/make_poster_671_figures.py`, `make_poster_final_figures.py` | **Active poster scripts** |
| `3_layers_Matser_plan_Full/` | **Planning docs** — master plan, layer pseudocode |
| `LAYER*_*.md` audit reports | **Documentation** — prior programmatic audits |

---

## 3. Large and heavy items

### 3.1 Largest folders (priority for cleanup planning)

| Rank | Path | Size | Assessment |
|------|------|------|------------|
| 1 | `Layer2_Motive_Kinematics/outputs/` | **54 GB** | Regeneratable intermediates; archive subfolder alone is 22 GB |
| 2 | `Layer2_Motive_Kinematics/data/252/` | **20 GB** | Raw CSVs + 13 AVI videos |
| 3 | `Layer3_JcvPCA/outputs/` | **5.0 GB** | Multiple redundant batch runs |
| 4 | `Layer2.5_Segmentation/outputs/` | **1.5 GB** | JcvPCA-ready exports (scientifically valuable) |
| 5 | `Layer1_motive_qc/motive_qc/data/` | **~550 MB** | Raw marker CSVs |
| 6 | All `.venv/` directories | **~2.3 GB** | Safe to delete and recreate |
| 7 | `671_test_data_des/` | **232 MB** | Duplicate of one 671 raw session |

### 3.2 Largest individual files (>500 MB)

| Size | File pattern | Location |
|------|--------------|----------|
| 1.7 GB | `*_Take*-Camera 6*.avi` | `Layer2_Motive_Kinematics/data/252/T{1,2,3}/` (13 files) |
| 987–974 MB | `filtered_relative_rotation_vectors.csv` | Layer 2 session `08_filtered_rotvecs/` |
| 536–528 MB | `relative_rotation_vectors.csv` | Layer 2 session `07_rotation_vectors/` |
| 243 MB | `671_T1_P1_R1_Take*.csv` | `671_test_data_des/` (duplicate raw export) |

### 3.3 Extension-weighted storage drivers

| Extension | Count | Typical role | Git status |
|-----------|-------|--------------|--------------|
| `.csv` | ~20,046 | Raw + interim + summary | Large frame-level CSVs gitignored |
| `.npy` | ~3,156 | Layer 3 PCA arrays | Gitignored |
| `.parquet` | ~1,342 | Layer 2.5/3 matrices | Gitignored |
| `.png` | ~3,784 | Plots across all layers | Mixed |
| `.avi` | 13 | Camera video (252 only) | Gitignored |

---

## 4. Possible raw data locations

**Treat all paths below as scientifically protected — do not delete without explicit confirmation and off-repo backup.**

### 4.1 Primary raw Motive marker CSVs (Layer 1)

- `Layer1_motive_qc/motive_qc/data/671/` (~289 MB)
- `Layer1_motive_qc/motive_qc/data/252/` (~259 MB)
- Flat copies also at `Layer1_motive_qc/motive_qc/data/*_Take*.csv` (duplicate naming layout)
- `Layer1_motive_qc/motive_qc/data/archive/` (~45 MB)

### 4.2 Raw / mixed Motive kinematic CSVs (Layer 2 input)

- `Layer2_Motive_Kinematics/data/671/` — 6 session files (T1–T3 × R1/R2)
- `Layer2_Motive_Kinematics/data/252/T{1,2,3}/` — multiple sessions including P1/P2 variants

### 4.3 Video (auxiliary raw capture)

- `Layer2_Motive_Kinematics/data/252/**/*.avi` — 13 camera files, **~20 GB total**

### 4.4 Root sample / sidecar

- `671_test_data_des/671_T1_P1_R1_Take*.csv` (243 MB) — full raw export
- `671_test_data_des/*_DataDescriptions.csv` — metadata sidecar (small, tracked)

### 4.5 Duplicated raw copies (same session, multiple locations)

| Session example | Locations |
|-----------------|-----------|
| `671_T1_P1_R1` | `671_test_data_des/`, `Layer1/data/`, `Layer2/data/671/`, `Layer2.5/reevluate_project/` (48 MB subset) |
| All 671/252 T×R | Layer 1 `data/` and Layer 2 `data/` both hold full raw CSV sets |

**Uncertainty:** It is unclear whether Layer 1 raw CSVs and Layer 2 mixed CSVs are identical exports or different Motive export modes (markers-only vs. solved skeleton). Both are large and should be preserved until verified.

---

## 5. Possible active analysis scripts

### 5.1 Layer 1

| Script / entry | Path |
|----------------|------|
| Main QC pipeline | `Layer1_motive_qc/motive_qc/motive_raw_qc.py` |
| Batch utilities | `Layer1_motive_qc/motive_qc/scripts/split_motive_qc.py`, `build_modules.py` |
| Notebooks | `notebooks/01_raw_csv_qc_layers_1_2.ipynb`, `02_raw_csv_qc_layers_3_5.ipynb` |

### 5.2 Layer 2

| Script / entry | Path |
|----------------|------|
| CLI pipeline | `layer2-motive run-until` (via `pyproject.toml` entry point) |
| Shell wrapper | `Layer2_Motive_Kinematics/scripts/run_layer2_pipeline.sh` |
| Export / diagnostics | `export_layer2_sessions.py`, `generate_pre_stage07_gate.py`, `stage05_sign_flip_diagnostic.py` |

### 5.3 Layer 2.5

| Script / entry | Path |
|----------------|------|
| Export builder | `Layer2.5_Segmentation/scripts/build_gaga_exports.py` |
| Validation | `validate_segmentation_inputs.py`, `validate_pilot_export.py` |
| Dashboard | `dashboard/pre_jvcpca_dashboard.py`, pages `1_Layer3_JcvPCA_Analysis.py`, `2_Layer3_Gaga_Workbench.py` |
| Notebooks | `post_layer2_segmentation_review.ipynb`, `pre_jvcpca_review.ipynb` |

### 5.4 Layer 3 (core + poster pipeline)

| Script | Purpose |
|--------|---------|
| `scripts/run_gaga_batch_jcvpca.py` | **Primary batch runner** |
| `scripts/run_layer3_jcvpca.py` | Single-manifest CLI runner |
| `scripts/generate_final_integrated_review.py` | Integrated deep review report |
| `scripts/generate_poster_ready_evidence_package.py` | Poster evidence curation |
| `scripts/generate_*_full_numeric_report.py` | Numeric audit reports (master, NV, directional robustness, nullspace) |
| `scripts/analyze_directional_robustness_t*.py` | T1/T2/T3 directional analyses |
| `scripts/analyze_natural_variability_deep_dive.py` | NV (R1 vs R2) analysis |
| `scripts/analyze_timepoint_link_contribution.py` | Link contribution patterns |
| `scripts/prepare_joint_heatmap_tables.py` | Joint heatmap data prep |
| `scripts/run_pc_focus_p50_p60_sensitivity.py` | PC focus sensitivity |

**Sacred core (do not refactor casually):** `Layer3_JcvPCA/src/layer3_jcvpca/core.py` → `compute_jcvpca()`

### 5.5 Root poster scripts

| Script | Path |
|--------|------|
| Participant 671 figures | `scripts/make_poster_671_figures.py` |
| Final 4-panel poster | `scripts/make_poster_final_figures.py` |

---

## 6. Possible redundant / generated outputs

### 6.1 High-confidence redundant (candidates for archival, not deletion yet)

| Item | Size | Rationale |
|------|------|-----------|
| `Layer2_Motive_Kinematics/outputs/archive/` | **22 GB** | Mirrors active 671 session outputs + audit reruns; `.gitignore` already mentions `**/outputs/archive/` |
| Layer 3 batch runs except `193319` | **~1.3 GB** | Five earlier runs on same day; `193319` has 20 completed comparisons + full reports |
| `Layer3_JcvPCA/outputs/_workbench_*` | ~10 MB | Exploratory preflight/phase previews |
| `Layer2.5_Segmentation/outputs/_diag/` | small | Explicitly gitignored as diagnostic scratch |
| `Layer2.5_Segmentation/reevluate_project/` | 318 MB | Typo-named scratch folder; duplicates parquet + one raw CSV |
| `671_test_data_des/*.csv` | 232 MB | Duplicates `Layer1/data/` and `Layer2/data/671/` for same session |
| Flat vs nested CSV copies in `Layer1/data/` | ~500 MB | Same sessions stored both at root and in `671/`, `252/` subfolders |
| `Layer3_JcvPCA/3_layers_Matser_plan_Full/` | 96 KB | Partial duplicate of root `3_layers_Matser_plan_Full/` |
| 51× `.DS_Store` files | negligible | macOS metadata |

### 6.2 Regeneratable but costly (archive, don't delete casually)

| Item | Size | Regeneration path |
|------|------|-------------------|
| Layer 2 active session outputs (non-archive) | ~32 GB | Re-run `layer2-motive run-until --stage 08` per session |
| Layer 2.5 `pre_jvcpca_review/` | 1.2 GB | Re-run notebooks + `build_gaga_exports.py` |
| Layer 3 primary batch `193319` | 3.6 GB | Re-run `run_gaga_batch_jcvpca.py` |
| Layer 3 per-comparison `.npy`/`.png` | majority of 3.6 GB | Embedded in batch re-run |

### 6.3 Likely canonical / keep-accessible near active work

| Item | Why keep |
|------|----------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | Latest full batch; feeds poster reports and root figures |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | Curated poster tables |
| `outputs/poster_final_figures/` | Final poster deliverables |
| `Layer3_JcvPCA/outputs/671_g4_validation_001/` | Documented first validation reference |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | Upstream input contract for Layer 3 |
| `Layer2.5_Segmentation/segmentation/*.xlsx` | Manual segmentation annotations |

---

## 7. Files probably safe to ignore from Git

### 7.1 Already in `.gitignore` (working as intended)

- `.venv/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `.ipynb_checkpoints/`
- `.DS_Store`, `.cursor/`, IDE caches
- `**/*.parquet`, `**/*.npy`, `**/*.npz`, `**/*.zip`
- `**/*.c3d`, `**/*.bvh`, `**/*.mp4`, `**/*.mov`, `**/*.avi`, `**/*.mkv`
- Raw Motive CSV patterns (`671_test_data_des/*_Take*.csv`, `Layer1/.../data/**/*.csv`, `Layer2/.../data/**/*.csv`)
- Large frame-level kinematic CSVs (stages 05–08)
- Frame-level QC event dumps
- `Layer2.5_Segmentation/outputs/pre_jvcpca_review/_diag/`
- `**/outputs/archive/`

### 7.2 Candidates to **add** to `.gitignore` (future cleanup stage)

| Pattern | Reason |
|---------|--------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_*/` | Large regeneratable batch outputs (~5 GB) |
| `Layer3_JcvPCA/outputs/_workbench_*/` | Exploratory scratch |
| `Layer2.5_Segmentation/reevluate_project/` | Scratch re-evaluation copies |
| `Layer2.5_Segmentation/outputs/archive/` | Superseded exports |
| `Layer1_motive_qc/motive_qc/outputs/batch_runs/` | New untracked batch output |
| `outputs/poster_final_figures/` | Regeneratable from scripts (unless poster submission requires tracking) |
| `**/*.egg-info/` | Build artifact (partially covered) |

### 7.3 Should remain tracked (or selectively tracked)

- All `src/`, `tests/`, `scripts/` (except `__pycache__`)
- Config YAML/CSV templates
- Markdown specs, scope docs, audit reports
- Small validation JSON/CSV summaries (e.g. `671_g4_validation_001/validation_report.json`)
- Segmentation `.xlsx` files
- Reference paper CSVs in `Layer3_JcvPCA/references/`
- Workflow schematic SVG + generator script

---

## 8. Scientifically important — do not delete

### 8.1 Irreplaceable or hard-to-recreate

1. **All raw Motive CSV exports** — Layer 1 `data/`, Layer 2 `data/`, and any unique sessions not backed up elsewhere.
2. **Camera AVI files** (`Layer2/data/252/`) — 20 GB; no regeneration path in-repo.
3. **Manual segmentation work** — `Layer2.5_Segmentation/segmentation/{671,252}_ex_segmentatios_frames.xlsx`.
4. **DataDescriptions sidecars** — session metadata paired with captures.

### 8.2 Scientifically central processed artifacts

1. **Layer 2.5 JcvPCA-ready parquet exports** — `outputs/pre_jvcpca_review/{671,252}/**/window_jvcpca_matrix.parquet` and manifests.
2. **Layer 3 primary batch results** — `gaga_batch_jcvpca_20260626_193319/` root CSV/MD reports:
   - `FINAL_integrated_deep_review_after_p50_p60.md`
   - `directional_robustness_t1_t3_FULL_NUMERIC_REPORT.md`
   - `joint_heatmap_full_numeric_report.md` (referenced in recent work)
   - `jcvpca_link_results*.csv`, `comparable_links_by_comparison.csv`
3. **Natural variability (NV) analyses** — comparisons named `*_I_T*_R1_vs_R2` in batch output.
4. **Participant 671 validation** — `outputs/671_g4_validation_001/`.
5. **Poster deliverables** — `outputs/poster_final_figures/`, `poster_ready_evidence_package/`.

### 8.3 Code and configuration (reproducibility backbone)

- `Layer3_JcvPCA/config/layer3_config.yaml`
- `Layer2.5_Segmentation/outputs/pre_jvcpca_review/layer25_export_manifest.csv`
- All layer `pyproject.toml` / `requirements.txt`
- `3_layers_Matser_plan_Full/MASTER_PLAN.md` and layer pseudocode
- `Layer3_JcvPCA/docs/LAYER3_SCOPE.md`

---

## 9. Risks and uncertainties

| Risk | Detail | Recommended handling |
|------|--------|---------------------|
| **Raw data duplication** | Same sessions in 3–4 locations; unclear if all are identical export types | Hash-compare before deduplication |
| **Layer 1 vs Layer 2 CSV semantics** | Layer 1 = marker QC input; Layer 2 = mixed quaternion CSV — may differ | Document export type per path; never assume interchangeability |
| **Archive vs active Layer 2 outputs** | 22 GB archive may include superseded filtering runs | Cross-reference `stage08_filtering_index.csv` before archiving |
| **Multiple Layer 3 batch runs** | Unclear if earlier runs used different config | Diff `batch_manifest.csv` across runs before removing |
| **Stale root README** | Says Layer 3 "planned" | Update in a later docs pass (not this audit) |
| **Uncommitted deletions** | 3 tracked files show as deleted in git status | Restore or formally commit deletion after review |
| **Typo folder `reevluate_project`** | May contain unique exploratory notes (`revised_pre_jvcpca_review_tables.md`) | Read before archiving |
| **252 P2 sessions** | Present in Layer 2 data (252/) but V1 scope focuses P1 Group 4 | Confirm whether P2 data is needed for poster |
| **Off-repo backup unknown** | 85 GB may exceed git remote; raw data backup status not verified | Confirm external backup before any deletion |
| **Poster figure source of truth** | Root `outputs/poster_final_figures/` vs Layer 3 evidence package | Trace `make_poster_final_figures.py` input paths |

---

## 10. Recommended next cleanup stages

**Principle:** Archive first, delete never without backup + hash verification + explicit approval.

### Stage A — Inventory hardening (no moves)

1. Confirm off-repo backup of all raw CSVs and AVI files.
2. Hash-compare duplicate raw CSV sets (`671_test_data_des` vs Layer 1 vs Layer 2).
3. Document canonical Layer 3 batch run (`193319`) in a `ACTIVE_RUNS.md`.
4. Update root `README.md` Layer 3 status (planned → implemented).

### Stage B — Git hygiene

1. Extend `.gitignore` for Layer 3 batch outputs and workbench folders.
2. Resolve 3 deleted tracked files (restore or commit intentional removal).
3. Decide whether poster figures should be tracked or regenerated-only.

### Stage C — Archive redundant outputs (move, not delete)

Suggested archive target: `_archive/2026-06-cleanup/` outside active paths or per-layer `outputs/archive/` with dated subfolders.

| Priority | Content | Est. savings |
|----------|---------|--------------|
| P1 | `Layer2_Motive_Kinematics/outputs/archive/` | 22 GB |
| P2 | Layer 3 batch runs except `193319` | ~1.3 GB |
| P3 | `Layer3_JcvPCA/outputs/_workbench_*` | ~10 MB |
| P4 | `Layer2.5_Segmentation/reevluate_project/` | 318 MB |
| P5 | Duplicate raw CSV at `671_test_data_des/` (after hash match) | 232 MB |

### Stage D — Reproducible structure rebuild

Proposed clean layout (future state):

```text
3Layers_project/
├── docs/                          # Project-wide docs (this audit, ACTIVE_RUNS, DATA_REGISTRY)
├── layers/
│   ├── layer1_motive_qc/
│   ├── layer2_kinematics/
│   ├── layer2_5_segmentation/
│   └── layer3_jcvpca/
├── data/                          # Single canonical raw data tree (read-only)
│   ├── raw_markers/{671,252}/
│   └── raw_kinematics/{671,252}/
├── outputs/                       # Active run outputs only
│   ├── layer2/
│   ├── layer2_5/
│   ├── layer3/                    # symlink or pointer to canonical batch
│   └── poster/
├── scripts/                       # Cross-layer poster scripts
└── archive/                       # Dated superseded outputs
```

**Do not execute Stage D until Stages A–C are complete and approved.**

### Stage E — Reduce Layer 3 batch bulk (optional, after reproducibility proven)

- Keep root CSV/MD reports + `comparisons/` parquet inputs.
- Strip per-comparison `.npy` and diagnostic `.png` if batch script can regenerate them.
- Potential savings: ~2–3 GB from primary batch alone.

---

## Appendix A — Layer 3 batch runs (2026-06-26)

| Folder | Size | Notes |
|--------|------|-------|
| `gaga_batch_jcvpca_20260626_193319` | 3.6 GB | **Likely canonical** — 20 comparisons, full report suite |
| `gaga_batch_jcvpca_20260626_193110` | 780 MB | Superseded attempt |
| `gaga_batch_jcvpca_20260626_193235` | 371 MB | Superseded attempt |
| `gaga_batch_jcvpca_20260626_180044` | 91 MB | Early run |
| `gaga_batch_jcvpca_20260626_175138` | 91 MB | Early run |
| `gaga_batch_jcvpca_20260626_174553` | 91 MB | Early run |

## Appendix B — Session coverage (participants 671 and 252)

Both participants have sessions at **T1, T2, T3** with repetitions **R1, R2** (P1 focus in V1 scope):

| Layer | 671 | 252 |
|-------|-----|-----|
| Layer 1 raw QC data | ✓ (6 sessions) | ✓ (6+ sessions) |
| Layer 2 kinematic outputs | ✓ (6 active + archive copies) | ✓ (6 P1 sessions + P2 data in raw) |
| Layer 2.5 pre_jvcpca exports | ✓ (full window tree) | ✓ (full window tree) |
| Layer 3 batch comparisons | ✓ (longitudinal, NV, directional) | ✓ (same comparison families) |

## Appendix C — Notebooks (complete list)

| Notebook | Layer | Purpose |
|----------|-------|---------|
| `01_raw_csv_qc_layers_1_2.ipynb` | 1 | Raw CSV QC layers 1–2 |
| `02_raw_csv_qc_layers_3_5.ipynb` | 1 | Raw CSV QC layers 3–5 |
| `post_layer2_segmentation_review.ipynb` | 2.5 | Segmentation review |
| `pre_jvcpca_review.ipynb` | 2.5 | Pre-JcvPCA window export review |

---

*End of audit. No files were moved, renamed, deleted, or overwritten during this inspection.*
