# Stage 07 — Rotation-vector log-map conversion and diagnostics

Generated: 2026-06-19 15:06:38 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/06_relative_quaternions/relative_quaternions.parquet`

## What was detected

- Stage 06 input format: Loaded Stage 06 relative quaternions from parquet; parquet is primary deliverable
- Links processed: 50
- Core / review / excluded links: 16/2/32
- Max rotvec norm (core / all): 2.68098 / 2.68098 rad
- Max frame-to-frame jump (core / all): 1.47401 / 2.07034 rad
- Core warnings/failures: 2/1
- Review warnings/failures: 0/0
- Excluded warnings/failures: 8/8
- Compact signal columns: 25
- Stage 08 may proceed: False

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

- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/07_rotation_vectors/report.md`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/07_rotation_vectors/relative_rotation_vectors.parquet`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/07_rotation_vectors/relative_rotation_vectors.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/07_rotation_vectors/qc_link_manifest.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/07_rotation_vectors/qc_session_manifest.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/07_rotation_vectors/rotvec_summary_by_link.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/07_rotation_vectors/branch_cut_report.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/07_rotation_vectors/rotvec_jump_report.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/07_rotation_vectors/assumptions_and_limitations.md`

## Warnings

- J005 (LUArm→LFArm): jump warning (max jump=0.673624 rad)
- J029 (RUArm→RFArm): jump warning (max jump=0.555333 rad)
- J008 (LHand→LIndex1) [excluded]: jump fail (max jump=1.73016 rad; non-blocking unless core)
- J009 (LIndex1→LIndex2) [excluded]: jump fail (max jump=2.07034 rad; non-blocking unless core)
- J010 (LIndex2→LIndex3) [excluded]: jump warning (max jump=0.862642 rad)
- J011 (LHand→LMiddle1) [excluded]: jump fail (max jump=1.66744 rad; non-blocking unless core)
- J012 (LMiddle1→LMiddle2) [excluded]: jump fail (max jump=1.97838 rad; non-blocking unless core)
- J013 (LMiddle2→LMiddle3) [excluded]: jump warning (max jump=0.824323 rad)
- J014 (LHand→LPinky1) [excluded]: jump fail (max jump=1.60084 rad; non-blocking unless core)
- J015 (LPinky1→LPinky2) [excluded]: jump fail (max jump=1.795 rad; non-blocking unless core)
- J016 (LPinky2→LPinky3) [excluded]: jump warning (max jump=0.747917 rad)
- J017 (LHand→LRing1) [excluded]: jump fail (max jump=1.62369 rad; non-blocking unless core)
- J018 (LRing1→LRing2) [excluded]: jump fail (max jump=1.88696 rad; non-blocking unless core)
- J019 (LRing2→LRing3) [excluded]: jump warning (max jump=0.786236 rad)
- J023 (LHand→LThumb1) [excluded]: jump warning (max jump=0.823032 rad)
- J024 (LThumb1→LThumb2) [excluded]: jump warning (max jump=0.630874 rad)
- J025 (LThumb2→LThumb3) [excluded]: jump warning (max jump=0.630874 rad)
- J032 (RHand→RIndex1) [excluded]: jump warning (max jump=0.524099 rad)

## Errors

- J007 (LFArm→LHand): jump fail (max jump=1.47401 rad)

## Validation status

FAIL — core link rotation-vector diagnostics failed (see branch_cut_report and rotvec_jump_report)

## Next recommended action

Review rotvec_summary_by_link.csv, branch_cut_report.csv, and rotvec_jump_report.csv. Core and excluded diagnostics are summarized separately. Continue to Stage 08 filtering only if stage08_may_proceed is true and human review accepts diagnostics. Stage 07 does not filter or finalize analysis features.

## Diagnostic summaries by link group

### Core candidate links

- Links: **16**
- Warnings: **2**
- Failures: **1**
- Max rotvec norm: **2.68098 rad**
- Max frame-to-frame jump: **1.47401 rad**

- `J005` LUArm→LFArm: branch_cut=pass, jump=warning, max_norm=2.681, max_jump=0.6736, near_pi=0, large_jumps=1
- `J007` LFArm→LHand: branch_cut=pass, jump=fail, max_norm=1.611, max_jump=1.474, near_pi=0, large_jumps=1
- `J029` RUArm→RFArm: branch_cut=pass, jump=warning, max_norm=2.439, max_jump=0.5553, near_pi=0, large_jumps=1

### Review / provisional trunk-root links

- Links: **2**
- Warnings: **0**
- Failures: **0**
- Max rotvec norm: **0.401428 rad**
- Max frame-to-frame jump: **0.0420663 rad**


### Excluded distal / finger / toe links

- Links: **32**
- Warnings: **8**
- Failures: **8**
- Max rotvec norm: **2.04 rad**
- Max frame-to-frame jump: **2.07034 rad**

- `J008` LHand→LIndex1: branch_cut=pass, jump=fail, max_norm=1.752, max_jump=1.73, near_pi=0, large_jumps=1
- `J009` LIndex1→LIndex2: branch_cut=pass, jump=fail, max_norm=2.04, max_jump=2.07, near_pi=0, large_jumps=1
- `J010` LIndex2→LIndex3: branch_cut=pass, jump=warning, max_norm=0.85, max_jump=0.8626, near_pi=0, large_jumps=1
- `J011` LHand→LMiddle1: branch_cut=pass, jump=fail, max_norm=1.754, max_jump=1.667, near_pi=0, large_jumps=1
- `J012` LMiddle1→LMiddle2: branch_cut=pass, jump=fail, max_norm=2.04, max_jump=1.978, near_pi=0, large_jumps=1
- `J013` LMiddle2→LMiddle3: branch_cut=pass, jump=warning, max_norm=0.85, max_jump=0.8243, near_pi=0, large_jumps=1
- `J014` LHand→LPinky1: branch_cut=pass, jump=fail, max_norm=1.834, max_jump=1.601, near_pi=0, large_jumps=1
- `J015` LPinky1→LPinky2: branch_cut=pass, jump=fail, max_norm=2.04, max_jump=1.795, near_pi=0, large_jumps=1
- `J016` LPinky2→LPinky3: branch_cut=pass, jump=warning, max_norm=0.85, max_jump=0.7479, near_pi=0, large_jumps=1
- `J017` LHand→LRing1: branch_cut=pass, jump=fail, max_norm=1.777, max_jump=1.624, near_pi=0, large_jumps=1
- `J018` LRing1→LRing2: branch_cut=pass, jump=fail, max_norm=2.04, max_jump=1.887, near_pi=0, large_jumps=1
- `J019` LRing2→LRing3: branch_cut=pass, jump=warning, max_norm=0.85, max_jump=0.7862, near_pi=0, large_jumps=1
- `J023` LHand→LThumb1: branch_cut=pass, jump=warning, max_norm=1.44, max_jump=0.823, near_pi=0, large_jumps=1
- `J024` LThumb1→LThumb2: branch_cut=pass, jump=warning, max_norm=1.204, max_jump=0.6309, near_pi=0, large_jumps=1
- `J025` LThumb2→LThumb3: branch_cut=pass, jump=warning, max_norm=0.5927, max_jump=0.6309, near_pi=0, large_jumps=1
- `J032` RHand→RIndex1: branch_cut=pass, jump=warning, max_norm=1.053, max_jump=0.5241, near_pi=0, large_jumps=1

## Stage 07 scope reminder

- Stage 07 uses the log-map / rotation-vector representation.
- Stage 07 does not filter, finalize analysis features, resolve skeleton-version mismatch, or make Layer 3 ready.
- Branch-cut/jump diagnostics are required before filtering.
