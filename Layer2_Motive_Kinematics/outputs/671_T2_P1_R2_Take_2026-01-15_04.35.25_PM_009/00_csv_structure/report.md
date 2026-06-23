# Stage 00 — CSV structure audit

Generated: 2026-06-23 15:15:03 UTC

## Input files used

- `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T2_P1_R2_Take 2026-01-15 04.35.25 PM_009.csv`

## What was detected

- Metadata line: 1
- Data start line: 9
- Role line numbers: {'metadata': 1, 'type': 3, 'name': 4, 'id': 5, 'parent': 6, 'property': 7, 'component': 8}
- Frame column index 0 (Frame)
- Time column index 1 (Time (Seconds))
- Total columns mapped: 752
- Bone rotation quaternion columns: 204
- Distinct source bones with rotation columns: 51

## Assumptions

- Header block parsed manually without pandas MultiIndex headers.
- Flat column names generated for future numeric loading with pd.read_csv(skiprows=..., names=...).
- Rotation Type detected as Quaternion from metadata row.
- Coordinate Space detected as Global from metadata row.

## Outputs written

- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/00_csv_structure/report.md`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/00_csv_structure/header_row_detection.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/00_csv_structure/detected_columns.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/00_csv_structure/unmatched_columns.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/00_csv_structure/columns_used_for_layer2.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/00_csv_structure/columns_ignored_for_layer2.csv`
- `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/00_csv_structure/metadata_detected.csv`

## Warnings

- None

## Errors

- None

## Validation status

PASS — ready for human review

## Next recommended action

Human reviewer should validate detected header roles, metadata, Frame/Time columns, and bone rotation quaternion inventory before Stage 01.
