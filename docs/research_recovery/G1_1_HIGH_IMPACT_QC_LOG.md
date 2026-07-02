# G1.1 — High-Impact QC Threshold Coverage

**Date:** 2026-07-01  
**Mode:** Config/docs/tests only — no runner rewiring, no runtime behavior change  
**Goal:** Make G2 Data Readiness traffic lights scientifically defensible while keeping registry **curated, not complete**.

---

## Thresholds added or corrected (G1.1)

### Layer 1 — `Layer1_motive_qc/motive_qc/config.yaml`

| Registry key | Value | Source path |
|--------------|-------|-------------|
| `layer1.min_marker_coverage_pct` | 90.0 | `readiness.min_marker_coverage_pct` *(source key corrected)* |
| `layer1.max_missing_percent_pass` | 1.0 | `quality_labels.marker.clean.max_missing_percent` |
| `layer1.max_missing_percent_warn` | 5.0 | `quality_labels.marker.minor_issue.max_missing_percent` |
| `layer1.max_missing_percent_caution` | 10.0 | `quality_labels.marker.caution.max_missing_percent` *(replaces `max_missing_percent_fail`)* |
| `layer1.max_large_gaps_pass` | 0 | `quality_labels.marker.clean.max_large_gaps` |
| `layer1.max_large_gaps_caution` | 1 | `quality_labels.marker.caution.max_large_gaps` |
| `layer1.session_acceptable_max_labeled_missing_percent` | 5.0 | `quality_labels.session.acceptable_for_preprocessing.max_labeled_missing_percent` |
| `layer1.session_caution_max_labeled_missing_percent` | 10.0 | `quality_labels.session.caution_for_preprocessing.max_labeled_missing_percent` |
| `layer1.session_acceptable_max_large_gaps_labeled` | 0 | `quality_labels.session.acceptable_for_preprocessing.max_large_gaps_labeled` |
| `layer1.session_caution_max_large_gaps_labeled` | 2 | `quality_labels.session.caution_for_preprocessing.max_large_gaps_labeled` |
| `layer1.frame_caution_missing_labeled_percent` | 10.0 | `frame_qc_mask.caution_missing_labeled_percent` |
| `layer1.frame_exclude_missing_labeled_percent` | 20.0 | `frame_qc_mask.exclude_missing_labeled_percent` |
| `layer1.acceleration_percentile_threshold` | 99.97 | `artifacts.acceleration_percentile_threshold` |

**Updated (not new):** `velocity_percentile_threshold`, `chosen_sigma` — full downstream invalidation + corrected `source_config_key` (`artifacts.sigma_sensitivity.chosen_sigma`).

### Layer 2 — `Layer2_Motive_Kinematics/configs/default_layer2_config.yaml`

| Registry key | Value | Source path |
|--------------|-------|-------------|
| `layer2.rotvec_jump_warning_rad` | 0.5 | `rotvec.jump_warning_rad` |
| `layer2.rotvec_near_pi_warning_fraction` | 0.95 | `rotvec.near_pi_warning_fraction` |
| `layer2.quaternion_warning_max_abs_norm_error` | 0.01 | `quaternion_qc.warning_max_abs_norm_error` |

**Already present (G1):** `jump_context_window_frames`, `rotvec_jump_fail_rad`, `quaternion_pass_max_abs_norm_error`, `filtering_cutoff_hz` — invalidation chains extended in G1.1.

---

## Invalidation tags (G1.1 standard chains)

**L1 high-impact QC** → invalidates:
`layer1_qc`, `layer2_5_exports`, `layer3_batches`, `decision_summaries`, `audit_reports`, `poster_packages`, `exported_figures`

**L2 high-impact QC** → invalidates:
`layer2`, `layer2_5_exports`, `layer3_batches`, `decision_summaries`, `audit_reports`, `poster_packages`, `exported_figures`

Regenerate guidance: L1 → `[layer1_qc, layer2_5_exports, layer3_batches]`; L2 → `[layer2, layer2_5_exports, layer3_batches]`.

---

## Runtime behavior

**Unchanged.** Layer runners still read layer YAML; registry is declarative + tested only.

---

## Tests

`tests/test_analysis_config.py` — 25 parametrized source-path mirrors + G1.1 invalidation spot checks.

Run: `Layer3_JcvPCA/.venv/bin/python -m pytest tests/test_analysis_config.py -q`

---

*G1.1 complete — pause before G2.*
