# Stage 03 — Frame and time validation

Generated: 2026-06-23 15:18:32 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv`

## What was detected

- Frame column: index=0, label='Frame'
- Time column: index=1, label='Time (Seconds)'
- Total rows: 30604
- First frame: 0
- Last frame: 30603
- Expected frame count (index span): 30604
- Observed unique frame count: 30604
- Missing frame count: 0
- Duplicate frame count: 0
- Non-monotonic frame transitions: 0
- First time (s): 0.0
- Last time (s): 255.025
- Duration (s): 255.025
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

- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/03_frame_time_validation/report.md`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/03_frame_time_validation/frame_time_summary.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/03_frame_time_validation/frame_gap_report.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/03_frame_time_validation/time_step_report.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/03_frame_time_validation/assumptions_and_limitations.md`

## Warnings

- None

## Errors

- None

## Validation status

PASS — frame/time structure validated

## Next recommended action

Review frame/time summary, gap report, and time-step report. Continue to Stage 04 only if timing_status is pass or warning is accepted and stage04_may_proceed is true.
