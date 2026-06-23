# Stage 08 filtering batch index

Batch index of per-file Butterworth filtering with jump-context masking (V1).

## Explicit limitation

Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.

Stage 08 V1 does **not** interpolate Stage 07 jump frames. Native filtered columns may retain values inside jump-context windows; analysis-clean columns are NaN there.

Total runs: 6

## Batch aggregate

- **Total jump event frames (sum across files):** 64
- **Total jump-context frames (sum across files):** 3904

## `671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001`

- **Input:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv`
- **Output:** `outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001`
- **Links processed:** 50 (pass/blocked/excluded/review: 15/1/32/2)
- **Links with jump context:** 19
- **Jump event frames:** 19
- **Jump-context frames:** 1159
- **Analysis-eligible frames:** 458938
- **Interpolation applied:** False
- **Status:** REVIEW REQUIRED
- **Limitations:** Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.

## `671_T1_P1_R2_Take_2026-01-06_03.57.12_PM_003`

- **Input:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T1_P1_R2_Take 2026-01-06 03.57.12 PM_003.csv`
- **Output:** `outputs/671_T1_P1_R2_Take_2026-01-06_03.57.12_PM_003`
- **Links processed:** 50 (pass/blocked/excluded/review: 16/0/32/2)
- **Links with jump context:** 0
- **Jump event frames:** 0
- **Jump-context frames:** 0
- **Analysis-eligible frames:** 483760
- **Interpolation applied:** False
- **Status:** PASS WITH REVIEW
- **Limitations:** Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.

## `671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005`

- **Input:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T2_P1_R1_Take 2026-01-15 04.35.25 PM_005.csv`
- **Output:** `outputs/671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005`
- **Links processed:** 50 (pass/blocked/excluded/review: 16/0/32/2)
- **Links with jump context:** 13
- **Jump event frames:** 13
- **Jump-context frames:** 793
- **Analysis-eligible frames:** 485574
- **Interpolation applied:** False
- **Status:** PASS WITH REVIEW
- **Limitations:** Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.

## `671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009`

- **Input:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T2_P1_R2_Take 2026-01-15 04.35.25 PM_009.csv`
- **Output:** `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009`
- **Links processed:** 50 (pass/blocked/excluded/review: 16/0/32/2)
- **Links with jump context:** 0
- **Jump event frames:** 0
- **Jump-context frames:** 0
- **Analysis-eligible frames:** 487664
- **Interpolation applied:** False
- **Status:** PASS WITH REVIEW
- **Limitations:** Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.

## `671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000`

- **Input:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T3_P1_R1_Take 2026-02-03 08.05.01 PM_000.csv`
- **Output:** `outputs/671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000`
- **Links processed:** 54 (pass/blocked/excluded/review: 13/3/32/6)
- **Links with jump context:** 17
- **Jump event frames:** 23
- **Jump-context frames:** 1403
- **Analysis-eligible frames:** 411762
- **Interpolation applied:** False
- **Status:** REVIEW REQUIRED
- **Limitations:** Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.

## `671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005`

- **Input:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/671/671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv`
- **Output:** `outputs/671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005`
- **Links processed:** 54 (pass/blocked/excluded/review: 16/0/32/6)
- **Links with jump context:** 8
- **Jump event frames:** 9
- **Jump-context frames:** 549
- **Analysis-eligible frames:** 502211
- **Interpolation applied:** False
- **Status:** PASS WITH REVIEW
- **Limitations:** Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.
