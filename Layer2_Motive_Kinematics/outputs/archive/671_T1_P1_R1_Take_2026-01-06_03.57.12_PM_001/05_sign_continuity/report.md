# Stage 05 — Global quaternion sign-continuity correction

Generated: 2026-06-19 13:55:28 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv`

## What was detected

- Quaternion groups processed: 51
- Total frames processed: 30604
- Total sign flips: 57080
- Max sign flips (any bone): 14270
- Bones with zero flips: 47
- Min consecutive dot observed: 0.06716906266199994
- Post-correction valid: True
- Stage 06 may proceed: True

## Assumptions

- Sign continuity uses consecutive dot-product sign test on SciPy-order quaternions.
- Correction multiplies q[t] by -1 when dot(q[t], q_corrected[t-1]) < 0.
- Post-correction validation requires consecutive dot >= -1e-12.
- Output table uses long format (one row per frame per bone) with flip_applied flag.
- Stage 05 corrects global quaternion signs only; it does not change represented rotations.
- Stage 05 does not interpolate missing data or repair failed Stage 04 QC data.
- Stage 05 does not perform anatomical validation.
- Stage 05 does not compute relative rotations.
- Stage 05 does not convert to rotation vectors or filter.
- Stage 05 does not make Layer 3 features ready.
- No quaternion normalization is applied; Stage 04-passed norms are preserved.

## Outputs written

- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/05_sign_continuity/report.md`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/05_sign_continuity/sign_continuity_summary.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/05_sign_continuity/sign_flips_by_bone.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/05_sign_continuity/sign_flip_frames.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/05_sign_continuity/global_quaternions_sign_continuous.parquet`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/05_sign_continuity/global_quaternions_sign_continuous.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/05_sign_continuity/assumptions_and_limitations.md`

## Warnings

- None

## Errors

- None

## Validation status

PASS — global sign continuity corrected and validated

## Next recommended action

Review sign-continuity summary and flip reports. Continue to Stage 06 only if post_correction_valid is true and stage06_may_proceed is true.
