# Stage 00 — CSV structure audit

Generated: 2026-06-21 12:23:49 UTC

## Input files used

- `data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv`

## What was detected

- Metadata line: 1
- Data start line: 9
- Role line numbers: {'metadata': 1, 'type': 3, 'name': 4, 'id': 5, 'parent': 6, 'property': 7, 'component': 8}
- Frame column index 0 (Frame)
- Time column index 1 (Time (Seconds))
- Total columns mapped: 827
- Bone rotation quaternion columns: 204
- Distinct source bones with rotation columns: 51

## Assumptions

- Header block parsed manually without pandas MultiIndex headers.
- Flat column names generated for future numeric loading with pd.read_csv(skiprows=..., names=...).
- Rotation Type detected as Quaternion from metadata row.
- Coordinate Space detected as Global from metadata row.

## Outputs written

- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/00_csv_structure/report.md`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/00_csv_structure/header_row_detection.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/00_csv_structure/detected_columns.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/00_csv_structure/unmatched_columns.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/00_csv_structure/columns_used_for_layer2.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/00_csv_structure/columns_ignored_for_layer2.csv`
- `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/00_csv_structure/metadata_detected.csv`

## Warnings

- None

## Errors

- None

## Validation status

PASS — ready for human review

## Next recommended action

Human reviewer should validate detected header roles, metadata, Frame/Time columns, and bone rotation quaternion inventory before Stage 01.
