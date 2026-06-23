# Layer 3 JcvPCA Backend Readiness Report

**Date:** 2026-06-24  
**Purpose:** Audit existing Layer 3 backend before UI implementation.  
**Validation dataset:** `T1_P1_R1`, `T1_P1_R2`, `T2_P1_R2` (671, Group 4 upper-body pilot windows).

## Methodological references

| File | Role |
|------|------|
| `references/S1_File.py` | Computational reference (JcvPCA section only) |
| `3_layers_Matser_plan_Full/LAYER3_JCVPCA_PSEUDOCODE.md` | Project pseudocode |
| `docs/LAYER3_SCOPE.md` | V1 scope and input contract |
| `docs/METHOD_ADAPTATION_NOTES.md` | Paper vs project adaptations |
| `3_layers_Matser_plan_Full/MASTER_PLAN_V5_1_CURSOR_SCOPE_ADDENDUM.md` | RSS aggregation rule |

No disagreement found between `S1_File.py` and pseudocode on the JcvPCA sequence.

---

## 1. What Layer 3 logic already exists?

| Module | Status |
|--------|--------|
| `core.py` — `compute_jcvpca`, `select_selected_m_from_A` | Complete, paper-faithful |
| `validation.py` — matrix schema, feature order, selected_m, manifest roles | Complete |
| `io.py` — load matrix, infer features, joint-link map, manifest | Complete |
| `aggregation.py` — RSS axis→link, axis tables | Complete |
| `reporting.py` — JSON/CSV/markdown writers | Complete (V1 runner outputs) |
| `runner.py` — dry_validate + full V1 (6-matrix concatenated design) | Complete for V1 scope |

## 2. Which parts are ready to execute?

- `compute_jcvpca(A, B, feature_names)` — ready
- Per-matrix schema validation — ready
- Cross-matrix feature identity/order match — ready
- RSS link aggregation — ready
- PC selection from A only (90% cumulative variance) — ready
- V1 manifest-driven runner (6 matrices) — ready

Verified on real data: three windows load as 6721/6841/7321 rows × 34 cols (30 features + 4 metadata), 0 NaN, identical canonical feature order, `layer3_safe=true`.

## 3. Which parts are incomplete or unsafe?

| Gap | Severity |
|-----|----------|
| No direct single-window A/B + NV_A/NV_B runner | Missing (additive) |
| No Layer 2.5 manifest preflight (`layer3_safe`, warnings) | Missing (additive) |
| **No Matrix Stability / PCA Readiness checks** | Missing (additive) |
| No plotting | Missing (additive) |
| No main-vs-NV comparison table | Missing (additive) |
| No distribution/democracy metrics | Missing (additive) |
| No UI | Missing |
| V1 runner requires 6 matrices; first validation uses 3 single windows | Design mismatch (handled by new `analysis_service`) |

Nothing in the existing core is scientifically unsafe. Gaps are infrastructure/UI.

## 4. Which parts should be reused?

- `core.compute_jcvpca` — do not modify
- `aggregation.build_axis_table`, `aggregate_axis_to_link_rss` — do not modify
- `validation.validate_jcvpca_matrix`, `validate_feature_schema_match`, `validate_selected_m` — reuse
- `io.load_matrix`, `infer_feature_columns`, `build_joint_link_map` — reuse
- `reporting.write_json`, `write_csv`, `ensure_output_dir` — extend

## 5. Which parts should be modified?

- `reporting.py` — extend with per-analysis output package + matrix stability artifacts
- `__init__.py` — export new public symbols if needed

## 6. Which parts should not be touched?

- `core.py` — computational sequence is verified against paper
- `runner.py` — V1 manifest runner remains for future 6-matrix workflow
- Layer 2.5 export pipeline

## 7. Minimal UI needed

Streamlit page inside existing Layer 2.5 app (`pages/1_Layer3_JcvPCA_Analysis.py`) with: identity, 4 window paths, preflight, **Matrix Stability / PCA Readiness**, parameters, pre-run plots, run (blocked on blocking), results.

## 8. Validation before run

Blocking: schema fail, NaN/inf, feature mismatch, `layer3_safe=false`, matrix rank=0, too few frames.  
Warning (non-blocking): Stage 07/08 burden, near-zero variance features, high condition number, dominant PC.

## 9–10. Plots and tables

**Existing (tables only):** axis/link JcvPCA CSVs, explained variance, NV link table.  
**To add:** all matplotlib plots, matrix stability reports, main-vs-NV table, democracy metrics.

## 11–12. Input assumptions and verification

Assumptions: canonical `Parent_to_Child_axis` features; 4 metadata cols; no NaN; identical order across windows.  
Verified by loading real parquets and export manifests for 671 Group 4 windows.

## Backend checklist (16 questions)

| # | Question | Answer |
|---|----------|--------|
| 1 | Executable JcvPCA backend? | YES |
| 2 | Loads Layer 2.5 matrices? | YES |
| 3 | Validates layer3_safe? | NO (adding in preflight) |
| 4 | Feature columns identical/ordered? | YES |
| 5 | Metadata separated? | YES |
| 6 | Canonical names (not J00x identity)? | YES (real data uses canonical) |
| 7 | PCA fit on A only? | YES |
| 8 | Center A and B correctly? | YES (independent) |
| 9 | No z-scoring? | YES |
| 10 | Project B into A space? | YES (manual matmul) |
| 11 | Re-express B in feature space? | YES |
| 12 | JRW per feature + RSS link? | YES |
| 13 | JcvPCA = abs(B)-abs(A)? | YES |
| 14 | Natural variability support? | YES (same function) |
| 15 | Result tables? | YES; plots NO |
| 16 | Incomplete/inconsistent? | Runner scope only; core OK |

**Verdict:** Proceed with UI on existing core + additive modules including Matrix Stability / PCA Readiness.
