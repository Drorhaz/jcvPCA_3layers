# Stage 03 — Frame and time validation

Generated: 2026-06-19 13:35:25 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv`

## What was detected

- Frame column: index=0, label='Frame'
- Time column: index=1, label='Time (Seconds)'
- Total rows: 31392
- First frame: 0
- Last frame: 31391
- Expected frame count (index span): 31392
- Observed unique frame count: 31392
- Missing frame count: 0
- Duplicate frame count: 0
- Non-monotonic frame transitions: 0
- First time (s): 0.0
- Last time (s): 261.591667
- Duration (s): 261.591667
- Median dt (s): 0.008333000000000368
- Inferred sampling rate (Hz): 120.00480019200238
- Metadata sampling rate (Hz): 120.0
- Rate difference (%): 0.004000160001981594
- Non-positive dt intervals: 0
- Unusually large dt intervals: 0
- Unusually small dt intervals: 0
- timing_status: pass
- Stage 04 may proceed: True

## Assumptions

- Frame and Time columns are loaded using Stage 00 header detection and flat column indices.
- Sampling rate is inferred as 1 / median positive dt from the Time column.
- Metadata sampling rate uses Export Frame Rate, falling back to Capture Frame Rate.
- Provisional thresholds: metadata tolerance 0.5%, large dt > 1.5× median, small dt < 0.5× median.
- This stage validates Frame and Time column structure only.
- No quaternion norm QC, gap repair, sign continuity, relative rotations, rotation vectors, filtering, or Layer 3 processing is performed.
- Missing frame indices are reported but not interpolated or repaired.
- Sampling rate is inferred from median positive dt; irregular intervals are flagged only.
- Joint sets are not frozen; this stage does not validate bone or joint selection.

## Outputs written

- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/03_frame_time_validation/report.md`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/03_frame_time_validation/frame_time_summary.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/03_frame_time_validation/frame_gap_report.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/03_frame_time_validation/time_step_report.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/03_frame_time_validation/assumptions_and_limitations.md`

## Warnings

- None

## Errors

- None

## Validation status

PASS — frame/time structure validated

## Next recommended action

Review frame/time summary, gap report, and time-step report. Continue to Stage 04 only if timing_status is pass or warning is accepted and stage04_may_proceed is true.
