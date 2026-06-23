# Stage 08 — Filtered relative rotation vectors (V1, no interpolation)

Generated: 2026-06-23 17:36:12 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/07_rotation_vectors/relative_rotation_vectors.parquet`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/03_frame_time_validation/frame_time_summary.csv`

## What was detected

- Links processed: 54
- Links pass / QC-context flagged / excluded / blocked / review: 16 / 8 / 32 / 0 / 6
- Total Stage 07 jump event frames: 9
- Total jump-context frames (may overlap): 549
- Total branch-cut event frames: 0
- Total branch-cut context frames (may overlap): 0
- Total analysis-eligible frames: 502211
- Interpolation applied: False
- Native and analysis filtered columns retain numeric values where filtering succeeded.
- QC/risk rows are flagged via stage08_analysis_eligible and stage08_mask_reason; see stage08_flag_report.csv and stage08_ineligible_rows_report.csv.
- Computational NaNs (filter failure / non-finite input) are listed in stage08_nan_report.csv.

## Assumptions

- Butterworth sosfiltfilt: cutoff=10.0 Hz, order=4
- Sampling rate from Stage 03: 120.00480019200238 Hz
- QC context window: ±30 frames (jump and branch-cut events)
- Stage 08 V1 does not interpolate Stage 07 jump frames.
- Stage 08 V1 does not interpolate or repair Stage 07 jump frames.
- Stage 07 jump and branch-cut failures use localized context flagging, not whole-link blocks.
- Native and analysis filtered columns are numeric wherever filtering succeeded.
- QC/risk rows are flagged via stage08_analysis_eligible and stage08_mask_reason; analysis columns are not NaN-blanked for QC alone.
- Final inclusion/exclusion remains deferred to post–Layer 2 / pre–Layer 3 feature selection.
- Stage 08 does not implement Layer 3.
- Stage 08 does not overwrite Stage 07 outputs or modify Stage 07 thresholds.
- Pipeline-integrity failures (quaternion/sign/reconstruction) still block entire links.

## Outputs written

- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/08_filtered_rotvecs/report.md`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/08_filtered_rotvecs/filtered_relative_rotation_vectors.parquet`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/08_filtered_rotvecs/filtered_relative_rotation_vectors.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/08_filtered_rotvecs/filtering_summary_by_link.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/08_filtered_rotvecs/stage08_jump_context_report.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/08_filtered_rotvecs/stage08_branch_cut_context_report.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/08_filtered_rotvecs/stage08_flag_report.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/08_filtered_rotvecs/stage08_ineligible_rows_report.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/08_filtered_rotvecs/stage08_nan_report.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/08_filtered_rotvecs/filter_diagnostics.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/08_filtered_rotvecs/assumptions_and_limitations.md`

## Warnings

- None

## Errors

- None

## Validation status

PASS WITH REVIEW — filtering completed; review link summaries

## Next recommended action

Review filtering_summary_by_link.csv, stage08_jump_context_report.csv, stage08_flag_report.csv, and stage08_branch_cut_context_report.csv. Use rx/ry/rz_filtered_analysis for downstream numeric export and read flags separately for QC review. Final Layer 2 export/manifest can be prepared next; Layer 3 remains out of scope.

## Stage 08 V1 policy reminder

- Stage 08 V1 does **not** interpolate or repair Stage 07 jump frames.
- Jump and branch-cut Stage 07 failures are **localized** (event ± context window).
- Native and analysis filtered values are numeric wherever filtering succeeded.
- QC/risk rows are **flagged** (`stage08_analysis_eligible=false`); values are not NaN-blanked for QC alone.
- Whole-link blocks apply only to pipeline-integrity QC (`block_filter`).
- Final inclusion/exclusion remains deferred to post–Layer 2 / pre–Layer 3 feature selection.
- Stage 08 does not implement Layer 3.

## QC context summary

- Jump event frames (total across links): **9**
- Jump-context frames (total, overlapping): **549**
- Branch-cut event frames (total): **0**
- Branch-cut context frames (total, overlapping): **0**
- Links with QC context flagging: **8**
