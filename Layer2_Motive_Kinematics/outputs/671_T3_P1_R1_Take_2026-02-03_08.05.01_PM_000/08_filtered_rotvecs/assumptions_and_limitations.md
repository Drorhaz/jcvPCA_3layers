# Stage 08 assumptions and limitations

## Purpose

Apply zero-phase Butterworth low-pass filtering to Stage 07 rotation-vector components while preserving QC lineage and producing analysis eligibility flags.

## Filtering parameters

- Filter type: Butterworth (SOS), scipy.signal.sosfiltfilt
- Cutoff: 10.0 Hz
- Order: 4
- Sampling rate: 120.00480019200238 Hz (from Stage 03 session manifest)
- Cutoff validation: cutoff < 0.45 × sampling_rate
- QC context window: ±30 frames (jumps and branch-cut events)

## Stage 08 QC policy (V1)

| Stage 07 outcome | Stage 08 policy | Stage 08 flagging |
|---|---|---|
| Jump warning or fail | `allow_filter_with_warning` | Jump event ± context → `stage07_jump_context` |
| Branch-cut warning or fail | `allow_filter_with_warning` | `rotvec_norm` > 2.98451 rad ± context → `stage07_branch_cut_context` |
| Quaternion / sign / reconstruction fail | `block_filter` | Whole link flagged |

## Mask reasons

- `stage07_jump_context`: within ±30 frames of a Stage 07 jump event (frame-to-frame magnitude > 0.5 rad; warning and fail levels).
- `stage07_branch_cut_context`: within ±30 frames of a frame where `rotvec_norm` exceeds the branch-cut warning threshold (2.98451 rad). Jump context takes priority when both apply.
- `blocked_needs_review`: whole-link block from pipeline-integrity QC only.

## Jump / branch-cut context rules

- **No interpolation** of flagged rows.
- Jump events: row-level `stage07_jump_magnitude_rad` on frame-to-frame transitions.
- Branch-cut events: row-level `rotvec_norm` above branch-cut warning threshold.
- Rows inside a context window: `stage08_analysis_eligible = false`; filtered numeric values are preserved and the row is flagged for downstream review.
- NaNs in analysis columns appear only when filtering genuinely failed (`filter_not_applied`) or source rotvec components were non-finite.
- Stage 07 link-level `fail` labels are preserved for reporting; they do not imply whole-link analysis exclusion in Stage 08.

## Output columns

- Native archive: `rx_filtered_native`, `ry_filtered_native`, `rz_filtered_native`, `rotvec_norm_filtered_native`
- Analysis export: `rx_filtered_analysis`, `ry_filtered_analysis`, `rz_filtered_analysis`, `rotvec_norm_filtered_analysis` (numeric when filtering succeeded; use flags for QC)
- Raw preserved: `rx_raw`, `ry_raw`, `rz_raw`, `rotvec_norm_raw`
- Jump QC: `stage08_stage07_jump_frame`, `stage08_within_jump_context_window`, `stage08_distance_to_nearest_stage07_jump_frame`
- Branch-cut QC: `stage08_branch_cut_event_frame`, `stage08_within_branch_cut_context_window`, `stage08_distance_to_nearest_branch_cut_frame`

## Explicit limitations

- Stage 08 V1 does not interpolate or repair Stage 07 jump frames.
- Stage 07 jump and branch-cut failures use localized context flagging, not whole-link blocks.
- Native and analysis filtered columns are numeric wherever filtering succeeded.
- QC/risk rows are flagged via stage08_analysis_eligible and stage08_mask_reason; analysis columns are not NaN-blanked for QC alone.
- Final inclusion/exclusion remains deferred to post–Layer 2 / pre–Layer 3 feature selection.
- Stage 08 does not implement Layer 3.
- Stage 08 does not overwrite Stage 07 outputs or modify Stage 07 thresholds.
- Pipeline-integrity failures (quaternion/sign/reconstruction) still block entire links.
