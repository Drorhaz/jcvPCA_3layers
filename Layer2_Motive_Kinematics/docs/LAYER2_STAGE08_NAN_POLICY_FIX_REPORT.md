# Layer 2 Stage 08 NaN Policy Fix — Implementation Report

Date: 2026-06-23

## 1. Files changed

| File | Change |
|------|--------|
| `src/layer2_motive/filtering.py` | Removed QC NaN masking; added flag/nan report builders; renamed link status to `filtered_but_jump_context_flagged` |
| `src/layer2_motive/stages/stage08.py` | Updated policy docs; writes `stage08_flag_report.csv`, `stage08_ineligible_rows_report.csv`, `stage08_nan_report.csv` |
| `src/layer2_motive/export_layer2.py` | Updated integrity audit, manifest NaN counts, export limitations text |
| `tests/test_filtering_validation.py` | Updated/added contract tests |
| `tests/test_export_layer2.py` | Updated fixture and integrity expectations |

## 2. All NaN-producing policies found in Layer 2

| Stage | Location | Policy | Classification |
|-------|----------|--------|----------------|
| 04 | `quaternion_qc.py` `load_bone_rotation_numeric_data` | `pd.to_numeric(..., coerce)` → NaN for unparseable CSV | **A** — legitimate input missingness |
| 04 | `quaternion_qc.py` internal gap detection | `np.full(..., np.nan)` for norm array (not exported) | **A** |
| 05 | `quaternion_continuity.py` | NaN in → NaN out on quaternions | **A/C** — propagation |
| 06 | `relative_rotation.py` | SciPy invalid quat → NaN relative quat | **A/C** — computational |
| 07 | `rotvec.py` | SciPy log-map invalid quat → NaN rx/ry/rz | **A/C** — computational |
| 07 | `qc_propagation.py` | Sets fail flags; does **not** NaN rotvec columns | **A** — diagnostic only |
| **08** | `filtering.py` `filter_rotvec_components` | NaN where segment too short / non-finite input | **A** — filter cannot run |
| **08** | `filtering.py` `process_link_filtering` (removed) | `analysis_filtered[~analysis_eligible] = np.nan` | **B** — QC masking (**fixed**) |
| Export | `export_layer2.py` (removed check) | Expected NaN on ineligible rows | **B** — audit enforced old policy (**fixed**) |

## 3. Legitimate NaN policies kept

- Stage 04–07: missing/invalid quaternion and rotvec propagation (SciPy / CSV coerce).
- Stage 08 `filter_rotvec_components`: NaN when input segment is non-finite or shorter than `min_filtfilt_length`.
- Stage 08 `filter_not_applied` mask reason on rows where filtering genuinely did not run.

## 4. QC-masking policies changed to flag-only

| Former behavior | New behavior |
|-----------------|--------------|
| Jump-context rows: `rx_filtered_analysis = NaN` | Numeric filtered value preserved; `stage08_analysis_eligible=false`, `stage08_mask_reason=stage07_jump_context` |
| Branch-cut context rows: analysis NaN | Same — flag only |
| Excluded distal/toe links: analysis NaN | Flag only; numeric when filter applied |
| `block_filter` / manual review / provisional links: analysis NaN | Flag only; numeric when filter applied |
| Link status `filtered_but_jump_context_masked` | Renamed to `filtered_but_jump_context_flagged` (old enum name kept as alias) |

Core code change:

```python
# Before
analysis_filtered[~analysis_eligible] = np.nan

# After
analysis_filtered = filtered.copy()  # no QC blanking
```

## 5. Accidental NaN policies fixed

- `export_layer2.py` integrity check `analysis_clean_nan_when_ineligible` enforced the old NaN-masking contract. Replaced with `no_qc_mask_nan_in_analysis_columns`.
- `n_analysis_nan_frames` in link manifest previously counted ineligible rows; now counts actual NaNs in `rx_filtered_analysis`.

No merge/join bugs found.

## 6. Stage 07 thresholds unchanged

Confirmed: `identify_stage07_jump_event_frames`, `RotVecThresholds`, and config defaults (`jump_warning_rad=0.5`, `jump_fail_rad=1.0`, branch-cut thresholds) were not modified.

## 7. Stage 08 filter parameters unchanged

Confirmed: `cutoff_hz=10.0`, `filter_order=4`, `filter_type=butterworth`, `jump_context_window_frames=30`, `nyquist_safety_factor=0.45` — unchanged.

## 8. Quaternion math and rotvec logic unchanged

No changes to quaternion parsing, parent-child mapping, multiplication, sign continuity, rotvec/log-map, or Butterworth SOS design.

## 9. Tests added/updated

**Updated**

- `test_jump_context_frames_keep_numeric_analysis_values` (was `test_analysis_clean_nan_inside_jump_context`)
- `test_excluded_links_flagged_but_numeric_when_filtered`
- `test_block_filter_still_flags_whole_link`
- `test_branch_cut_context_flagging`
- `test_qc_flagged_rows_keep_numeric_analysis_values` (export)

**Added**

- `test_jump_context_no_qc_mask_nan_in_analysis_columns`
- `test_native_and_analysis_filtered_match_when_filter_applied`
- `test_computational_nan_only_when_filter_not_applied`
- `test_stage08_nan_report_distinguishes_computational_from_qc_flagged`
- `test_stage08_reports_include_flagged_rows`
- `test_jump_detection_thresholds_unchanged`
- `test_filter_parameters_unchanged`

## 10. Tests run and results

```text
Layer2_Motive_Kinematics: pytest tests/ → 119 passed, 1 skipped
Focused: test_filtering_validation.py + test_export_layer2.py → 34 passed
```

## 11. Example before/after (jump-context frame)

Hypothetical frame×link in jump context where filtering succeeded:

| Field | Before | After |
|-------|--------|-------|
| `rx_filtered_native` | 0.142 | 0.142 |
| `rx_filtered_analysis` | **NaN** | **0.142** |
| `stage08_analysis_eligible` | false | false |
| `stage08_mask_reason` | stage07_jump_context | stage07_jump_context |
| `stage08_filter_status` | filtered_but_jump_context_masked | filtered_but_jump_context_flagged |

The numeric value is preserved, and the risk is explicitly flagged for Layer 2.5 / notebook / Layer 3 decision-making.

## 12. Remaining known limitations

- `rx_filtered_native` and `rx_filtered_analysis` are now identical whenever filtering succeeds; column names retained for Layer 2.5 contract compatibility.
- Rows with `filter_not_applied` still have NaN in both native and analysis columns (legitimate computational failure).
- Existing archived Stage 08 outputs under `outputs/` still reflect the old NaN-masking policy until re-run.
- Layer 2.5 must read `stage08_analysis_eligible` / `stage08_mask_reason` for QC decisions; numeric matrices no longer encode exclusion via NaN holes.

## New Stage 08 reports

| Report | Purpose |
|--------|---------|
| `stage08_flag_report.csv` | All ineligible/flagged rows with context bounds |
| `stage08_ineligible_rows_report.csv` | Same + `value_kept_numeric` column |
| `stage08_nan_report.csv` | True computational NaNs with classification |
| `stage08_jump_context_report.csv` | Enriched with eligibility columns + review note |
