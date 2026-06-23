# Layer 3 JcvPCA UI Implementation Report

**Date:** 2026-06-24  
**Scope:** Layer 3 JcvPCA validation/analysis UI integrated into the existing Layer 2.5 Streamlit app, including Matrix Stability / PCA Readiness.

## Summary

Implemented a multipage Streamlit page (`Layer2.5_Segmentation/dashboard/pages/1_Layer3_JcvPCA_Analysis.py`) that drives the existing Layer 3 JcvPCA computational core via new additive backend modules. The first validation run on participant 671 Group 4 windows completed successfully (`671_g4_validation_001`).

## What was done

### Backend (reused)
- `core.compute_jcvpca` — unchanged; paper-faithful JcvPCA sequence
- `aggregation`, `validation`, `io` — reused

### Backend (new)
| Module | Purpose |
|--------|---------|
| `matrix_stability.py` | Formal Matrix Stability / PCA Readiness metrics and pass/warning/blocking classification |
| `preflight.py` | Manifest-aware schema validation + matrix stability orchestration |
| `identity.py` | Canonical parent/child/link identity columns |
| `analysis_service.py` | Direct single-window A/B + NV_A/NV_B analysis |
| `distribution.py` | Exploratory JRW democracy metrics |
| `nv_compare.py` | Main vs NV ΔJRW comparison table |
| `viz.py` | Matplotlib plots (stability + JcvPCA results) |
| `app_controller.py` | UI orchestration with run gating |
| `reporting.py` | Extended with full output package writers |

### UI
- Added as Streamlit multipage inside existing Layer 2.5 dashboard
- Sections: identity, input windows, preflight, **Matrix Stability / PCA Readiness**, parameters, pre-run plots, run, results
- Run blocked on blocking status; warnings require acknowledgment

### First validation run
- A = T1_P1_R1, B = T2_P1_R2, NV_A = T1_P1_R1, NV_B = T1_P1_R2
- Preflight: **warning** (Stage 07/08 + low frame/feature ratio warnings; not blocking)
- A/reference rank = 30, selected_m = 9
- Output: `Layer3_JcvPCA/outputs/671_g4_validation_001/` (14 plots, all tables, stability reports)

### Tests
40 tests pass, including 14 matrix-stability and preflight/controller gating tests.

## Methodological references

- `Layer3_JcvPCA/references/S1_File.py`
- `Layer3_JcvPCA/3_layers_Matser_plan_Full/LAYER3_JCVPCA_PSEUDOCODE.md`
- `Layer3_JcvPCA/docs/LAYER3_SCOPE.md`
- `Layer3_JcvPCA/docs/METHOD_ADAPTATION_NOTES.md`
- `Layer3_JcvPCA/backend_readiness_report.md`

## Matrix Stability / PCA Readiness

### 1. What metrics were implemented?

Per matrix (A, B, NV_A, NV_B): n_frames, n_features, frame_to_feature_ratio, numeric completeness, NaN/inf counts, total variance, near-zero-variance feature count/percent, feature variance min/median/max, matrix rank, rank fraction, singular values, condition number, dominant PC variance percent, n PCs for 80/90/95% variance, QC burden flags from manifest, optional split-half PC similarity.

### 2. Where are they computed?

`Layer3_JcvPCA/src/layer3_jcvpca/matrix_stability.py` — `assess_matrix_stability()`, called from `preflight.run_preflight()`.

### 3. Blocking vs warning

**Blocking:** NaN/inf, non-numeric features, zero total variance, rank=0, too few frames, feature mismatch, J00x identity, layer3_safe=false.

**Warning:** near-zero-variance features, low rank, high condition number, dominant first PC, low frame/feature ratio, split-half instability, Stage 07/08/Layer1 burden.

Warnings do not block unless combined with blocking schema failures.

### 4. Default thresholds and rationale

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| near_zero_variance_threshold | 1e-8 | Detect numerically flat features |
| min_frames_required | 10 | Matches existing PCA floor |
| min_frames_per_feature_ratio | 5 | Rule-of-thumb for stable PCA |
| condition_number_warning_threshold | 1e8 | Standard ill-conditioning flag |
| pc_dominance_warning_threshold | 0.80 | Single-PC dominance warning |
| split_half_similarity_warning_threshold | 0.85 | Exploratory stability check |

### 5. A/reference emphasis

A metrics highlighted in UI ("A/reference PCA readiness") and primary stability tables (`feature_variance_table.csv`, `joint_variance_table.csv`, `singular_value_table.csv`) saved from A. Manifest records `rank_A`, `condition_number_A`, etc.

### 6. UI display

Section 4 shows per-matrix stability table, A/reference metrics (rank, condition number, dominant PC %, frame/feature ratio), and explanatory caveat text.

### 7. Saved plots/tables

`matrix_stability_report.{md,csv}`, `feature_variance_table.csv`, `joint_variance_table.csv`, `singular_value_table.csv`, `split_half_stability_table.csv` (when enabled), plus stability plots in `plots/`.

### 8. What remains exploratory

Split-half PCA similarity, motion-energy timeline, democracy/Gini metrics, main-vs-NV exceed flags — all descriptive, not statistical proof.

### 9. PI review before interpreting

- Single-window comparison is calibration, not V1 concatenated design
- Main pair differs in timepoint AND repetition; NV differs only in repetition
- One NV pair is a descriptive baseline, not significance testing
- Upper-body 10-link pilot scope (not whole-body core-16)
- Stage 07/08 warnings present in real windows — review QC burden
- Matrix stability warnings on real data (17 warnings) — review before claiming robust JcvPCA structure

## Self-review

1. **Backend verified before UI?** Yes — `backend_readiness_report.md` written first; core reused unchanged.
2. **Guiding files inspected?** Yes — S1_File.py, pseudocode, scope docs.
3. **A/B direction preserved?** Yes — A is reference; B is comparison.
4. **No z-scoring?** Yes — not exposed or used.
5. **Metadata out of PCA?** Yes — `_rx/_ry/_rz` only.
6. **Canonical feature identity?** Yes — J00x rejected in preflight.
7. **NV as descriptive baseline?** Yes — labeled throughout.
8. **Safe parameters only?** Yes — dangerous options not exposed.
9. **Enough plots for PI?** Yes — 14 plots on first run including stability + JcvPCA.
10. **Democracy metrics caveated?** Yes — labeled exploratory.
11. **Scientifically uncertain:** single-window level, asymmetric main vs NV design, pilot link scope.
12. **PI should review:** QC warnings, stability warnings, PC count choice, whether main ΔJRW exceeds NV descriptively.

## Remaining work (future)

- Manifest-driven comparison selector (`layer3_comparison_manifest.csv`)
- Accumulated-window stability curve
- Full 6-matrix V1 runner integration in UI
- Interactive Plotly option (currently matplotlib per user choice)

## How to run

```bash
cd Layer2.5_Segmentation
pip install -r requirements-dashboard.txt
pip install -e ../Layer3_JcvPCA
streamlit run dashboard/pre_jvcpca_dashboard.py
```

Navigate to **Layer 3 JcvPCA Analysis** in the sidebar.
