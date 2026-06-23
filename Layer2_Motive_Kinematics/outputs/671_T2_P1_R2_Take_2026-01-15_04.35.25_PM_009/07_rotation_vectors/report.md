# Stage 07 — Rotation-vector log-map conversion and diagnostics

Generated: 2026-06-23 17:29:43 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T2_P1_R2_Take 2026-01-15 04.35.25 PM_009.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/06_relative_quaternions/relative_quaternions.parquet`

## What was detected

- Stage 06 input format: Loaded Stage 06 relative quaternions from parquet; parquet is primary deliverable
- Links processed: 50
- Core / review / excluded links: 16/2/32
- Max rotvec norm (core / all): 2.66323 / 2.66323 rad
- Max frame-to-frame jump (core / all): 0.340899 / 0.398582 rad
- Core warnings/failures: 0/0
- Review warnings/failures: 0/0
- Excluded warnings/failures: 0/0
- Compact signal columns: 25
- Stage 08 may proceed: True

## Assumptions

- Rotation vector conversion: scipy.spatial.transform.Rotation.from_quat([qx, qy, qz, qw]).as_rotvec()
- Near-π statistic threshold: 3.04159 rad
- Branch-cut warning/fail: > 2.98451 / ≥ 3.14159 rad
- Jump warning/fail: > 0.5 / > 1.0 rad
- Loaded Stage 06 relative quaternions from parquet; parquet is primary deliverable
- Stage 07 uses the log-map / rotation-vector representation (SciPy Rotation.as_rotvec).
- Stage 07 performs branch-cut and frame-to-frame jump diagnostics only.
- Stage 07 does not filter.
- Stage 07 does not finalize analysis features.
- Stage 07 does not resolve skeleton-version mismatch.
- Stage 07 does not make Layer 3 ready.
- Core and excluded link diagnostics are interpreted separately.
- Jump/branch-cut failures on core links are flagged for localized Stage 08 masking.
- Branch-cut/jump diagnostics are required before Stage 08 filtering.
- Provisional joint selection from Stage 01 / pre–Stage 07 gate is preserved but not frozen.

## Outputs written

- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/07_rotation_vectors/report.md`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/07_rotation_vectors/relative_rotation_vectors.parquet`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/07_rotation_vectors/relative_rotation_vectors.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/07_rotation_vectors/qc_link_manifest.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/07_rotation_vectors/qc_session_manifest.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/07_rotation_vectors/rotvec_summary_by_link.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/07_rotation_vectors/branch_cut_report.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/07_rotation_vectors/rotvec_jump_report.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/07_rotation_vectors/assumptions_and_limitations.md`

## Warnings

- None

## Errors

- None

## Validation status

PASS — rotation vectors computed; core link branch-cut and jump diagnostics OK

## Next recommended action

Review rotvec_summary_by_link.csv, branch_cut_report.csv, and rotvec_jump_report.csv. Core and excluded diagnostics are summarized separately. Continue to Stage 08 filtering only if stage08_may_proceed is true and human review accepts diagnostics. Stage 07 does not filter or finalize analysis features.

## Diagnostic summaries by link group

### Core candidate links

- Links: **16**
- Warnings: **0**
- Failures: **0**
- Max rotvec norm: **2.66323 rad**
- Max frame-to-frame jump: **0.340899 rad**


### Review / provisional trunk-root links

- Links: **2**
- Warnings: **0**
- Failures: **0**
- Max rotvec norm: **0.442635 rad**
- Max frame-to-frame jump: **0.0367739 rad**


### Excluded distal / finger / toe links

- Links: **32**
- Warnings: **0**
- Failures: **0**
- Max rotvec norm: **2.04 rad**
- Max frame-to-frame jump: **0.398582 rad**


## Stage 07 scope reminder

- Stage 07 uses the log-map / rotation-vector representation.
- Stage 07 does not filter, finalize analysis features, resolve skeleton-version mismatch, or make Layer 3 ready.
- Branch-cut/jump diagnostics are required before filtering.
