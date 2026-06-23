# Stage 07 — Rotation-vector log-map conversion and diagnostics

Generated: 2026-06-19 15:08:41 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T3_P1_R1_Take 2026-02-03 08.05.01 PM_000.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/06_relative_quaternions/relative_quaternions.parquet`

## What was detected

- Stage 06 input format: Loaded Stage 06 relative quaternions from parquet; parquet is primary deliverable
- Links processed: 54
- Core / review / excluded links: 16/6/32
- Max rotvec norm (core / all): 2.69069 / 2.69069 rad
- Max frame-to-frame jump (core / all): 1.73994 / 2.00682 rad
- Core warnings/failures: 0/3
- Review warnings/failures: 0/0
- Excluded warnings/failures: 7/7
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

- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/07_rotation_vectors/report.md`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/07_rotation_vectors/relative_rotation_vectors.parquet`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/07_rotation_vectors/relative_rotation_vectors.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/07_rotation_vectors/qc_link_manifest.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/07_rotation_vectors/qc_session_manifest.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/07_rotation_vectors/rotvec_summary_by_link.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/07_rotation_vectors/branch_cut_report.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/07_rotation_vectors/rotvec_jump_report.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/07_rotation_vectors/assumptions_and_limitations.md`

## Warnings

- J007 (LHand→LIndex1) [excluded]: jump fail (max jump=1.68196 rad; non-blocking unless core)
- J008 (LIndex1→LIndex2) [excluded]: jump fail (max jump=2.00682 rad; non-blocking unless core)
- J009 (LIndex2→LIndex3) [excluded]: jump warning (max jump=0.836173 rad)
- J010 (LHand→LMiddle1) [excluded]: jump fail (max jump=1.08178 rad; non-blocking unless core)
- J011 (LMiddle1→LMiddle2) [excluded]: jump fail (max jump=1.28576 rad; non-blocking unless core)
- J012 (LMiddle2→LMiddle3) [excluded]: jump warning (max jump=0.535733 rad)
- J017 (LRing1→LRing2) [excluded]: jump warning (max jump=0.569015 rad)
- J022 (LHand→LThumb1) [excluded]: jump warning (max jump=0.972914 rad)
- J036 (RMiddle1→RMiddle2) [excluded]: jump warning (max jump=0.536788 rad)
- J038 (RHand→RPinky1) [excluded]: jump fail (max jump=1.37156 rad; non-blocking unless core)
- J039 (RPinky1→RPinky2) [excluded]: jump fail (max jump=1.61144 rad; non-blocking unless core)
- J040 (RPinky2→RPinky3) [excluded]: jump warning (max jump=0.671435 rad)
- J041 (RHand→RRing1) [excluded]: jump warning (max jump=0.900616 rad)
- J042 (RRing1→RRing2) [excluded]: jump fail (max jump=1.0725 rad; non-blocking unless core)

## Errors

- J004 (LUArm→LFArm): jump fail (max jump=1.3332 rad)
- J006 (LFArm→LHand): jump fail (max jump=1.44974 rad)
- J031 (RFArm→RHand): jump fail (max jump=1.73994 rad)

## Validation status

FAIL — core link rotation-vector diagnostics failed (see branch_cut_report and rotvec_jump_report)

## Next recommended action

Review rotvec_summary_by_link.csv, branch_cut_report.csv, and rotvec_jump_report.csv. Core and excluded diagnostics are summarized separately. Continue to Stage 08 filtering only if stage08_may_proceed is true and human review accepts diagnostics. Stage 07 does not filter or finalize analysis features.

## Diagnostic summaries by link group

### Core candidate links

- Links: **16**
- Warnings: **0**
- Failures: **3**
- Max rotvec norm: **2.69069 rad**
- Max frame-to-frame jump: **1.73994 rad**

- `J004` LUArm→LFArm: branch_cut=pass, jump=fail, max_norm=2.691, max_jump=1.333, near_pi=0, large_jumps=1
- `J006` LFArm→LHand: branch_cut=pass, jump=fail, max_norm=2.004, max_jump=1.45, near_pi=0, large_jumps=1
- `J031` RFArm→RHand: branch_cut=pass, jump=fail, max_norm=2.065, max_jump=1.74, near_pi=0, large_jumps=2

### Review / provisional trunk-root links

- Links: **6**
- Warnings: **0**
- Failures: **0**
- Max rotvec norm: **0.443071 rad**
- Max frame-to-frame jump: **0.171813 rad**


### Excluded distal / finger / toe links

- Links: **32**
- Warnings: **7**
- Failures: **7**
- Max rotvec norm: **2.04 rad**
- Max frame-to-frame jump: **2.00682 rad**

- `J007` LHand→LIndex1: branch_cut=pass, jump=fail, max_norm=1.748, max_jump=1.682, near_pi=0, large_jumps=2
- `J008` LIndex1→LIndex2: branch_cut=pass, jump=fail, max_norm=2.04, max_jump=2.007, near_pi=0, large_jumps=2
- `J009` LIndex2→LIndex3: branch_cut=pass, jump=warning, max_norm=0.85, max_jump=0.8362, near_pi=0, large_jumps=1
- `J010` LHand→LMiddle1: branch_cut=pass, jump=fail, max_norm=1.613, max_jump=1.082, near_pi=0, large_jumps=1
- `J011` LMiddle1→LMiddle2: branch_cut=pass, jump=fail, max_norm=1.919, max_jump=1.286, near_pi=0, large_jumps=2
- `J012` LMiddle2→LMiddle3: branch_cut=pass, jump=warning, max_norm=0.7995, max_jump=0.5357, near_pi=0, large_jumps=1
- `J017` LRing1→LRing2: branch_cut=pass, jump=warning, max_norm=1.979, max_jump=0.569, near_pi=0, large_jumps=1
- `J022` LHand→LThumb1: branch_cut=pass, jump=warning, max_norm=1.711, max_jump=0.9729, near_pi=0, large_jumps=1
- `J036` RMiddle1→RMiddle2: branch_cut=pass, jump=warning, max_norm=1.423, max_jump=0.5368, near_pi=0, large_jumps=1
- `J038` RHand→RPinky1: branch_cut=pass, jump=fail, max_norm=1.733, max_jump=1.372, near_pi=0, large_jumps=2
- `J039` RPinky1→RPinky2: branch_cut=pass, jump=fail, max_norm=2.04, max_jump=1.611, near_pi=0, large_jumps=1
- `J040` RPinky2→RPinky3: branch_cut=pass, jump=warning, max_norm=0.85, max_jump=0.6714, near_pi=0, large_jumps=1
- `J041` RHand→RRing1: branch_cut=pass, jump=warning, max_norm=1.443, max_jump=0.9006, near_pi=0, large_jumps=2
- `J042` RRing1→RRing2: branch_cut=pass, jump=fail, max_norm=1.731, max_jump=1.073, near_pi=0, large_jumps=1

## Stage 07 scope reminder

- Stage 07 uses the log-map / rotation-vector representation.
- Stage 07 does not filter, finalize analysis features, resolve skeleton-version mismatch, or make Layer 3 ready.
- Branch-cut/jump diagnostics are required before filtering.
