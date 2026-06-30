# Layer 3 — JcvPCA (V1)

Layer 3 is a **computational, auditable** Python package that implements a conservative adaptation of the **JcvPCA** framework (Dubois et al.) for Gaga / OptiTrack / Motive movement data.

It compares **parent–child relative rotation-vector contribution structure** between a reference condition **A** and a comparison condition **B**. It emits **numbers and neutral reports only**. It does **not** decide whether a change is statistically significant, clinically meaningful, robust, or beyond natural variability — that interpretation happens later (e.g. in a notebook or PI review).

Layer 3 is **independent** of Layers 1, 2, and 2.5. It **reads** Layer 2.5 JcvPCA-ready window matrices as input and never modifies upstream pipelines.

---

## Quick orientation for agents

| Question | Answer |
|----------|--------|
| What does Layer 3 compute? | JcvPCA-style axis and joint-link (RSS) deltas between A and B, plus a natural-variability (NV) baseline |
| What is the sacred core? | `src/layer3_jcvpca/core.py` → `compute_jcvpca()` — paper-faithful; do not change the sequence |
| What are the two ways to run it? | (1) **CLI manifest runner** — 6-matrix V1 design; (2) **Streamlit UI / `analysis_service`** — single-window validation (currently used in practice) |
| Where do inputs come from? | `Layer2.5_Segmentation/outputs/.../window_jvcpca_matrix.parquet` |
| Where do outputs go? | `Layer3_JcvPCA/outputs/<analysis_id>/` |
| What blocks a run? | Preflight **blocking** status (schema fail, NaN/inf, `layer3_safe=false`, rank=0, feature mismatch, etc.) |
| What requires acknowledgment? | Preflight **warning** status (matrix stability, QC burden, etc.) — UI gates on this |
| Reference implementation | `references/S1_File.py` (JcvPCA section only) |
| Scope doc (authoritative) | `docs/LAYER3_SCOPE.md` |
| First real validation run | `outputs/671_g4_validation_001/` |

---

## Position in the project pipeline

```text
Layer 1  (raw QC, gaps, artifacts)
    ↓
Layer 2  (quaternions, filtering, kinematics)
    ↓
Layer 2.5 (segmentation, window selection, JcvPCA-ready matrix export)
    ↓
Layer 3  (this package — JcvPCA comparison on exported matrices)
    ↓
External interpretation (notebooks, PI review, reporting)
```

Layer 3 assumes upstream work is done: marker QC, quaternion reconstruction, filtering, segmentation, and window selection all happen before Layer 3. Layer 3 only validates that exported matrices meet its input contract and are numerically suitable for PCA.

---

## Scientific framing

**Describe the analysis as:**

> JcvPCA-style comparison of Motive-derived parent–child relative rotation-vector contribution structure.

**Preferred interpretation language:**

- increased / decreased contribution in B relative to A
- change beyond T1 repetition-level variability (when compared descriptively to NV)
- within T1 repetition-level variability / inconclusive

**Do not claim (Layer 3 does not support these):**

- statistical significance, proof of change, causal motor change
- direct anatomical joint loading or muscle use
- synchronization change

**Features used:** columns ending in `_rx`, `_ry`, `_rz` (3D rotation-vector components per parent–child link). Metadata columns never enter PCA.

**Centering rule (critical):** A and B are each centered by their **own** column means. B is **not** centered with A's mean. Manual projection is used; `PCA_A.transform(B_raw)` is forbidden because it would apply A's fitted mean to B.

**Normalization:** No z-scoring, no variance scaling, no range normalization.

---

## Two execution paths (both exist today)

Layer 3 currently supports **two complementary workflows**. Agents should know which one applies to a task.

### Path A — V1 manifest runner (6-matrix concatenated design)

**Entry:** `scripts/run_layer3_jcvpca.py` → `runner.py`

**Config:** `config/layer3_config.yaml` (`mode: dry_validate` or `mode: full`)

**Design:** Requires six Group 4 matrices defined in `config/layer3_analysis_manifest_template.csv`:

```text
A_T1  = A_T1_R1 + A_T1_R2   (row-wise concat)
B_T2  = B_T2_R1 + B_T2_R2
B_T3  = B_T3_R1 + B_T3_R2
NV_T1 = A_T1_R1 vs A_T1_R2  (same compute_jcvpca, not a statistical test)
```

**Comparisons run in `full` mode:**

1. `compute_jcvpca(A_T1, B_T2)`
2. `compute_jcvpca(A_T1, B_T3)`
3. `compute_jcvpca(A_T1_R1, A_T1_R2)` → natural variability reference

**Modes:**

| Mode | What it does |
|------|----------------|
| `dry_validate` | Load every included manifest row; per-matrix schema validation + cross-matrix feature match. No PCA. Writes `validation_report.json`. |
| `full` | All six matrices required; builds datasets, runs three comparisons, writes V1 CSV/JSON outputs under `output_dir`. |

**Status:** Implemented and tested. Not yet wired into the Streamlit UI. Deferred in practice until all six Group 4 matrices are available and approved.

### Path B — Direct single-window analysis (UI + `analysis_service`)

**Entry:** Streamlit page `Layer2.5_Segmentation/dashboard/pages/1_Layer3_JcvPCA_Analysis.py`  
**Backend:** `analysis_service.run_direct_analysis()` via `app_controller.Layer3AnalysisController`

**Design:** Four **single windows** (not concatenated):

| Role | Meaning |
|------|---------|
| `A` | Reference window (defines PCA space) |
| `B` | Comparison window |
| `NV_A` | Natural-variability reference (often same file as A) |
| `NV_B` | Natural-variability comparison (different repetition, same timepoint as NV_A) |

**Comparisons:**

1. Main: `compute_jcvpca(A, B)` → labeled `main_A_vs_B`
2. NV: `compute_jcvpca(NV_A, NV_B)` → labeled `NV_A_vs_B`

**Additional outputs vs V1 runner:** matrix stability reports, preflight validation report, main-vs-NV table, distribution/democracy metrics, ~14 matplotlib plots.

**Status:** This is the **currently exercised path**. First validation run: `outputs/671_g4_validation_001/`.

**Important design note:** The single-window path is **calibration / validation**, not the full V1 concatenated cross-repetition design. The main A vs B pair can differ in both timepoint and repetition; NV differs only in repetition within T1.

---

## Core algorithm (`core.compute_jcvpca`)

The computational sequence intentionally matches `references/S1_File.py` (JcvPCA section), generalized to many features and variable `selected_m`:

```text
1. Center A independently:  A_centered = A - A.mean(axis=0)
2. Fit PCA on A → pca_A_frame, pca_A_variance_ratio
3. Center B independently:  B_centered = B - B.mean(axis=0)
4. Project B into A's PCA space:  B_projected = B_centered @ pca_A_frame.T
5. Fit PCA on B_projected → pca_B_frame
6. Re-express B loadings in original feature space:  B_reproj = pca_B_frame @ pca_A_frame
7. JcvPCA_axis = |B_reproj| - |A_loadings|
```

**PC selection (`selected_m`):** Smallest number of A-PCs reaching cumulative explained variance ≥ threshold (default **0.90**), computed from **A only**. In the UI path, result is clamped to `[min_pcs, max_pcs]` (defaults 2–10). Can be overridden via config (`selected_m_override`) but is always re-validated.

**Joint-link aggregation (project adaptation):** The paper uses scalar joints; this project uses rx/ry/rz triplets per link. Link-level **JRW** uses root-sum-square across the triplet, not simple sum:

```python
JRW_A_link = sqrt(A_rx² + A_ry² + A_rz²)
JRW_B_link = sqrt(B_rx² + B_ry² + B_rz²)
JcvPCA_link = JRW_B_link - JRW_A_link
```

See `aggregation.py` and `docs/METHOD_ADAPTATION_NOTES.md`.

---

## Package layout

```text
Layer3_JcvPCA/
├── config/
│   ├── layer3_config.yaml              # CLI runner config
│   ├── layer3_config_sample.yaml
│   └── layer3_analysis_manifest_template.csv
├── docs/
│   ├── LAYER3_SCOPE.md                 # Authoritative V1 scope
│   ├── METHOD_ADAPTATION_NOTES.md      # Paper vs project differences
│   ├── LAYER3_UI_IMPLEMENTATION_REPORT.md
│   └── figures/jcvpca_workflow/        # Workflow schematic
├── outputs/
│   ├── layer3_jcvpca/                  # CLI runner outputs
│   └── 671_g4_validation_001/          # First UI validation run
├── references/
│   ├── S1_File.py                      # Paper Python reference
│   └── Data_from_the_paper_jcvPCA/     # Paper sample CSVs
├── scripts/
│   └── run_layer3_jcvpca.py            # CLI entrypoint
├── src/layer3_jcvpca/
│   ├── core.py                         # ★ JcvPCA computation (do not alter sequence)
│   ├── aggregation.py                  # Axis tables, RSS link aggregation
│   ├── validation.py                   # Schema, feature order, selected_m checks
│   ├── io.py                           # Load parquet/csv, manifest, feature inference
│   ├── runner.py                       # V1 manifest runner (dry_validate / full)
│   ├── preflight.py                    # 4-window schema + layer3_safe + stability orchestration
│   ├── matrix_stability.py             # Matrix Stability / PCA Readiness metrics
│   ├── analysis_service.py             # Direct single-window analysis
│   ├── app_controller.py               # UI orchestration + run gating
│   ├── nv_compare.py                   # Main vs NV ΔJRW comparison table
│   ├── distribution.py                 # Exploratory JRW democracy metrics
│   ├── identity.py                     # Parent/child/link identity enrichment
│   ├── reporting.py                    # CSV/JSON/Markdown writers + output package
│   └── viz.py                          # Matplotlib plots
└── tests/                              # 7 test modules (~40 tests)
```

---

## Input contract

Layer 3 consumes **Layer 2.5 exported window matrices** (`.parquet` or `.csv`).

### Required metadata columns (never enter PCA)

```text
session_id, run_label, frame, time_sec
```

### Required feature columns

```text
<any_joint_link_stem>_rx
<any_joint_link_stem>_ry
<any_joint_link_stem>_rz
```

Example: `Neck_to_Head_rx`, `Neck_to_Head_ry`, `Neck_to_Head_rz`

### Validation rules (enforced; no silent repair)

- Feature columns numeric; no NaN; no inf
- No constant (zero-variance) feature columns
- Identical feature names and **identical column order** across all A/B/NV matrices
- Each link has a complete rx/ry/rz triplet
- Enough rows for PCA (`min_rows_for_pca`, default 10)
- `selected_m` valid against A and B dimensions
- Preflight rejects legacy `J00x_`-style feature identity columns
- Preflight checks Layer 2.5 export manifest for `layer3_safe=false` (blocking)

Real pilot data (participant 671, Group 4): ~6720–7320 rows × 34 columns (30 features + 4 metadata), 10 upper-body links, canonical naming, `layer3_safe=true`.

---

## Preflight and Matrix Stability / PCA Readiness

Before analysis (Path B), `preflight.run_preflight()` loads four windows and runs:

1. **Schema validation** — same rules as above, per matrix
2. **Cross-matrix feature match** — names and order
3. **Layer 2.5 manifest checks** — `layer3_safe`, QC warning burden
4. **Matrix stability** — `matrix_stability.assess_matrix_stability()` per role (A, B, NV_A, NV_B)

### Preflight status

| Status | Meaning | Run allowed? |
|--------|---------|--------------|
| `pass` | All checks OK | Yes |
| `warning` | Non-blocking issues (stability, QC burden, etc.) | Yes in UI **after user acknowledgment** |
| `blocking` | Schema/safety failures | No |

### Matrix stability metrics (per matrix)

Examples: `n_frames`, `n_features`, `frame_to_feature_ratio`, matrix rank, condition number, dominant PC variance %, near-zero-variance feature count, singular value spectrum, split-half PC similarity, motion-energy timeline, QC burden flags from Layer 2.5 manifest.

**A/reference is emphasized** because A defines the PCA space. Primary stability tables and key manifest fields (`rank_A`, `condition_number_A`, etc.) come from A.

Default warning thresholds live in `MatrixStabilityParams` (`matrix_stability.py`). See `docs/LAYER3_UI_IMPLEMENTATION_REPORT.md` for the full table.

---

## Outputs

### Path A — V1 runner (`outputs/layer3_jcvpca/` or configured `output_dir`)

| File | Content |
|------|---------|
| `validation_report.json` | Dry validate or full-mode validation summary |
| `analysis_metadata.json` | Run metadata, feature list, selected_m, roles used |
| `explained_variance.csv` | Per-PC variance for each comparison |
| `jcvpca_axis.csv` | Axis-level JcvPCA per PC × feature |
| `jrw_axis.csv` | Absolute loadings (A and B reprojected) per axis |
| `jcvpca_link.csv` | Link-level RSS JcvPCA |
| `jrw_link.csv` | Link-level JRW A and B |
| `natural_variability_t1.csv` | NV link-level table |
| `natural_variability_t1_axis.csv` | NV axis-level table |
| `interpretation_summary.md` | Neutral summary (no significance claims) |

### Path B — UI / `analysis_service` (`outputs/<analysis_id>/`)

**Tables:**

| File | Content |
|------|---------|
| `analysis_manifest.json` | Run provenance, paths, selected_m, stability summary |
| `analysis_summary.md` | Short human-readable summary |
| `analysis_validation_report.{csv,md}` | Preflight check list |
| `matrix_stability_report.{csv,md}` | Per-matrix stability findings |
| `feature_variance_table.csv` | A/reference feature variances |
| `joint_variance_table.csv` | A/reference link variances |
| `singular_value_table.csv` | A/reference singular values |
| `split_half_stability_table.csv` | Split-half check (when enabled) |
| `pc_variance_table.csv` | Explained variance for selected PCs |
| `jrw_feature_table.csv` | Axis-level loadings + identity columns |
| `jrw_joint_table.csv` | Link-level JRW and JcvPCA |
| `jcvpca_delta_jrw_table.csv` | ΔJRW per link × PC |
| `nv_jrw_table.csv` | NV link-level results |
| `main_vs_nv_comparison_table.csv` | Main ΔJRW vs NV ΔJRW (descriptive exceed flags) |

**Plots** (`plots/` — generated by `viz.save_analysis_plots`):

| Plot | Purpose |
|------|---------|
| `feature_variance_bar.png` | A/reference per-feature variance |
| `joint_variance_bar.png` | A/reference per-link variance |
| `singular_value_spectrum.png` | Singular value decay |
| `motion_energy_timeline.png` | Per-frame motion-energy proxy (A) |
| `qc_flag_timeline.png` | QC flag timeline from manifest (A) |
| `split_half_pca_similarity.png` | Split-half stability (when available) |
| `scree_plot.png` | A/reference scree |
| `cumulative_variance.png` | A/reference cumulative EVR |
| `pc_trajectory_A_B.png` | PC1 vs PC2 trajectories |
| `pc_trajectory_A_B_3d.png` | PC1–PC3 trajectories |
| `pc_trajectory_A_B_multipc.png` | Multi-PC trajectory panels |
| `pc_score_heatmap_A_B.png` | PC score heatmap |
| `jrw_A_B_bar.png` | JRW A vs B per link |
| `delta_jrw_bar.png` | ΔJRW (JcvPCA) per link |
| `delta_jrw_vs_nv.png` | Main vs NV comparison |
| `jrw_heatmap_joint_axis.png` | Loadings heatmap (link × axis) |
| `jrw_democracy_curve.png` | Exploratory democracy/Gini curve |

---

## Install

```bash
cd Layer3_JcvPCA
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

**Dependencies:** numpy, pandas, scikit-learn, pyarrow, pyyaml, matplotlib  
**Python:** ≥ 3.10

---

## How to run

### CLI (V1 manifest runner)

```bash
python scripts/run_layer3_jcvpca.py --config config/layer3_config.yaml
```

Edit `config/layer3_config.yaml`:

- `manifest_path` — path to manifest CSV with six Group 4 roles
- `output_dir` — where to write results
- `mode` — `dry_validate` (default) or `full`
- `variance_threshold` — default 0.90
- `selected_m_override` — optional; `null` = derive from A
- `min_rows_for_pca` — default 10
- `export_weighted` — default false

### Streamlit UI (single-window analysis — current primary workflow)

```bash
cd Layer2.5_Segmentation
pip install -r requirements-dashboard.txt
pip install -e ../Layer3_JcvPCA
streamlit run dashboard/pre_jvcpca_dashboard.py
```

Open sidebar → **Layer 3 JcvPCA Analysis**.

**UI flow:**

1. Analysis identity (ID, participant, notes)
2. Four window paths (A, B, NV_A, NV_B) — defaults point at 671 Group 4 pilot windows
3. Preflight — schema + stability
4. Matrix Stability / PCA Readiness review
5. Analysis parameters (PC selection mode, thresholds)
6. Pre-run plots (optional preview)
7. Run — blocked on blocking preflight; warnings require checkbox acknowledgment
8. Results — tables, plots, download paths

### Programmatic (for agents/scripts)

```python
from pathlib import Path
from layer3_jcvpca.analysis_service import AnalysisIdentity, AnalysisParams, run_direct_analysis
from layer3_jcvpca.preflight import run_preflight

paths = {
    "A": ".../window_jvcpca_matrix.parquet",
    "B": ".../window_jvcpca_matrix.parquet",
    "NV_A": ".../window_jvcpca_matrix.parquet",
    "NV_B": ".../window_jvcpca_matrix.parquet",
}
preflight = run_preflight(paths)
result = run_direct_analysis(
    paths,
    AnalysisIdentity(analysis_id="my_run_001", participant_id="671"),
    AnalysisParams(),
    output_dir="Layer3_JcvPCA/outputs/my_run_001",
    preflight=preflight,
)
```

---

## Tests

```bash
cd Layer3_JcvPCA
pytest -q
```

| Test module | What it covers |
|-------------|----------------|
| `test_core_matches_paper_logic.py` | JcvPCA sequence vs paper reference |
| `test_rss_aggregation.py` | RSS link aggregation |
| `test_input_validation.py` | Matrix schema validation |
| `test_feature_order.py` | Feature order enforcement |
| `test_matrix_stability.py` | Stability metrics and thresholds |
| `test_preflight_ui.py` | Preflight + controller gating |
| `test_analysis_service.py` | End-to-end direct analysis |

Core invariants enforced by tests: no z-scoring, independent centering, no `PCA.transform` on B, PC selection from A only, RSS not sum for links.

---

## V1 scope — included vs excluded

### Included in V1

- Group 4, group-level, cross-repetition analysis (manifest runner)
- Single-window validation path (UI)
- T1 as reference condition
- `_rx/_ry/_rz` rotation-vector features only
- Natural variability as descriptive baseline (not statistical test)
- Matrix Stability / PCA Readiness checks
- Matplotlib visualization package

### Explicitly excluded (do not implement without scope change)

- Group 5
- Task-level analysis
- JsvCRP, CRP
- Bootstrap / inferential statistics
- Cross-subject analysis
- Automatic segmentation or window selection
- Euler, omega, position, velocity features
- Z-scoring or variance normalization

---

## Reference run: `671_g4_validation_001`

Example of a completed Path B run (participant 671, Group 4 upper-body pilot):

| Window | Path role | Source |
|--------|-----------|--------|
| T1_P1_R1 | A, NV_A | Reference / NV reference |
| T2_P1_R2 | B | Comparison (different timepoint + repetition) |
| T1_P1_R2 | NV_B | NV comparison (repetition only) |

**Results snapshot:**

- Preflight: **warning** (17 warnings, 0 blocking — Stage 07/08 QC burden, stability flags)
- `selected_m`: 9 (90% cumulative variance on A, clamped to [2, 10])
- A rank: 30 features; frame/feature ratio ≈ 224
- Output: `outputs/671_g4_validation_001/` — all tables + 14 plots

Agents inspecting expected output structure should start there.

---

## Key documentation map

| Document | Use when |
|----------|----------|
| `docs/LAYER3_SCOPE.md` | Authoritative scope, input contract, output list |
| `docs/METHOD_ADAPTATION_NOTES.md` | Paper vs project differences |
| `docs/LAYER3_UI_IMPLEMENTATION_REPORT.md` | UI architecture, stability thresholds, PI review checklist |
| [`docs/legacy/layer3/backend_readiness_report.md`](../docs/legacy/layer3/backend_readiness_report.md) | Pre-UI backend audit |
| [`docs/legacy/master_plan/LAYER3_JCVPCA_PSEUDOCODE.md`](../docs/legacy/master_plan/LAYER3_JCVPCA_PSEUDOCODE.md) | Project pseudocode |
| `references/S1_File.py` | Original paper Python (JcvPCA lines ~82–106) |

---

## Agent guidelines — do's and don'ts

**Do:**

- Treat `core.compute_jcvpca` as frozen unless there is a documented methodological bug
- Read preflight / matrix stability before interpreting JcvPCA magnitudes
- Label NV comparisons as descriptive baselines
- Keep metadata out of PCA
- Match existing module boundaries when adding features

**Don't:**

- Add z-scoring, `PCA.transform(B)`, or alternative PCA-comparison methods
- Claim statistical significance from Layer 3 outputs
- Silently repair or impute bad input matrices
- Conflate the single-window UI path with the 6-matrix V1 concatenated design
- Modify Layer 2.5 export logic from Layer 3

---

## Known gaps / future work

- Manifest-driven comparison selector in UI (`layer3_comparison_manifest.csv`)
- Full 6-matrix V1 runner integration in Streamlit
- Accumulated-window stability curve
- Interactive Plotly plots (currently matplotlib only)
- `full` CLI mode awaiting all six Group 4 matrices and PI approval

---

## Workflow schematic

A visual overview of the Layer 3 pipeline is in:

- `docs/figures/jcvpca_workflow/jcvpca_workflow_schematic.svg`
- `docs/figures/jcvpca_workflow/jcvpca_workflow_schematic.png`

Regenerate with:

```bash
python docs/figures/jcvpca_workflow/generate_jcvpca_workflow_figure.py
```
