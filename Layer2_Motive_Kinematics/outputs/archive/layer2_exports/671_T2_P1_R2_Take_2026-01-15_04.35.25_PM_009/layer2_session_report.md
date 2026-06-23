# Layer 2 per-session export report

Generated: 2026-06-19 15:53:24 UTC

## Session identity

- **Session ID:** 671_T2_P1_R2
- **Run label:** 671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009
- **Skeleton template:** Core + Passive Fingers (54)

## Source

- **Stage 08 parquet:** `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/08_filtered_rotvecs/filtered_relative_rotation_vectors.parquet`
- **Stage 08 report:** `outputs/671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009/08_filtered_rotvecs/report.md`

## Frame / time range

- Frames: 0–30478 (30479 expected)
- Time (sec): 0.000–253.983
- Duration (sec): 253.983
- Sampling rate (Hz): 120.00480019200238

## Links

- Total links: 50
- Core candidates: 16
- Review/provisional: 2
- Excluded by policy: 32

## Stage 07 jump summary

- Stage 07 jump event rows: 0

## Stage 08 masking summary

- Jump-context rows: 0
- Analysis-eligible rows: 487664
- Analysis-ineligible rows: 1036286
- Filter cutoff/order: 10.0 Hz / 4
- Jump context window: ±30 frames

## Native vs analysis-clean

- **Native filtered** columns retain Butterworth-filtered values where filtering ran; they may exist inside jump-context windows for review.
- **Analysis-clean** columns are NaN where `stage08_analysis_eligible=false` (jump context, excluded links, blocked/review policy).

## Known limitations

- Relative rotations are parent-child skeleton segment orientations derived from Motive-solved global bone quaternions.
- Stage 08 does not interpolate or repair Stage 07 jump frames.
- Native filtered values (`*_filtered_native`) are archive/review values and may exist inside jump-context windows.
- Analysis-clean values (`*_filtered_analysis`) are NaN-masked where policy indicates ineligibility (`stage08_analysis_eligible=false`).
- Excluded distal/toe links are retained for traceability but are not recommended for analysis.
- Review/provisional trunk/spine links remain review status and are not core candidates.
- Final frame-window selection and joint/link selection happen later in the post–Layer 2 segmentation notebook.
- Layer 2 does not implement segmentation, PCA, JcvPCA, or JRW.

## Downstream use

This export is a Layer 2 per-session candidate input for the post–Layer 2 segmentation notebook. It is **not** a final Layer 3/JcvPCA input and does not freeze feature selection.
