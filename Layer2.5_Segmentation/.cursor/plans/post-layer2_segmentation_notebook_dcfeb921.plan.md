---
name: Post-Layer2 Segmentation Notebook
overview: Detailed V1 implementation plan for a per-session, frame-level QC-integrated post-Layer 2 segmentation review notebook. A thin Jupyter front end calls tested Python modules; a CLI validator runs the same checks. No exact marker->link mapping, no Layer 3, no PCA/JcvPCA/JRW. Inputs are never modified.
todos:
  - id: phase0
    content: "Phase 0: Project scaffolding (src/ layout, pyproject.toml, requirements.txt, pytest config, package __init__) and freeze the input contract."
    status: completed
  - id: phase1
    content: "Phase 1: schemas.py — required column lists, allowed-value enums (recommendation/severity/feature_scope/mapping_confidence), normalized schema dataclasses, threshold constants."
    status: completed
  - id: phase2
    content: "Phase 2: load_inputs.py — load_layer1_qc_folder + load_layer2_export_folder with required-vs-optional handling and non-fatal warnings; return typed bundle objects."
    status: completed
  - id: phase3
    content: "Phase 3: validate_inputs.py — all design-review checks (files, columns, identity run_key==session_id, frame range/overlap, time drift, duplicate frame×link, manifest join by run_label+link_id, integrity audit, NaN-vs-gap distinction). Returns structured ValidationResult."
    status: completed
  - id: phase4
    content: "Phase 4: scripts/validate_segmentation_inputs.py CLI — writes validation_report.md, validation_summary.json, validation_checks.csv; exit codes for pass/warn/block."
    status: completed
  - id: phase5
    content: "Phase 5: qc_events.py — normalize Layer 1 qc_mask (+ optional intervals, artifact_events, gaps) into the internal event schema; frame-level only; optional body-region overlay column."
    status: pending
  - id: phase6
    content: "Phase 6: window_summary.py — subset_window, summarize_layer1_window, summarize_layer2_window, build_combined_qc_event_table."
    status: pending
  - id: phase7
    content: "Phase 7: recommendations.py — window-recomputed per-link 6-class logic with configurable thresholds; never relies solely on session-level default."
    status: pending
  - id: phase8
    content: "Phase 8: export_segment.py — write the six segment artifacts; selected frames+links only; preserve QC labels and analysis NaNs; relative_frame/time; record overrides + alignment + warnings."
    status: pending
  - id: phase9
    content: "Phase 9: widgets.py + notebooks/post_layer2_segmentation_review.ipynb — progressive-disclosure thin front end calling the modules; default-select candidate_include only; require notes on warning export."
    status: pending
  - id: phase10
    content: "Phase 10: tests/ — pytest suite covering loading, validation, identity, alignment, join, window subset, summaries, all recommendation classes, export, NaN preservation, no-input-mutation, override logging, no marker->link invalidation claim."
    status: pending
  - id: phase11
    content: "Phase 11: docs + end-to-end smoke test on 671_T1_P1_R1 (scripts/smoke_segment_export.py) producing one reference segment; README documentation."
    status: pending
isProject: false
---

# Post-Layer 2 Segmentation Notebook — Detailed V1 Implementation Plan

## 0. Scope, guardrails, and non-goals

V1 = safe, frame-level QC integration for ONE session at a time.

In scope:
- Load one Layer 1 QC folder + one Layer 2 export folder.
- Validate identity, frame alignment, schemas, manifest join, integrity audit (same checks as design review).
- CLI validator that writes a report and is callable from the notebook.
- Session overview, interactive frame-range selection, window QC summaries, combined QC event table.
- Window-recomputed per-link recommendations (6 classes).
- Link selection widget; segment export (6 files) with full decision/override logging.
- Optional coarse `body_region_group` risk OVERLAY (label only, never auto-exclude).

Explicit non-goals (do NOT implement):
- Exact marker -> bone -> link mapping (Motive CSV header parsing). V2.
- Layer 3, PCA, JcvPCA, JRW, statistics, final feature freeze.
- Multi-session combination, timeline plots, video, auto window suggestion, body map.
- Any mutation/repair/imputation of Layer 1 or Layer 2 inputs.

Hard correctness rules (must hold everywhere):
- Frame is the canonical join key. Never join on floating-point time.
- Identity: Layer 1 `run_key` must equal Layer 2 `session_id`. `run_label` is longer (take/date) and must NOT be used as the Layer 1 identity key.
- Identity mismatch -> block by default; allow explicit force override only if recorded in metadata (`identity_override=true`).
- Frame-range mismatch -> restrict to overlap, record mismatch, never silently truncate.
- Missing time column -> allow frame-based operation, reconstruct display time from `frame / frame_rate_hz`, set `time_source="reconstructed"`.
- Recommendations recomputed per window; session-level `recommended_segmentation_default` used only as a labeled prior.
- Analysis-clean NaNs (`*_filtered_analysis`) are masked-by-policy, distinct from raw marker gaps; never imputed, never conflated.
- Inputs are opened read-only; export writes only under `outputs/`.

set up a project virtualenv in Phase 0.

## 1. Verified fixture facts (ground truth to code against)

Canonical fixtures:
- Layer 1: `input/Layer1_QC/QC_671_T1_P1_R1/`
- Layer 2: `input/Layer2_Kinematics/671_T1_P1_R1/`

Layer 1 (`layer1_segmentation_notebook_manifest.json`): `subject_id=671`, `session_id=T1_P1_R1`, `run_key=671_T1_P1_R1`, `frame_rate_hz=120.0`, `n_frames=30604`, `frame_index_column=frame`, `time_column=time_s`, points to `qc_mask.csv`, `qc_mask_intervals.csv`.
- `qc_mask.csv`: 30604 rows, frames `0..30603`, `time_s 0.0..255.025`, `status in {use(26618), caution(2464), exclude(1522)}`, flags `flag_gap_0p2, flag_gap_0p5, flag_artifact_sigma, flag_segment_swap, flag_edge_effect`, `reason`.
- `artifact_events.csv`: `event_id, marker_name, body_region_group, method, start_frame, end_frame, start_time_s, end_time_s, duration_frames, duration_seconds, event_class, severity, near_gap, methods_in_event, peak_metric_value`. Markers like `671:LFArm`, segment-length pairs like `ChestTop__WaistCBack`.
- `qc_mask_intervals.csv`: `start_frame, end_frame, start_s, end_s, duration_s, status, reason, criterion, affected_markers, has_*` flags.

Layer 2 (`layer2_session_summary.json`): `session_id=671_T1_P1_R1`, `run_label=671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001`, `skeleton_template="Core + Passive Fingers (54)"`, `frame_count=30604`, `duration_sec=255.025`, `sampling_rate_hz=120.0048`, `n_links_total=50`, `integrity_status=pass`.
- `layer2_session_filtered_rotvecs.parquet`: 1,530,200 rows = 50 links x 30604 frames, 41 columns, frames `0..30603`. Categorical values verified:
  - `feature_scope in {core_candidate, review_provisional, excluded_distal, excluded_toe}`
  - `stage07_jump_status in {pass, warning, fail}`
  - `stage08_policy in {allow_filter, allow_filter_with_warning, block_filter, manual_review_required, excluded_from_analysis}`
  - `stage08_output_scope in {analysis_clean_core, review_provisional, blocked, excluded_from_analysis}`
  - `stage08_mask_reason in {"", stage07_jump_context, manual_review_provisional, blocked_needs_review, excluded_feature_scope}`
- `layer2_session_link_manifest.csv`: 50 rows; columns include `session_id, run_label, skeleton_template, link_id, parent_canonical, child_canonical, feature_scope, included_in_v0, requires_manual_review, stage08_policy, stage08_output_scope, n_total_frames, n_native_finite_frames, n_analysis_eligible_frames, n_analysis_nan_frames, n_jump_context_frames, n_stage07_jump_frames, n_stage07_warning_frames, n_stage07_fail_frames, n_layer2_masked_frames, percent_analysis_eligible, recommended_segmentation_default, short_explanation`.
- `layer2_session_integrity_audit.csv`: `check_name, status, details`; 16 checks all `pass`.

Worked recommendation examples to assert in tests:
- `J004 Neck->Head`: 100% eligible, full-session -> `candidate_include`.
- `J005 LUArm->LFArm`: session-level `include_with_caution` (61 jump-context frames near the single Stage07 jump ~ frame region). A window EXCLUDING those 61 frames must recompute to `candidate_include`.
- `J007 LFArm->LHand`: `stage08_policy=block_filter` -> `blocked_needs_review` in EVERY window.
- `J002/J003 (Ab links)`: `review_provisional` + `requires_manual_review=true` -> `manual_review` in every window.
- `J008+ finger links`: `excluded_distal` -> `excluded_by_policy` in every window.

## 2. Project structure to create

```text
Layer2.5_Segmentation/
  pyproject.toml                 # package config + pytest config
  requirements.txt               # pandas, pyarrow, ipywidgets, jupyterlab, pytest
  README.md                      # (or docs/) project usage
  docs/POST_LAYER2_SEGMENTATION_NOTEBOOK_README.md
  notebooks/post_layer2_segmentation_review.ipynb
  scripts/
    validate_segmentation_inputs.py   # CLI validator
    smoke_segment_export.py           # non-interactive end-to-end smoke test
  src/layer2_motive/
    __init__.py
    segmentation/
      __init__.py
      schemas.py
      load_inputs.py
      validate_inputs.py
      qc_events.py
      window_summary.py
      recommendations.py
      export_segment.py
      widgets.py
  tests/
    conftest.py                  # fixture paths + tiny synthetic builders
    test_load_inputs.py
    test_validate_inputs.py
    test_qc_events.py
    test_window_summary.py
    test_recommendations.py
    test_export_segment.py
    test_no_input_mutation.py
  outputs/                       # generated (gitignored): segments/, segmentation_validation/
```

Packaging: `pyproject.toml` with `[project]` (name `layer2-segmentation`), src layout, `[tool.pytest.ini_options] pythonpath=["src"]`. Notebook adds `src` to `sys.path` (or relies on editable install) — no business logic in the notebook.

Dependencies (`requirements.txt`): `pandas>=2.0`, `pyarrow>=14`, `ipywidgets>=8`, `jupyterlab`, `pytest>=8`.

## 3. Module specs

### 3.1 schemas.py (single source of truth)
- Required Layer 1 columns:
  - `qc_mask`: `["frame","status"]` required; `["time_s","flag_gap_0p2","flag_gap_0p5","flag_artifact_sigma","flag_segment_swap","flag_edge_effect","reason"]` expected/optional.
  - manifest keys required: `["run_key","frame_rate_hz","n_frames","frame_index_column"]`.
- Required Layer 2 parquet columns (assert all present):
  `["session_id","run_label","frame","time_sec","link_id","parent_canonical","child_canonical","feature_scope","included_in_v0","requires_manual_review","stage07_jump_status","stage07_jump_magnitude_rad","stage08_policy","stage08_within_jump_context_window","stage08_analysis_eligible","stage08_mask_reason","stage08_output_scope","rx_filtered_native","ry_filtered_native","rz_filtered_native","rotvec_norm_filtered_native","rx_filtered_analysis","ry_filtered_analysis","rz_filtered_analysis","rotvec_norm_filtered_analysis"]`.
- Required Layer 2 link-manifest columns:
  `["session_id","run_label","link_id","parent_canonical","child_canonical","feature_scope","included_in_v0","requires_manual_review","stage08_policy","stage08_output_scope","percent_analysis_eligible","recommended_segmentation_default","short_explanation"]`.
- Enums (frozensets):
  - `RECOMMENDATION_CLASSES = {candidate_include, include_with_caution, manual_review, exclude_recommended, excluded_by_policy, blocked_needs_review}`
  - `SEVERITY_CLASSES = {info, caution, exclude, minor, moderate, severe}`
  - `FEATURE_SCOPES = {core_candidate, review_provisional, excluded_distal, excluded_toe}`
  - `MAPPING_CONFIDENCE = {n/a, body_region_overlay, unmapped}`
  - `ENTITY_TYPES = {frame, marker, segment, link, interval}`
- Dataclasses / TypedDicts: `Layer1Bundle`, `Layer2Bundle`, `SessionIdentity`, `AlignmentInfo`, `ValidationCheck`, `ValidationResult`, `RecommendationThresholds(include_min=95.0, caution_min=90.0, blocked_mask_frac=0.5, jump_context_isolated_max=...)`, `SegmentSelection`.
- `COMBINED_EVENT_COLUMNS`, `JOINT_SUMMARY_COLUMNS`, `SEGMENT_PARQUET_COLUMNS` lists.

### 3.2 load_inputs.py
- `load_layer1_qc_folder(path) -> Layer1Bundle`:
  - read manifest JSON (required) and `qc_mask.csv` (required) -> hard error if missing.
  - optionally read `qc_mask_intervals.csv`, `artifact_events.csv`, `gaps_over_0p2s.csv`, `gaps_over_0p5s.csv`, `quarantined_markers.csv` -> on missing/empty, attach `None` + append a non-fatal warning string. Tolerate empty optional files.
  - bundle carries: manifest dict, qc_mask df, optional dfs, `source_paths`, `warnings`.
- `load_layer2_export_folder(path) -> Layer2Bundle`:
  - read parquet (required), link manifest CSV (required), summary JSON (required) -> hard error if missing.
  - optionally read integrity audit CSV, report/assumptions/README -> non-fatal.
  - parquet read once and cached; expose `.parquet_df` and a `frame`-indexed accessor.
- All reads are read-only; never write back. Returns warnings list, never raises on OPTIONAL files.

### 3.3 validate_inputs.py (mirrors design-review checks)
Functions returning `ValidationCheck` rows aggregated into `ValidationResult{checks, blocking_errors, warnings, safe_to_open: bool}`:
- `validate_layer1_contract(bundle)`: required files present; manifest loads; qc_mask required columns exist; detect frame range; detect/repair time column (record `time_source`).
- `validate_layer2_contract(bundle)`: required files present; summary loads; parquet loads; link manifest loads; required parquet columns exist; required manifest columns exist; detect frame range; no duplicate `(frame, link_id)` rows.
- `resolve_session_identity(l1, l2)`: compare Layer1 `run_key` vs Layer2 `session_id`. Pass if equal; else BLOCK unless `force=True` (then record `identity_override=true`). Explicitly assert `run_label` is NOT used as the L1 key (separate check that records `run_label` and confirms match was via `session_id`).
- `validate_frame_alignment(l1, l2)`: compute both ranges; overlap `[max(starts), min(ends)]`; if identical report `exact_frame_alignment=true`; if differ compute overlap + WARN + record mismatch; compare time ranges for DISPLAY/drift warning only; assert frame is canonical key.
- `validate_link_manifest_join(l2)`: join by `(run_label, link_id)` (and `(session_id, run_label, link_id)`); assert set equality parquet<->manifest; FAIL if join incomplete; never join by `link_id` alone.
- `check_layer2_integrity_audit(l2)`: if audit present, surface each `check_name/status`; treat any non-`pass` as WARNING (or BLOCK for critical ones like `analysis_clean_nan_when_ineligible`, `no_duplicate_frame_link_rows`).
- `check_nan_vs_gap_distinction(l2)`: confirm `*_filtered_analysis` NaN aligns with `stage08_analysis_eligible=false` and is reported separately from Layer 1 raw gaps (no conflation in any downstream table).
- `run_all_validations(l1, l2, force=False) -> ValidationResult`: orchestrates all of the above; deterministic ordering; `safe_to_open = no blocking_errors`.

### 3.4 scripts/validate_segmentation_inputs.py (CLI)
- Args: `--layer1-dir`, `--layer2-dir`, `--out`, `--force` (optional).
- Loads both folders, runs `run_all_validations`, writes to `--out`:
  - `validation_report.md`: L1 identity/frame count/range/time range; L2 identity/frame count/range/time range; identity comparison; frame alignment result; required files+columns; link-manifest join result; integrity audit status; warnings; blocking errors; final verdict "SAFE / SAFE WITH WARNINGS / BLOCKED to open in segmentation notebook".
  - `validation_summary.json`: machine-readable identity, alignment block, counts, `safe_to_open`, lists of warnings/errors.
  - `validation_checks.csv`: one row per check (`check_name, status[pass|warn|fail], details`).
- Exit codes: `0` pass, `0` pass-with-warnings (warnings in report), `2` blocked. Never writes into input dirs.

### 3.5 qc_events.py (Layer 1 normalization, frame-level only)
- `normalize_qc_mask(qc_mask_df, identity) -> events_df`: one row per non-`use` frame (status caution/exclude) as `qc_type="frame_status"`, severity = status; also emit per-flag events (`marker_gap_0p2`, `marker_gap_0p5`, `artifact_sigma`, `segment_swap`, `edge_effect`) when flag True; carry `reason`.
- `normalize_intervals(intervals_df)`: optional -> interval events (`start_frame,end_frame`, severity=status, reason, `affected_markers` -> notes).
- `normalize_artifact_events(artifact_df)`: optional -> events with `marker_raw_name`, `body_region_group`, `event_class`, `severity`, frame range.
- `parse_gap_intervals(gaps_df, frame_rate_hz)`: optional -> parse `"a-b; c-d"` seconds strings to frame ranges (display/aux only).
- `build_layer1_event_table(bundle, identity) -> normalized events df` (internal schema): columns `session_key, source_file, source_layer="layer1", qc_type, severity, frame, start_frame, end_frame, time_sec, start_time_sec, end_time_sec, duration_frames, duration_seconds, marker_raw_name, body_region_group, reason, notes`.
- `build_body_region_overlay(events_df)` (optional V1.1): aggregate artifact/exclude frames per `body_region_group` for the window; output is LABEL-ONLY with `mapping_confidence="body_region_overlay"`; MUST NOT assert a specific link is invalid.
- Invariant: no function maps a marker to a specific Layer 2 link in V1.

### 3.6 window_summary.py
- `subset_window(layer1_events, layer2_df, start_frame, end_frame) -> (l1_window, l2_window)`: inclusive `[start,end]`; validate bounds within overlap; handle empty window.
- `summarize_layer1_window(l1_window, n_window_frames) -> dict`: counts of use/caution/exclude frames, gap frames, artifact-event frames, percent affected, clusters, markers/groups affected.
- `summarize_layer2_window(l2_window) -> dict`: Stage07 jump frames, Stage08 jump-context rows, analysis-ineligible rows, analysis NaN rows, links affected by masks, counts by output scope.
- `build_combined_qc_event_table(l1_window_events, l2_window) -> df` with columns: `source_layer, frame, start_frame, end_frame, time_sec, start_time_sec, end_time_sec, entity_type, entity_name, link_id, parent_canonical, child_canonical, qc_type, severity, reason, recommended_action, mapping_confidence`. For V1 `mapping_confidence in {n/a, body_region_overlay, unmapped}`.

### 3.7 recommendations.py (window-recomputed)
- `recommend_links_for_window(l2_window, l1_window_summary, thresholds) -> df`, one row per link:
  columns `link_id, parent_canonical, child_canonical, feature_scope, n_window_frames, n_analysis_eligible_frames, n_analysis_nan_frames, n_layer2_jump_context_frames, n_stage07_jump_frames_in_window, percent_usable, has_critical_issue, recommendation, short_explanation`.
- `percent_usable = 100 * n_analysis_eligible_frames / n_window_frames`.
- `n_stage07_jump_frames_in_window` = rows with `stage07_jump_status=="fail"`.
- Rule order (first match wins):
  1. `excluded_by_policy`: `feature_scope in {excluded_distal, excluded_toe}` or `stage08_policy=="excluded_from_analysis"`.
  2. `blocked_needs_review`: core link with `stage08_policy=="block_filter"`, or core link with major masked burden (`n_analysis_nan_frames/n_window_frames >= thresholds.blocked_mask_frac` driven by blocked/mask reasons).
  3. `manual_review`: `feature_scope=="review_provisional"` or `requires_manual_review==true`.
  4. `candidate_include`: `core_candidate` and `percent_usable >= include_min(95)` and no Stage07 fail in window and no severe Layer 1 burden.
  5. `include_with_caution`: `core_candidate` and (`caution_min(90) <= percent_usable < include_min`) or isolated jump-context frames or small Layer 1 caution/exclude burden.
  6. `exclude_recommended`: `core_candidate` and `percent_usable < caution_min(90)` and not already policy/blocked.
- `has_critical_issue = recommendation in {blocked_needs_review, exclude_recommended}` or any Stage07 fail on a core link in window.
- `short_explanation`: human string referencing the deciding factors. Thresholds configurable via `RecommendationThresholds`.

### 3.8 export_segment.py
- `export_segment(l2_df, combined_events, recommendation_df, selection, identity, alignment, validation_result, out_root="outputs/segments") -> Path`:
  - Resolve `session_key`, `segment_name`; create `outputs/segments/<session_key>/<segment_name>/`.
  - Subset parquet to selected frames AND selected links; add `segment_id, segment_name, relative_frame = frame-start_frame, relative_time_sec`; add `selected_for_segment=true`; preserve all QC label columns AND analysis NaNs (no imputation).
  - Write the six files:
    - `segment_filtered_rotvecs.parquet`
    - `segment_qc_events.csv` (combined events intersecting window)
    - `segment_joint_summary.csv` (one row per available link incl. selection + recommendation)
    - `segment_metadata.json` (identity, frame range, selected/excluded links, thresholds used, alignment block, time_source, identity_override, warnings, software_version/git_commit, input path pointers + sizes/mtimes)
    - `segment_review_report.md` (identity, window, links, L1/L2 summaries, combined event summary, user notes, limitations footer "candidate Layer 3 input, not final analysis; no inputs modified")
    - `segment_selection_log.json` (per-link recommendation vs user_choice + `override` flag, timestamps, user note)
  - Returns the segment dir. Never writes outside `outputs/`; never touches inputs.

### 3.9 widgets.py + notebook
- Widgets (thin ipywidgets wrappers over the modules):
  - `build_session_loader_widget()`: two path inputs + Load button -> calls load + `run_all_validations`; shows verdict; only enables next step if `safe_to_open` (warnings allowed).
  - `build_overview_view()`: identity, template, frame/time span, link rollups, session-level recommendation prior.
  - `build_frame_range_widget()`: `IntRangeSlider` + start/end `BoundedIntText` + time readout + Review Window button. ENABLED only after validation passes.
  - `build_link_selection_widget()`: grouped checkboxes by body region / feature group; default-check only `candidate_include`; show recommendation + percent_usable inline.
  - `build_export_widget()`: `segment_name`, notes Textarea, Export button; requires notes if any warning/caution/manual_review/blocked link selected.
  - `build_warning_summary(...)`: banner with counts.
- Notebook sections (progressive disclosure; each gated on prior success): 1 Setup, 2 Load folders, 3 Validate identity+alignment, 4 Session overview, 5 Frame-range selection, 6 Window QC review, 7 Link recommendation table, 8 Link selection, 9 Export, 10 Review exported files.
- The notebook MUST call the same validation functions before enabling the frame-range widget; on failure it stops and shows errors; on warnings it proceeds but displays + records them in export metadata.

## 4. Tests (pytest, non-notebook logic)

Fixtures: `conftest.py` exposes real fixture dirs + builders for a tiny synthetic parquet (e.g. 200 frames x 4 links) and tiny qc_mask to trigger every branch deterministically.

Required tests (map to spec):
- Loading: L1 folder loads; L2 folder loads; optional-missing => warning not failure; empty optional tolerated.
- Schema: required L2 parquet columns validated; missing required column FAILS; required manifest columns validated.
- Identity: `run_key==session_id` passes; identity mismatch BLOCKS unless force; run_label mismatch does NOT block when session_id==run_key.
- Alignment: exact match on 0..30603 passes; differing ranges compute overlap + warning; missing time column still allows frame-based validation + `time_source=reconstructed`.
- Duplicate `(frame, link_id)` rows FAIL.
- Manifest join by `run_label+link_id` succeeds; deliberate join failure FAILS; never by link_id alone.
- Window subset inclusive + correct; empty window handled.
- Layer 1 window summary counts use/caution/exclude frames.
- Layer 2 window summary counts analysis-eligible/masked rows.
- Recommendations: all six classes triggerable; recompute by window (J005-style flip: full session => caution, window avoiding 61 frames => candidate_include); J007 stays blocked.
- Export: writes all six files; parquet has only selected frames + links; expected row count = n_selected_frames * n_selected_links; analysis NaNs preserved; overrides logged.
- No-input-mutation: snapshot input file hashes/mtimes before+after full run; assert unchanged.
- No marker->link invalidation: assert no V1 output column/text claims a marker invalidates a specific link (mapping_confidence stays in the allowed V1 set).

## 5. End-to-end smoke test (real fixture)

`scripts/smoke_segment_export.py` (non-interactive):
- Load `input/Layer1_QC/QC_671_T1_P1_R1/` + `input/Layer2_Kinematics/671_T1_P1_R1/`.
- Run validation -> assert `safe_to_open`.
- Pick a small window (e.g. frames 1000..2000) and a small link set (e.g. `J004 Neck->Head`, `J020 LThigh->LShin`).
- Build summaries + recommendations; export segment.
- Assert: session loads; frame alignment passes (exact); window summary produced; recommendations produced; export folder created; parquet row count == n_frames_selected * n_links_selected; metadata records alignment + decisions.
- Print the resulting segment folder path.

## 6. Documentation

`docs/POST_LAYER2_SEGMENTATION_NOTEBOOK_README.md` (and a README section) covering: expected input folders; minimal required files; Layer 1 marker QC vs Layer 2 link QC distinction; frame-based alignment; recommendation classes + rules; the six exported segment files; CLI validator usage; limitations; explicit statements that V1 does NOT implement exact marker->link mapping and does NOT run Layer 3.

## 7. Phasing, acceptance, and stop conditions

- Phase 0 (scaffold + contract): structure, pyproject, requirements compile; `pip install -e .` works. Stop if a required column is absent in the real parquet.
- Phase 1 (schemas): enums + column lists import; validated against real parquet header.
- Phase 2 (load): both fixtures load; optional-file warnings work. Test: loading.
- Phase 3 (validate): all checks return structured result; real fixture => `safe_to_open=true`, exact alignment. Tests: identity/alignment/join/duplicates/columns. Stop if integrity critical check fails with no override path.
- Phase 4 (CLI): `validate_segmentation_inputs.py` writes 3 files on real fixture; correct exit codes.
- Phase 5 (qc_events): Layer 1 normalization; frame-level only. Test: normalization. Stop if events can't be expressed at frame level.
- Phase 6 (window_summary): subset + summaries + combined table. Tests: window/summaries.
- Phase 7 (recommendations): 6-class window recompute; J005 flip + J007 blocked verified. Tests: recommendations. Stop if full-session recompute can't reproduce manifest priors.
- Phase 8 (export): six files; NaNs preserved; no mutation. Tests: export + no-mutation + overrides.
- Phase 9 (widgets + notebook): full progressive flow on real session; validation gates frame widget.
- Phase 10 (tests): full suite green.
- Phase 11 (docs + smoke): smoke produces one reference segment; README done.

## 8. Definition of done

- CLI validation works on the real `671_T1_P1_R1` fixture and writes report/summary/checks.
- Notebook uses the SAME validation functions; frame-range widget disabled until validation passes; export blocked on invalid inputs; warnings surfaced + recorded in metadata.
- Validation output is produced/recorded before any segment export; no manual copy/paste validation.
- All required tests pass (loading, validation, identity, alignment, join, window, summaries, all recommendation classes, window recompute, export of six files, only-selected frames/links, NaN preservation, no-input-mutation, override logging, no marker->link invalidation claim).
- End-to-end smoke export produces a `outputs/segments/671_T1_P1_R1/<segment_name>/` folder with all six files and correct parquet row count.
- Layer 1 and Layer 2 inputs provably unmodified.

## 9. Deferred to V2
Exact marker -> bone -> link mapping (Motive CSV header), timeline/plots, auto candidate-window detection, multi-session comparison, interactive body map, video, and any Layer 3 / PCA / JcvPCA / JRW preparation.


 runtime here has no pandas/pyarrow in the base Python (PEP 668 blocks global pip), so implementation will need a virtualenv or pip install --user/--break-system-packages