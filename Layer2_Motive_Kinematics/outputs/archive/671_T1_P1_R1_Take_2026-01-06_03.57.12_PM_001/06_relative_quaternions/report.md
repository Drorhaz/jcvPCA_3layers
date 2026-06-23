# Stage 06 — Relative quaternion computation and reconstruction validation

Generated: 2026-06-19 14:11:52 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv`

## What was detected

- Parent-child links processed: 50
- Parent-child links missing/skipped: 1
- Total frames: 30604
- Global max reconstruction error (deg): 4.1081380140780184e-14
- Links pass/warning/fail: 50/0/0
- Total raw relative sign flips: 4
- Total relative sign flips after correction: 0
- Relative sign continuity valid: True
- Stage 07 may proceed: True

## Assumptions

- Relative quaternion: q_rel = inv(q_parent) * q_child via SciPy Rotation.from_quat(parent).inv() * Rotation.from_quat(child). Reconstruction: q_child ≈ q_parent * q_rel via parent * relative.
- Reconstruction pass threshold: max error ≤ 1e-05 deg
- Reconstruction warning threshold: max error ≤ 0.001 deg
- When raw relative quaternion sequences contain sign discontinuities, Stage 06 applies the same consecutive dot-product correction as Stage 05 (flip q[t] when dot(q[t], q[t-1]) < 0) with explicit logging. This is a documented second-pass sign continuity on relative quaternions, required before Stage 07 log-map.
- Parent-child links derived from Stage 01 candidate_joint_map (not a fixed joint list).
- Stage 06 computes native relative quaternions from sign-continuous global quaternions.
- Stage 06 does not finalize analysis features.
- Stage 06 does not resolve skeleton-version mismatch.
- Stage 06 does not convert to rotation vectors.
- Stage 06 does not filter.
- Stage 06 does not make Layer 3 ready.
- Provisional joint selection from Stage 01 is preserved but not frozen.
- Root-anchor links are labeled and excluded from final-analysis status by default.

## Outputs written

- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/06_relative_quaternions/report.md`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/06_relative_quaternions/relative_quaternions.parquet`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/06_relative_quaternions/relative_quaternions.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/06_relative_quaternions/relative_quaternion_summary.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/06_relative_quaternions/reconstruction_validation_by_joint.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/06_relative_quaternions/relative_sign_continuity_report.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/06_relative_quaternions/assumptions_and_limitations.md`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/06_relative_quaternions/missing_parent_child_links.csv`

## Warnings

- J010: 1 raw relative sign flips corrected (documented second-pass sign continuity)
- J013: 1 raw relative sign flips corrected (documented second-pass sign continuity)
- J016: 1 raw relative sign flips corrected (documented second-pass sign continuity)
- J019: 1 raw relative sign flips corrected (documented second-pass sign continuity)

## Errors

- None

## Validation status

PASS — relative quaternions computed, reconstruction validated, relative sign continuity OK

## Next recommended action

Review relative quaternion summary and reconstruction validation. Continue to Stage 07 only if stage07_may_proceed is true. Stage 06 does not convert to rotation vectors, filter, or finalize features.
