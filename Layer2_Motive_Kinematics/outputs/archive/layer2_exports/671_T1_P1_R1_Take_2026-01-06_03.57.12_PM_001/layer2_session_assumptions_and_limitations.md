# Layer 2 session export — assumptions and limitations

- Relative rotations are parent-child skeleton segment orientations derived from Motive-solved global bone quaternions.
- Stage 08 does not interpolate or repair Stage 07 jump frames.
- Jump and branch-cut Stage 07 failures are masked locally (event frame ± context window), not as whole-link blocks.
- Native filtered values (`*_filtered_native`) are archive/review values and may exist inside QC context windows.
- Analysis-clean values (`*_filtered_analysis`) are NaN-masked where policy indicates ineligibility (`stage08_analysis_eligible=false`).
- Excluded distal/toe links are retained for traceability but are not recommended for analysis.
- Review/provisional trunk/spine links remain review status and are not core candidates.
- Final frame-window selection and joint/link selection happen later in the post–Layer 2 segmentation notebook.
- Layer 2 does not implement segmentation, PCA, JcvPCA, or JRW.
