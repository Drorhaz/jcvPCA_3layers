# Stage 04 — Quaternion norm / missingness / validity QC

Generated: 2026-06-23 15:18:59 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T2_P1_R2_Take 2026-01-15 04.35.25 PM_009.csv`

## What was detected

- Quaternion groups checked: 51
- Groups pass/warning/fail: 51/0/0
- Total zero-norm quaternions: 0
- Total near-zero-norm quaternions: 0
- Total non-finite quaternion rows: 0
- Max abs norm error observed: 9.996110001964098e-07
- Longest invalid gap observed: 0 frame(s)
- file_qc_status: pass
- Stage 05 may proceed: True

## Assumptions

- Bone Rotation groups are loaded using Stage 00 column detection (X/Y/Z/W per bone).
- Quaternion norms are computed on complete finite XYZW rows only; no normalization applied.
- Provisional thresholds: pass norm error <= 0.001, warning <= 0.01, near-zero norm < 1e-08.
- Stage 04 validates numeric quaternion quality only.
- Stage 04 does not validate anatomical correctness.
- Stage 04 does not perform sign-continuity.
- Stage 04 does not compute relative rotations.
- Stage 04 does not filter.
- Stage 04 does not make Layer 3 features ready.
- No quaternion normalization, interpolation, or silent repair is performed in Stage 04.
- v5 spec Stage 04 also describes normalization/mitigation outputs; this milestone implements QC/reporting only per approved plan.

## Outputs written

- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/04_quaternion_qc/report.md`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/04_quaternion_qc/quaternion_qc_summary.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/04_quaternion_qc/quaternion_qc_by_bone.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/04_quaternion_qc/quaternion_invalid_gap_report.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/04_quaternion_qc/assumptions_and_limitations.md`

## Warnings

- None

## Errors

- None

## Validation status

PASS — quaternion numeric QC validated

## Next recommended action

Review quaternion QC summary, per-bone table, and invalid-gap report. Continue to Stage 05 only if file_qc_status is pass or warning is accepted and stage05_may_proceed is true.
