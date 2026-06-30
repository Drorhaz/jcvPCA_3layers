# Stage 08 filtering batch index

Batch index of per-file Butterworth filtering with jump-context masking (V1).

## Explicit limitation

Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.

Stage 08 V1 does **not** interpolate Stage 07 jump frames. Native filtered columns may retain values inside jump-context windows; analysis-clean columns are NaN there.

Total runs: 6

## Batch aggregate

- **Total jump event frames (sum across files):** 32
- **Total jump-context frames (sum across files):** 1892

## `252_T1_P1_R1_Take_2026-04-28_04.15.00_PM_000`

- **Input:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/252/T1/252_T1_P1_R1_Take 2026-04-28 04.15.00 PM_000.csv`
- **Output:** `outputs/252_T1_P1_R1_Take_2026-04-28_04.15.00_PM_000`
- **Links processed:** 54 (pass/blocked/excluded/review: 16/0/32/6)
- **Links with jump context:** 1
- **Jump event frames:** 1
- **Jump-context frames:** 61
- **Analysis-eligible frames:** 505331
- **Interpolation applied:** False
- **Status:** PASS WITH REVIEW
- **Limitations:** Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.

## `252_T1_P1_R2_Take_2026-04-28_04.15.00_PM_002`

- **Input:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/252/T1/252_T1_P1_R2_Take 2026-04-28 04.15.00 PM_002.csv`
- **Output:** `outputs/252_T1_P1_R2_Take_2026-04-28_04.15.00_PM_002`
- **Links processed:** 54 (pass/blocked/excluded/review: 16/0/32/6)
- **Links with jump context:** 3
- **Jump event frames:** 9
- **Jump-context frames:** 549
- **Analysis-eligible frames:** 505643
- **Interpolation applied:** False
- **Status:** PASS WITH REVIEW
- **Limitations:** Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.

## `252_T2_P1_R1_Take_2026-04-26_06.09.29_PM_001`

- **Input:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/252/T2/252_T2_P1_R1_Take 2026-04-26 06.09.29 PM_001.csv`
- **Output:** `outputs/252_T2_P1_R1_Take_2026-04-26_06.09.29_PM_001`
- **Links processed:** 54 (pass/blocked/excluded/review: 16/0/32/6)
- **Links with jump context:** 5
- **Jump event frames:** 5
- **Jump-context frames:** 305
- **Analysis-eligible frames:** 504175
- **Interpolation applied:** False
- **Status:** PASS WITH REVIEW
- **Limitations:** Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.

## `252_T2_P1_R2_Take_2026-04-26_06.09.29_PM_004`

- **Input:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/252/T2/252_T2_P1_R2_Take 2026-04-26 06.09.29 PM_004.csv`
- **Output:** `outputs/252_T2_P1_R2_Take_2026-04-26_06.09.29_PM_004`
- **Links processed:** 54 (pass/blocked/excluded/review: 16/0/32/6)
- **Links with jump context:** 1
- **Jump event frames:** 1
- **Jump-context frames:** 61
- **Analysis-eligible frames:** 503219
- **Interpolation applied:** False
- **Status:** PASS WITH REVIEW
- **Limitations:** Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.

## `252_T3_P1_R1_Take_2026-06-09_05.04.14_PM`

- **Input:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/252/T3/252_T3_P1_R1_Take 2026-06-09 05.04.14 PM.csv`
- **Output:** `outputs/252_T3_P1_R1_Take_2026-06-09_05.04.14_PM`
- **Links processed:** 54 (pass/blocked/excluded/review: 16/0/32/6)
- **Links with jump context:** 5
- **Jump event frames:** 8
- **Jump-context frames:** 488
- **Analysis-eligible frames:** 503128
- **Interpolation applied:** False
- **Status:** PASS WITH REVIEW
- **Limitations:** Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.

## `252_T3_P1_R2_Take_2026-06-09_05.04.14_PM_001`

- **Input:** `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/data/252/T3/252_T3_P1_R2_Take 2026-06-09 05.04.14 PM_001.csv`
- **Output:** `outputs/252_T3_P1_R2_Take_2026-06-09_05.04.14_PM_001`
- **Links processed:** 54 (pass/blocked/excluded/review: 16/0/32/6)
- **Links with jump context:** 5
- **Jump event frames:** 8
- **Jump-context frames:** 428
- **Analysis-eligible frames:** 510181
- **Interpolation applied:** False
- **Status:** PASS WITH REVIEW
- **Limitations:** Stage 08 filtering success does not finalize analysis features, freeze joint selection, or make Layer 3 ready. V1 does not interpolate Stage 07 jump frames.
