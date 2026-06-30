# Optional Extra Figure Recommendations

These are optional supplementary/inset ideas only. They are NOT generated here
and must never modify, replace, or reorder the four locked figures (A-D). Each
is directly supported by an existing validated CSV. All language is descriptive
only - no causal, treatment-effect, clinical, or improvement claims. No new
modeling or unvalidated data is involved.

## Optional 1 - Robustness of the Delta/NV ratio to the chosen NV reference
1. **Proposed title:** Longitudinal Delta vs alternative natural-variability references (T1 / mean / max)
2. **Scientific purpose:** Show that the top longitudinal links of Figure A
   remain notable when the NV denominator is changed from the T1 repetition
   reference to the across-timepoint mean and max NV references.
3. **Required data source:** `longitudinal_delta_nv_ratio_by_link.csv`
   (columns `delta_to_NV_T1_ratio`, `delta_to_NV_mean_ratio`,
   `delta_to_NV_max_ratio`, `NV_mean_abs_delta`, `NV_max_abs_delta`).
4. **Added value beyond A-D:** Directly addresses the small-denominator caveat
   of Figure A by showing the ranking is not an artefact of one NV reference.
5. **Placement:** Small inset beside Figure A or supplementary panel.
6. **Caution:** Never average across participants; ratios remain descriptive
   scale comparisons, not significance, and tiny denominators still inflate ratios.

## Optional 2 - Null-space vs all-PC variability and threshold stability
1. **Proposed title:** Later-PC / null-space variability and link-identity stability
2. **Scientific purpose:** Show that null-space-like subsets often carry
   elevated mean link-level variability, and that family-level structure is more
   threshold-stable than exact link identity.
3. **Required data source:** `nullspace_noise_vs_structure_diagnostic.csv`
   (null/all ratios) and `nullspace_threshold_stability_summary.csv`
   (`threshold_stability_label`).
4. **Added value beyond A-D:** Adds a robustness/dimensionality dimension not
   covered by A-D, clarifying which structure is stable across thresholds.
5. **Placement:** Supplementary.
6. **Caution:** Magnitude elevation does not imply stable exact link identity;
   p70 is threshold-sensitive and supplementary only.

## Optional 3 - One-page take-home evidence table
1. **Proposed title:** Descriptive take-home evidence summary
2. **Scientific purpose:** Provide a compact text table of the main descriptive
   evidence questions, primary results, interpretations, and cautions.
3. **Required data source:** `poster_takehome_numeric_summary.csv`.
4. **Added value beyond A-D:** A single readable synthesis panel tying the
   figures together for viewers who do not read every panel.
5. **Placement:** Main poster bottom row or supplementary.
6. **Caution:** Keep neutral, descriptive language only; it is a summary, not an
   inferential or clinical conclusion.
