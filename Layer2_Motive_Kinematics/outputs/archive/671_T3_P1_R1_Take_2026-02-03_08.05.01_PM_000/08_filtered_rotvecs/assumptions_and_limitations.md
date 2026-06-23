# Stage 08 assumptions and limitations

## Purpose

Apply zero-phase Butterworth low-pass filtering to Stage 07 rotation-vector components while preserving QC lineage and producing an analysis-clean mask.

## Filtering parameters

- Filter type: Butterworth (SOS), scipy.signal.sosfiltfilt
- Cutoff: 10.0 Hz
- Order: 4
- Sampling rate: 120.00480019200238 Hz (from Stage 03 session manifest)
- Cutoff validation: cutoff < 0.45 × sampling_rate
- Jump context window: ±30 frames around Stage 07 jump warning/fail transitions

## Jump / context policy (V1)

- **No interpolation** of Stage 07 jump-fail rows or jump-context windows.
- Jump event frames are identified from row-level `stage07_jump_magnitude_rad` exceeding the Stage 07 jump-warning threshold on frame-to-frame transitions.
- Rows inside the jump context window are marked `stage08_analysis_eligible = false` with `stage08_mask_reason = stage07_jump_context`.
- Native filtered columns may retain values inside jump context; analysis-clean columns are set to NaN.

## Output columns

- Native archive: `rx_filtered_native`, `ry_filtered_native`, `rz_filtered_native`, `rotvec_norm_filtered_native`
- Analysis-clean: `rx_filtered_analysis`, `ry_filtered_analysis`, `rz_filtered_analysis`, `rotvec_norm_filtered_analysis`
- Raw preserved: `rx_raw`, `ry_raw`, `rz_raw`, `rotvec_norm_raw`

## Explicit limitations

- Stage 08 V1 does not interpolate or repair Stage 07 jump frames.
- Native filtered values may exist inside jump-context windows but are not analysis-clean.
- Analysis-clean columns are NaN/masked in jump-context windows.
- Final inclusion/exclusion remains deferred to post–Layer 2 / pre–Layer 3 feature selection.
- Stage 08 does not implement Layer 3.
- Stage 08 does not overwrite Stage 07 outputs or modify Stage 07 thresholds.
- Isolated Stage 07 jump failures do not remove entire links or sessions from filtering.
