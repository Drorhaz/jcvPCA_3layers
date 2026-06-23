# Stage 02 — Quaternion component-order / SciPy compatibility

Generated: 2026-06-19 13:30:53 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv`

## What was detected

- Rotation Type: Quaternion
- Coordinate Space: Global
- Bone Rotation quaternion groups checked: 55
- Groups passing constructability: 55
- Groups failing constructability: 0
- Groups with non-finite rows: 0
- Selected SciPy component order: x,y,z,w
- Stage 03 may proceed for this file: True

## Assumptions

- Motive Bone Rotation labels X/Y/Z/W map to SciPy [x,y,z,w] by label semantics.
- Constructability uses scipy.spatial.transform.Rotation.from_quat on finite numeric rows.
- Alternative [w,x,y,z] comparison is diagnostic only and not used for selection.
- This stage validates component-order / SciPy library compatibility only.
- Motive Bone Rotation columns are labeled X, Y, Z, W.
- SciPy Rotation.from_quat expects [x, y, z, w] (scalar-last).
- Intended mapping: Motive X,Y,Z,W -> SciPy x,y,z,w.
- This does not validate quaternion norms, temporal continuity, gaps, or relative joint rotations.
- Alternative-order constructability ([w,x,y,z] fed to SciPy) is reported for comparison only; numerical constructability of both orders does not prove semantic correctness.
- This does not validate global quaternion quality or biomechanical correctness.

## Outputs written

- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/02_component_order/report.md`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/02_component_order/component_order_summary.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/02_component_order/component_order_by_bone.csv`
- `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005/02_component_order/assumptions_and_limitations.md`

## Warnings

- None

## Errors

- None

## Validation status

PASS — component-order / SciPy compatibility validated for representative file

## Next recommended action

Review component-order report and assumptions. Continue to Stage 03 only if stage03_may_proceed_for_file is true and human reviewer accepts the component-order decision.
