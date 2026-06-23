# Stage 01 — Joint mapping and candidate joint detection

Generated: 2026-06-23 15:15:13 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T3_P1_R1_Take 2026-02-03 08.05.01 PM_000.csv`

## What was detected

- Bones detected: 55
- Candidate joints: 55
- Provisional auto-included: 17
- Excluded distal/toe/finger: 32
- Uncertain for review: 8
- Root/asset anchors: ['T3_671']
- Trunk chains: [['T3_671', 'Ab', 'Spine2', 'Spine3', 'Spine4', 'Chest', 'Neck', 'Neck2']]
- Population check fail/warning bones: 0/0
- selected_joint_map_v0 frozen=false (provisional only)

## Assumptions

- Subject prefix rule: colon_suffix (reversible via subject_prefix + canonical_bone_name).
- Distal exclusion uses provisional config heuristics only; joint set not frozen.
- Provisional auto-included joints: 17; uncertain candidates: 8.
- Parent==Root joints excluded from auto-selection but reported for manual review.
- Root/asset anchor reported as detected; not renamed to Pelvis unless present in CSV.
- Final analysis feature selection is deferred until after Layer 2 output validation and before Layer 3 JcvPCA. See `docs/FEATURE_SELECTION_BOUNDARY.md`.
- Structural rotation population check counts complete raw XYZW rows only; not norm QC or component-order validation.

## Outputs written

- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/01_joint_mapping/report.md`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/01_joint_mapping/bone_inventory.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/01_joint_mapping/candidate_joint_map.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/01_joint_mapping/selected_joint_map_v0.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/01_joint_mapping/excluded_distal_bones.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/01_joint_mapping/joint_selection_summary.md`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/01_joint_mapping/rotation_population_report.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/01_joint_mapping/hierarchy_mapping.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/01_joint_mapping/parent_child_joint_map.csv`
- `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000/01_joint_mapping/joint_channel_map.csv`

## Warnings

- None

## Errors

- None

## Validation status

PASS — native skeleton documented; joint set not frozen

## Next recommended action

Review native skeleton summary, provisional joint map, and population report. Final analysis feature selection is deferred until after Layer 2 validation and before Layer 3. Continue to Stage 02 after review.
