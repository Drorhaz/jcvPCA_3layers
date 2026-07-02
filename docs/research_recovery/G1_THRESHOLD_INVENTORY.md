# G1 — Threshold Inventory (initial governed registry)

**Date:** 2026-07-01  
**Phase:** G1 (from [`PROGRAM_GUI_OPTIMIZATION_PLAN.md`](PROGRAM_GUI_OPTIMIZATION_PLAN.md) Section 4).  
**Status:** **Initial governed registry — not complete all-layer coverage.** See [`G1_REVIEW_ADDENDUM.md`](G1_REVIEW_ADDENDUM.md).

**Purpose:** Document decision-relevant thresholds across L1–L3: where each live value lives today, and what G1 has mirrored into `config/` with rich schema. G1 provides **full Layer 3 (Gaga batch) coverage** and a **curated L1/L2/L2.5 subset** — not every threshold in every layer YAML.

**Federation stance (Option A):** L1/L2/L2.5 already externalize thresholds to layer YAML; runners still read those files. The central registry re-declares a **curated** subset for GUI visibility, invalidation metadata, and future wiring. **Layer 3** constants were hidden in Python; `config/analysis_params.yaml` mirrors them and is verified bit-for-bit by test (runners not rewired yet).

---

## Coverage summary (G1 scope)

| Layer | In central registry | Still only in layer source |
|-------|---------------------|----------------------------|
| L3 Gaga batch | **Full** (~15 entries in `analysis_params.yaml`) | Python constants (authoritative until rewiring) |
| L1 QC | **Curated 15** (G1.1 high-impact) | ~5+ more in `Layer1_motive_qc/motive_qc/config.yaml` |
| L2 kinematics | **Curated 7** (G1.1 high-impact) | ~2+ more in `default_layer2_config.yaml` |
| L2.5 | **Curated 6** | Full severity logic in `warnings.py` |

**G1.1 mirrored subset** (in `config/qc_rules.yaml` only — see [`G1_1_HIGH_IMPACT_QC_LOG.md`](G1_1_HIGH_IMPACT_QC_LOG.md)):

- **L1 (15):** readiness coverage; marker gap tiers (`max_missing_percent` pass/warn/caution + `max_large_gaps` pass/caution); session acceptable/caution missing % and large gaps; frame caution/exclude missing %; velocity/acceleration percentiles; `chosen_sigma`.
- **L2 (7):** quaternion pass/warn norm error; rotvec jump warn/fail; near-π fraction; filtering cutoff; jump context window.
- **L2.5 (6):** feature scope + finger/toe exclusion + warn/strong_warn/block severity gates.

---

## Layer 1 — Motive marker QC
Source: `Layer1_motive_qc/motive_qc/config.yaml`

| Threshold | Value | Meaning |
|-----------|-------|---------|
| `min_marker_coverage_pct` | 90.0 | Minimum marker coverage |
| `skeleton_overlap_min_markers` | 10 | Min shared markers for skeleton overlap |
| gap tiers `max_missing_percent` | 1.0 / 5.0 / 10.0 | Pass/warn/fail missing-frame tiers |
| gap tiers `max_large_gaps` | 0 / 0 / 1 | Large-gap tolerance per tier |
| `primary_report_thresholds_seconds` | [0.1, 0.2, 0.5, 1.0] | Gap-duration reporting bins |
| `velocity_percentile_threshold` | 99.97 | Velocity artifact percentile |
| `acceleration_percentile_threshold` | 99.97 | Acceleration artifact percentile |
| `sigma_sensitivity.chosen_sigma` | 8.0 | Artifact detection sigma |
| `min_jump_distance_m` | 0.10 | Marker jump distance |
| `max_rigid_cv` | 0.05 | Rigid-pair coefficient of variation |
| `max_segment_length_change_pct` | 18.0 | Segment length change |
| `peer_zscore_threshold` | 2.5 | Peer z-score outlier |
| `hf_power_ratio_threshold` | 0.02 | High-frequency power ratio |

## Layer 2 — Kinematics
Source: `Layer2_Motive_Kinematics/configs/default_layer2_config.yaml`

| Threshold | Value | Meaning |
|-----------|-------|---------|
| `quaternion_qc.pass_max_abs_norm_error` | 1.0e-3 | Quaternion norm pass |
| `quaternion_qc.warning_max_abs_norm_error` | 1.0e-2 | Quaternion norm warn |
| `quaternion_qc.min_complete_xyzw_percent` | 99.0 | Complete quaternion coverage |
| `rotvec.jump_warning_rad` | 0.5 | Rotvec jump warn |
| `rotvec.jump_fail_rad` | 1.0 | Rotvec jump fail (Stage 07) |
| `rotvec.near_pi_warning_fraction` | 0.95 | Branch-cut warn |
| `filtering.cutoff_hz` | 10.0 | Butterworth cutoff |
| `filtering.jump_context_window_frames` | 30 | Stage 08 mask window (±frames) |

## Layer 2.5 — Segmentation / export
Sources: `Layer2.5_Segmentation/config/default_feature_scope.yaml`; severity logic in `src/pre_jvcpca_review/warnings.py`

| Threshold | Value | Meaning |
|-----------|-------|---------|
| `allowed_feature_scope` | core_candidate | Feature-scope tag required for inclusion |
| `exclude_fingers` / `exclude_toes` | true / true | Distal exclusion |
| warning severities | info / warning / strong_warning / blocking | Warn-vs-fail gate |
| blocking warnings | missing matrix, schema mismatch, constant column | Hard export block |

## Layer 3 — JcvPCA  (**hidden in Python — migrate to `analysis_params.yaml`**)

| Threshold | Value | Source location |
|-----------|-------|-----------------|
| `pca.variance_threshold` | 0.80 | `jcvpca_trace.py:260` `DEFAULT_VARIANCE_THRESHOLD`; `gaga_batch_runner.py:479` |
| `pca.min_pcs` | 2 | `jcvpca_trace.py:261` |
| `pca.max_pcs` | 10 | `jcvpca_trace.py:262` |
| `pc_focus.cumulative_thresholds` | [0.50, 0.60] | `run_pc_focus_p50_p60_sensitivity.py:64-65` |
| `pc_focus.sensitivity_p_archived` | 2 | `gaga_batch_runner.py:75` `SENSITIVITY_P` |
| `weighting.explained_variance_weighting` | false | `gaga_batch_runner.py:508` |
| `distribution.low_contribution_flag` | 0.02 | `analyze_link_contribution_distribution.py:26` `P_LINK_FLOOR_FLAG` |
| `cohort.participants` | ["671","252"] | `gaga_batch_runner.py:66` |
| `cohort.blocks.A` | [P1,P2,P3,P4,P5] | `gaga_batch_runner.py:68` |
| `cohort.blocks.B` | [P3,P4,P5] | `gaga_batch_runner.py:69` |

Also locked-by-scope (from `Layer3_JcvPCA/docs/LAYER3_SCOPE.md`): independent per-dataset centering, no normalization/z-scoring, full rx/ry/rz triplet, RSS aggregation.

---

*Inventory only — no runner behavior changed. `config/analysis_params.yaml` values are verified against these by `tests/test_analysis_config.py`.*
