# Stage 07 — Rotation-vector log-map conversion and diagnostics

Generated: 2026-06-19 15:07:37 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T2_P1_R1_Take 2026-01-15 04.35.25 PM_005.csv`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/06_relative_quaternions/relative_quaternions.parquet`

## What was detected

- Stage 06 input format: Loaded Stage 06 relative quaternions from parquet; parquet is primary deliverable
- Links processed: 50
- Core / review / excluded links: 16/2/32
- Max rotvec norm (core / all): 2.47439 / 2.47439 rad
- Max frame-to-frame jump (core / all): 0.718768 / 1.97181 rad
- Core warnings/failures: 2/0
- Review warnings/failures: 0/0
- Excluded warnings/failures: 5/6
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

- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/07_rotation_vectors/report.md`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/07_rotation_vectors/relative_rotation_vectors.parquet`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/07_rotation_vectors/relative_rotation_vectors.csv`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/07_rotation_vectors/qc_link_manifest.csv`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/07_rotation_vectors/qc_session_manifest.csv`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/07_rotation_vectors/rotvec_summary_by_link.csv`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/07_rotation_vectors/branch_cut_report.csv`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/07_rotation_vectors/rotvec_jump_report.csv`
- `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005/07_rotation_vectors/assumptions_and_limitations.md`

## Warnings

- J029 (RUArm→RFArm): jump warning (max jump=0.718768 rad)
- J031 (RFArm→RHand): jump warning (max jump=0.701735 rad)
- J023 (LHand→LThumb1) [excluded]: jump fail (max jump=1.14226 rad; non-blocking unless core)
- J032 (RHand→RIndex1) [excluded]: jump fail (max jump=1.65112 rad; non-blocking unless core)
- J033 (RIndex1→RIndex2) [excluded]: jump fail (max jump=1.97181 rad; non-blocking unless core)
- J034 (RIndex2→RIndex3) [excluded]: jump warning (max jump=0.821585 rad)
- J035 (RHand→RMiddle1) [excluded]: jump fail (max jump=1.26102 rad; non-blocking unless core)
- J036 (RMiddle1→RMiddle2) [excluded]: jump fail (max jump=1.51152 rad; non-blocking unless core)
- J037 (RMiddle2→RMiddle3) [excluded]: jump warning (max jump=0.629798 rad)
- J038 (RHand→RPinky1) [excluded]: jump warning (max jump=0.515744 rad)
- J039 (RPinky1→RPinky2) [excluded]: jump warning (max jump=0.593707 rad)
- J041 (RHand→RRing1) [excluded]: jump warning (max jump=0.879714 rad)
- J042 (RRing1→RRing2) [excluded]: jump fail (max jump=1.05399 rad; non-blocking unless core)

## Errors

- None

## Validation status

PASS — rotation vectors computed; core link branch-cut and jump diagnostics OK

## Next recommended action

Review rotvec_summary_by_link.csv, branch_cut_report.csv, and rotvec_jump_report.csv. Core and excluded diagnostics are summarized separately. Continue to Stage 08 filtering only if stage08_may_proceed is true and human review accepts diagnostics. Stage 07 does not filter or finalize analysis features.

## Diagnostic summaries by link group

### Core candidate links

- Links: **16**
- Warnings: **2**
- Failures: **0**
- Max rotvec norm: **2.47439 rad**
- Max frame-to-frame jump: **0.718768 rad**

- `J029` RUArm→RFArm: branch_cut=pass, jump=warning, max_norm=2.474, max_jump=0.7188, near_pi=0, large_jumps=1
- `J031` RFArm→RHand: branch_cut=pass, jump=warning, max_norm=1.88, max_jump=0.7017, near_pi=0, large_jumps=1

### Review / provisional trunk-root links

- Links: **2**
- Warnings: **0**
- Failures: **0**
- Max rotvec norm: **0.399879 rad**
- Max frame-to-frame jump: **0.0412427 rad**


### Excluded distal / finger / toe links

- Links: **32**
- Warnings: **5**
- Failures: **6**
- Max rotvec norm: **2.04 rad**
- Max frame-to-frame jump: **1.97181 rad**

- `J023` LHand→LThumb1: branch_cut=pass, jump=fail, max_norm=1.688, max_jump=1.142, near_pi=0, large_jumps=1
- `J032` RHand→RIndex1: branch_cut=pass, jump=fail, max_norm=1.752, max_jump=1.651, near_pi=0, large_jumps=1
- `J033` RIndex1→RIndex2: branch_cut=pass, jump=fail, max_norm=2.04, max_jump=1.972, near_pi=0, large_jumps=1
- `J034` RIndex2→RIndex3: branch_cut=pass, jump=warning, max_norm=0.85, max_jump=0.8216, near_pi=0, large_jumps=1
- `J035` RHand→RMiddle1: branch_cut=pass, jump=fail, max_norm=1.718, max_jump=1.261, near_pi=0, large_jumps=1
- `J036` RMiddle1→RMiddle2: branch_cut=pass, jump=fail, max_norm=2.04, max_jump=1.512, near_pi=0, large_jumps=1
- `J037` RMiddle2→RMiddle3: branch_cut=pass, jump=warning, max_norm=0.85, max_jump=0.6298, near_pi=0, large_jumps=1
- `J038` RHand→RPinky1: branch_cut=pass, jump=warning, max_norm=1.712, max_jump=0.5157, near_pi=0, large_jumps=1
- `J039` RPinky1→RPinky2: branch_cut=pass, jump=warning, max_norm=2.04, max_jump=0.5937, near_pi=0, large_jumps=1
- `J041` RHand→RRing1: branch_cut=pass, jump=warning, max_norm=1.722, max_jump=0.8797, near_pi=0, large_jumps=1
- `J042` RRing1→RRing2: branch_cut=pass, jump=fail, max_norm=2.04, max_jump=1.054, near_pi=0, large_jumps=1

## Stage 07 scope reminder

- Stage 07 uses the log-map / rotation-vector representation.
- Stage 07 does not filter, finalize analysis features, resolve skeleton-version mismatch, or make Layer 3 ready.
- Branch-cut/jump diagnostics are required before filtering.
