# Stage 07 — Rotation-vector log-map conversion and diagnostics

Generated: 2026-06-19 15:09:16 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/06_relative_quaternions/relative_quaternions.parquet`

## What was detected

- Stage 06 input format: Loaded Stage 06 relative quaternions from parquet; parquet is primary deliverable
- Links processed: 54
- Core / review / excluded links: 16/6/32
- Max rotvec norm (core / all): 2.64534 / 2.64534 rad
- Max frame-to-frame jump (core / all): 0.818209 / 0.818209 rad
- Core warnings/failures: 1/0
- Review warnings/failures: 0/0
- Excluded warnings/failures: 7/0
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
- Branch-cut/jump diagnostics are required before Stage 08 filtering.
- Provisional joint selection from Stage 01 / pre–Stage 07 gate is preserved but not frozen.

## Outputs written

- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/07_rotation_vectors/report.md`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/07_rotation_vectors/relative_rotation_vectors.parquet`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/07_rotation_vectors/relative_rotation_vectors.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/07_rotation_vectors/qc_link_manifest.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/07_rotation_vectors/qc_session_manifest.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/07_rotation_vectors/rotvec_summary_by_link.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/07_rotation_vectors/branch_cut_report.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/07_rotation_vectors/rotvec_jump_report.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/07_rotation_vectors/assumptions_and_limitations.md`

## Warnings

- J006 (LFArm→LHand): jump warning (max jump=0.818209 rad)
- J007 (LHand→LIndex1) [excluded]: jump warning (max jump=0.648009 rad)
- J008 (LIndex1→LIndex2) [excluded]: jump warning (max jump=0.768003 rad)
- J011 (LMiddle1→LMiddle2) [excluded]: jump warning (max jump=0.511489 rad)
- J013 (LHand→LPinky1) [excluded]: jump warning (max jump=0.676143 rad)
- J022 (LHand→LThumb1) [excluded]: jump warning (max jump=0.57362 rad)
- J032 (RHand→RIndex1) [excluded]: jump warning (max jump=0.568304 rad)
- J033 (RIndex1→RIndex2) [excluded]: jump warning (max jump=0.655098 rad)

## Errors

- None

## Validation status

PASS — rotation vectors computed; core link branch-cut and jump diagnostics OK

## Next recommended action

Review rotvec_summary_by_link.csv, branch_cut_report.csv, and rotvec_jump_report.csv. Core and excluded diagnostics are summarized separately. Continue to Stage 08 filtering only if stage08_may_proceed is true and human review accepts diagnostics. Stage 07 does not filter or finalize analysis features.

## Diagnostic summaries by link group

### Core candidate links

- Links: **16**
- Warnings: **1**
- Failures: **0**
- Max rotvec norm: **2.64534 rad**
- Max frame-to-frame jump: **0.818209 rad**

- `J006` LFArm→LHand: branch_cut=pass, jump=warning, max_norm=2.112, max_jump=0.8182, near_pi=0, large_jumps=1

### Review / provisional trunk-root links

- Links: **6**
- Warnings: **0**
- Failures: **0**
- Max rotvec norm: **0.43959 rad**
- Max frame-to-frame jump: **0.0308478 rad**


### Excluded distal / finger / toe links

- Links: **32**
- Warnings: **7**
- Failures: **0**
- Max rotvec norm: **2.04 rad**
- Max frame-to-frame jump: **0.768003 rad**

- `J007` LHand→LIndex1: branch_cut=pass, jump=warning, max_norm=1.752, max_jump=0.648, near_pi=0, large_jumps=1
- `J008` LIndex1→LIndex2: branch_cut=pass, jump=warning, max_norm=2.04, max_jump=0.768, near_pi=0, large_jumps=1
- `J011` LMiddle1→LMiddle2: branch_cut=pass, jump=warning, max_norm=1.828, max_jump=0.5115, near_pi=0, large_jumps=1
- `J013` LHand→LPinky1: branch_cut=pass, jump=warning, max_norm=1.214, max_jump=0.6761, near_pi=0, large_jumps=2
- `J022` LHand→LThumb1: branch_cut=pass, jump=warning, max_norm=1.768, max_jump=0.5736, near_pi=0, large_jumps=1
- `J032` RHand→RIndex1: branch_cut=pass, jump=warning, max_norm=0.9895, max_jump=0.5683, near_pi=0, large_jumps=1
- `J033` RIndex1→RIndex2: branch_cut=pass, jump=warning, max_norm=1.064, max_jump=0.6551, near_pi=0, large_jumps=1

## Stage 07 scope reminder

- Stage 07 uses the log-map / rotation-vector representation.
- Stage 07 does not filter, finalize analysis features, resolve skeleton-version mismatch, or make Layer 3 ready.
- Branch-cut/jump diagnostics are required before filtering.
