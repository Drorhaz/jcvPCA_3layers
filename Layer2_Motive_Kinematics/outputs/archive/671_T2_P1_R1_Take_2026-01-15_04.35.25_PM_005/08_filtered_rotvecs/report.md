# Stage 08 — Filtered relative rotation vectors (V1, no interpolation)

Generated: 2026-06-19 15:30:06 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T2_P1_R1_Take 2026-01-15 04.35.25 PM_005.csv`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/07_rotation_vectors/relative_rotation_vectors.parquet`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/03_frame_time_validation/frame_time_summary.csv`

## What was detected

- Links processed: 50
- Links pass / jump-context masked / excluded / blocked / review: 16 / 13 / 32 / 0 / 2
- Total Stage 07 jump event frames: 13
- Total jump-context frames (may overlap across events): 793
- Total analysis-eligible frames: 485574
- Interpolation applied: False
- Native filtered columns retain values where filtering succeeded.
- Analysis-clean columns are NaN outside eligibility (jump context, excluded, blocked, review).

## Assumptions

- Butterworth sosfiltfilt: cutoff=10.0 Hz, order=4
- Sampling rate from Stage 03: 120.00480019200238 Hz
- Jump context window: ±30 frames
- Stage 08 V1 does not interpolate Stage 07 jump frames.
- Stage 08 V1 does not interpolate or repair Stage 07 jump frames.
- Native filtered values may exist inside jump-context windows but are not analysis-clean.
- Analysis-clean columns are NaN/masked in jump-context windows.
- Final inclusion/exclusion remains deferred to post–Layer 2 / pre–Layer 3 feature selection.
- Stage 08 does not implement Layer 3.
- Stage 08 does not overwrite Stage 07 outputs or modify Stage 07 thresholds.
- Isolated Stage 07 jump failures do not remove entire links or sessions from filtering.

## Outputs written

- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/08_filtered_rotvecs/report.md`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/08_filtered_rotvecs/filtered_relative_rotation_vectors.parquet`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/08_filtered_rotvecs/filtered_relative_rotation_vectors.csv`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/08_filtered_rotvecs/filtering_summary_by_link.csv`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/08_filtered_rotvecs/stage08_jump_context_report.csv`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/08_filtered_rotvecs/filter_diagnostics.csv`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/08_filtered_rotvecs/assumptions_and_limitations.md`

## Warnings

- None

## Errors

- None

## Validation status

PASS WITH REVIEW — filtering completed; review link summaries

## Next recommended action

Review filtering_summary_by_link.csv and stage08_jump_context_report.csv. Use analysis-clean columns for downstream feature work; native columns are archival. Final Layer 2 export/manifest can be prepared next; Layer 3 remains out of scope.

## Stage 08 V1 policy reminder

- Stage 08 V1 does **not** interpolate or repair Stage 07 jump frames.
- Native filtered values may exist inside jump-context windows but are **not** analysis-clean.
- Analysis-clean columns are NaN/masked in jump-context windows.
- Final inclusion/exclusion remains deferred to post–Layer 2 / pre–Layer 3 feature selection.
- Stage 08 does not implement Layer 3.

## Jump context summary

- Jump event frames (total across links): **13**
- Jump-context frames (total, overlapping): **793**
- Links with jump context: **13**
