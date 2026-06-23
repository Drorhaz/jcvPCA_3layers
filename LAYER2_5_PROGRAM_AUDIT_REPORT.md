# Layer 2.5 Segmentation / Pre-JcvPCA Program Audit

> Audit-only deliverable. No code, config, threshold, test, script, report, manifest, output, notebook, or data file was modified to produce this report. All statements are based on reading the source tree, the committed input fixtures, and the committed output artifacts under `Layer2.5_Segmentation/`. Where a claim is interpretation rather than a directly observed fact, it is labelled as such.

Audit date: 2026-06-23
Auditor scope: `Layer2.5_Segmentation/` (code, notebooks, config, inputs, outputs, tests), with reference to `Layer1_motive_qc/`, `Layer2_Motive_Kinematics/`, and `Layer3_JcvPCA/` contracts.

---

## 1. Executive verdict

Layer 2.5 is **not yet a single, general, safe bridge**. It is **two parallel and partly disconnected subsystems** that share input fixtures but not a common safety spine:

1. **A robust *validation/review* subsystem** — package `src/layer2_motive/segmentation/` (`validate_inputs.py`, `load_inputs.py`, `qc_events.py`, `window_summary.py`, `notebook_review.py`). This does session-identity matching, frame alignment, link-manifest join checks, Layer 2 integrity-audit propagation, and input-fingerprint mutation detection. It is the **trustworthy** half. It is driven by `scripts/validate_segmentation_inputs.py`, `scripts/review_segmentation_window.py`, and the `notebooks/post_layer2_segmentation_review.ipynb` notebook.

2. **A separate *export* subsystem** — package `src/pre_jvcpca_review/` (`export_window.py`, `canonical_manifest.py`, `pilot_export_validation.py`, `discovery.py`, `load_layer1.py`, `load_layer2.py`). This is the half that actually **writes the Layer 3-bound JcvPCA matrix**. It contains a good *canonical* export path (`export_pilot_window_for_jvcpca`) **and** a *legacy* J00x-named export path (`export_window_for_jvcpca`).

The decisive finding: **the production notebook `notebooks/pre_jvcpca_review.ipynb` wires its "Export window data" button to the legacy J00x path (`export_window_for_jvcpca`), not the canonical path, and never invokes the robust identity/alignment validator from subsystem (1).** The committed export manifest `outputs/pre_jvcpca_review/session_window/window_export_manifest.json` confirms this: `"feature_naming_policy": "link_id_parent_to_child_axis"` and feature names such as `J004_Neck_to_Head_rx`. So in its current default wiring, Layer 2.5 *can and does* produce Layer 3 matrices whose feature identity carries `J00x`, with **no** L1↔L2 source-recording cross-check, **no** provenance hashing, **no** structured warnings, and **no** cross-session joint-alignment gate.

The canonical machinery to do this safely **exists** but is **not the default**, is **single-session/single-pilot**, and is **not connected** to discovery, provenance, harmonization, or a structured warning system.

**Bottom line:** the architecture is *promising and half-built*. It is **not ready** to be trusted to drive a user from participant/session selection to a canonically aligned, QC-aware, warning-aware, Layer 3-ready matrix without silent mistakes. It is **usable with strong caution** for the single pilot session (671_T1_P1_R1) **only if** the operator deliberately uses the canonical `--pilot-export` CLI path rather than the notebook's export button.

---

## 2. Files and code inspected

### Export subsystem — `src/pre_jvcpca_review/`
- `discovery.py` — path resolution within one folder (misleadingly named; not a discovery/index module).
- `load_layer1.py` — Layer 1 manifest + qc_mask window loader.
- `load_layer2.py` — Layer 2 link manifest, session summary, parquet window slice, link-order resolution.
- `canonical_manifest.py` — pilot feature manifest loader, canonical identity resolution by `parent_canonical`/`child_canonical`/`axis`.
- `export_window.py` — **both** export paths: `export_window_for_jvcpca` (legacy, J00x) and `export_pilot_window_for_jvcpca` (canonical).
- `pilot_export_validation.py` — single-matrix gate + `validate_cross_session_pilot_exports`.
- `pilot_safety_report.py` — per-link safety report (eligibility/jump/mask/NaN → include/caution/exclude).
- `mapping.py`, `events.py`, `tables.py`, `schemas.py`, `export_constants.py`, `layer2_flags.py`, `notebook_ui.py`, `build.py`.

### Validation/review subsystem — `src/layer2_motive/segmentation/`
- `validate_inputs.py` — identity, frame alignment, link join, integrity audit, fingerprints.
- `load_inputs.py`, `schemas.py`, `qc_events.py`, `marker_family.py`, `window_summary.py`, `notebook_review.py`.

### Scripts
- `scripts/build_pre_jvcpca_review.py` (CLI for review tables + `--export-window-only` + `--pilot-export`).
- `scripts/validate_segmentation_inputs.py`, `scripts/review_segmentation_window.py`, `scripts/build_pilot_safety_report.py`, `scripts/validate_pilot_export.py`, `scripts/inspect_jvcpca_parquet.py`.

### Notebooks
- `notebooks/pre_jvcpca_review.ipynb` (the export notebook — focus of this audit).
- `notebooks/post_layer2_segmentation_review.ipynb` (the review notebook).

### Config / inputs / outputs
- `config/group4_upper_body_pilot_feature_manifest.csv` (16 links × rx/ry/rz = 48 features).
- `input/Layer1_QC/QC_671_T1_P1_R1/*`, `input/Layer2_Kinematics/671_T1_P1_R1/*`, `reevluate_project/*`.
- `outputs/pre_jvcpca_review/session_window/*`, `outputs/segmentation_validation/671_T1_P1_R1/*`, `outputs/window_review/*`, `outputs/pilot_review/*`, `outputs/test_export/*`.

### Tests
- `tests/test_canonical_pilot_export.py`, `tests/test_pre_jvcpca_review.py`, `tests/test_validate_inputs.py`, `tests/test_window_summary.py`, `tests/test_qc_events.py`, `tests/test_marker_family.py`, `tests/test_display_tables.py`, `tests/test_notebook_review.py`, `tests/test_load_inputs.py`, `tests/test_schemas.py`, `tests/test_cli.py`.

Schema of the real Layer 2 parquet was inspected directly (read-only) and contains the expected analysis columns: `rx_filtered_analysis`, `ry_filtered_analysis`, `rz_filtered_analysis`, `stage07_jump_status`, `stage07_jump_magnitude_rad`, `stage08_analysis_eligible`, `stage08_mask_reason`, etc.

---

## 3. Layer 2.5 architecture and run path

There are two distinct run paths.

**Path A — review/validation (trustworthy):**
```
scripts/validate_segmentation_inputs.py
  -> layer2_motive.segmentation.load_inputs.load_layer1_qc_folder / load_layer2_export_folder
  -> validate_inputs.run_all_validations  (identity, alignment, joins, integrity, fingerprints)
  -> write validation_report.md / validation_summary.json / validation_checks.csv
notebooks/post_layer2_segmentation_review.ipynb -> review_segmentation_window.py -> window_summary
```

**Path B — JcvPCA export (the matrix producer):**
```
notebooks/pre_jvcpca_review.ipynb  (Export button)
  -> pre_jvcpca_review.export_window.export_window_for_jvcpca   <-- LEGACY J00x path
       -> resolve_layer1 / resolve_layer2 (discovery.py: file existence only)
       -> load_layer1_manifest (n_frames, fps)
       -> load_session_summary (session_id, run_label)
       -> load_link_manifest
       -> load_rotvecs_window_full
       -> build_long_rotvec_export / build_jvcpca_matrix / build_joint_frame_flag_log
       -> write_window_exports (parquet, parquet, csv, json)
```

The **CLI** `build_pre_jvcpca_review.py` additionally exposes `--pilot-export` → `export_pilot_window_for_jvcpca` (the **canonical** path with `validate_before_write`). The notebook does **not** expose this path.

**Architectural problem:** Path A's safety checks (identity, alignment, integrity) and Path B's export are never composed. Path B does its own minimal frame-window check (`_validate_frame_window` against `l1.n_frames`) and proceeds. The robust validator is not a precondition of export.

---

## 4. Layer 1 evidence-only input alignment

**Verdict: usable with caution (good intent, evidence treated correctly; not enforced as a gate).**

Concrete answers to §4 questions:

1. **Union flags not treated as whole-session exclusion?** Correct. `load_qc_mask` simply windows the frame-level flags; nothing converts `flag_gap_0p5`/`status` into a session/window verdict. Review tables report union-mask % as *informational* (`gap_0p5_flagged_frame_percent`, etc. in `tables.window_decision_summary_dataframe`).
2. **Evidence summarized inside the selected window?** Yes — `events.events_in_window` clips Layer 1 gap/artifact events to `[frame_start, frame_end]`.
3. **Relative to body region / features?** Yes — `events.filter_events_for_selected_links` and `mapping.filter_mapping_by_selected_links` scope evidence to the candidate links of the selected joints; `link_joint_review_dataframe` produces per-link regional gap/artifact percentages.
4. **Avoids rejecting an upper-body window for an irrelevant lower-body gap?** Yes, *because Layer 2.5 makes no automatic rejection at all* in the export path. Evidence is descriptive; the user decides. This satisfies the requirement but for the weaker reason that there is no decision logic.
5. **Affected markers and reason codes preserved?** Yes — `NormalizedEvent` carries `raw_marker_or_region`, `reason`, `source_file`; surfaced in `qc_event_review_table.csv`.
6. **Raw evidence distinguished from downstream decisions?** Yes — Layer 1 columns are prefixed `l1_frame_*` in the export flag log and explicitly labelled "regional QC, not link-specific proof" in the notebook.
7. **Window decisions explicit/local/scoped?** There is no automatic window inclusion/exclusion decision in the export path. (The `pilot_safety_report` does emit `include/include_with_caution/exclude_from_pilot` per link, but on full-session statistics, not on the selected window.)
8. **Evidence exported to notebook-readable and machine-readable?** Yes — CSV review tables + notebook HTML render.

**Caveat:** the export flag log joins the **union** qc_mask to every link at the same frame (`build_joint_frame_flag_log` merges `qc_window` on `frame` only). This is regional, not link-specific, and is *labelled as such*, but a careless reader could over-interpret `l1_frame_flag_gap_0p5=True` as "this link is bad." This is a documentation/UX risk, not a logic error.

---

## 5. Layer 2 analysis-clean input alignment

**Verdict: ready (this is the strongest part of the program).**

Answers to §5:

1. **Which Layer 2 file is loaded?** `layer2_session_filtered_rotvecs.parquet` (or fallback `filtered_relative_rotation_vectors.parquet`) via `discovery.resolve_layer2`.
2. **Uses `rx/ry/rz_filtered_analysis`?** Yes — `export_constants.MATRIX_SOURCE_COLUMNS` and the matrix builders read only these for feature values.
3. **Ever uses native filtered values as analysis values?** No for the matrix. The long export *retains* `rx_filtered_native`/`rotvec_norm_filtered_native` as diagnostic columns (clearly named), but the matrix uses analysis columns only. Good separation.
4. **Preserves `stage08_analysis_eligible`?** Yes (flag log default columns).
5. **Preserves `stage08_mask_reason`?** Yes.
6. **Preserves stage07 jump status / magnitude?** `stage07_jump_status` yes (default). `stage07_jump_magnitude_rad` only when `--include-full-l2-audit-columns` is set. By default magnitude is dropped.
7. **`link_id` only as display/traceability?** In the *canonical* path, yes. In the *legacy* path, `link_id` is part of the feature identity (see §3 of central rule below) — a violation.
8. **Uses `parent_canonical` / `child_canonical`?** Yes — read from the link manifest into `LinkRecord`.
9. **Uses Layer 2 run provenance?** Minimal. `run_label` and `session_id` are copied into outputs. `git_commit`, `config_hash`, input checksum are **not** consumed or checked (and Layer 2's own summary shows `"git_commit": null`).
10. **Detects stale/mismatched Layer 2 outputs?** No (export path). The older validator captures size/mtime fingerprints but is not invoked here.
11. **Rejects Layer 2 outputs lacking provenance?** No.
12. **Verifies Layer 2 frame/time range matches the window and Layer 1?** Partially. `_validate_frame_window` checks the window fits within `l1.n_frames`. The grid completeness check (`validate_complete_frame_link_grid`) ensures every requested frame×link exists in the Layer 2 slice. But there is **no** check that Layer 1 `n_frames` equals Layer 2 `frame_count`, nor that they describe the same source recording.

---

## 6. Direct Layer 1 / Layer 2 output discovery and notebook workflow

**Verdict: requires planning (the discovery/index workflow does not exist).**

Despite the filename `discovery.py`, there is **no discovery, indexing, scanning, or pairing**. `discovery.py` only confirms that specific files exist inside *one* directory the caller already chose.

Answers to §6:

1. **Hard-coded paths in the notebook?** Yes. `LAYER1_DIR` and `LAYER2_DIR` both default to `PROJECT_ROOT / "reevluate_project"`; `DATADESCRIPTIONS_PATH` is a hard-coded 671_T1 file. They are editable text widgets, so "no path editing" is **not** achieved.
2. **Auto-discover participants?** No.
3. **List sessions/runs for a participant?** No.
4. **Pair L1 folder with matching L2 folder?** No automatic pairing. The user points both widgets at folders by hand; nothing verifies they correspond.
5. **Fields used to pair?** None in the export path. (The validator subsystem *would* match `l1.run_key == l2.session_id`, but it is not used by export.)
6. **Detect multiple candidate runs?** No.
7. **Newest vs explicit selection?** N/A — no enumeration.
8. **Warn if L1/L2 from different source CSV?** No (export path). The Layer 1 manifest exposes `input_csv` and Layer 2 exposes `source_stage08_parquet`; **neither is compared**.
9. **Warn on different frame ranges/counts/time ranges?** No (export path). The validator does this but is disconnected.
10. **Warn if Layer 2 provenance missing/stale/different hash?** No.
11. **Notebook-friendly participant/session choices?** No — only free-text path fields.
12. **Review without manual path editing?** No.
13. **Selected identity preserved in outputs?** Partially — `session_id`/`run_label` come from the Layer 2 summary, plus resolved source paths in the manifest. There is no participant/timepoint/repetition decomposition.
14. **Manifest records which L1/L2 run folders were used?** Yes — `source_layer1_dir`, `source_layer2_dir`, and resolved source file paths are written to `window_export_manifest.json`.

**Observed evidence:** the committed `window_export_manifest.json` shows `source_layer1_dir` and `source_layer2_dir` both pointing at `.../Layer2.5_Segmentation/reevluate_project` — i.e. L1 and L2 "outputs" came from the *same hand-curated folder*, which is exactly the manual-path pattern the methodology wants to eliminate.

**Recommended implementation plan (do not implement now):**
- Add a real `discovery.py` (or `session_index.py`) that scans configured Layer 1 and Layer 2 output roots:
  - Layer 1 root: e.g. `Layer1_motive_qc/motive_qc/outputs/runs/<run_key>_<timestamp>/` and/or `outputs/batch_runs/<batch>/`.
  - Layer 2 root: e.g. `Layer2_Motive_Kinematics/outputs/layer2_exports/<run_label>/`.
- Parse each run's manifest (`layer1_segmentation_notebook_manifest.json`, `layer2_session_summary.json`) into a **session index** with one row per participant/session/run, with the columns listed in the prompt (`participant_id`, `timepoint`, `part_id`, `repetition_id`, `session_id`, `layer1_run_dir`, `layer2_run_dir`, source files, n_frames/frame ranges/time ranges for both layers, `marker_set_id`, `layer2_config_hash`, `layer2_git_commit`, `is_matched`, `match_warning`).
- Pair by canonical `subject_id + timepoint + part + repetition` (e.g. parse `671_T1_P1_R1`), **then verify** `layer1.input_csv` stem == `layer2.run_label` stem and `n_frames` equality before marking `is_matched=True`.
- Handle duplicates: if >1 run for a session, do **not** auto-pick newest silently — surface both and require explicit choice (record the chosen run dir).
- Expose the index as a `pandas`/`ipywidgets` dropdown cascade (participant → session → repetition → window/scope) so the notebook never needs free-text paths.
- Tests: index build from fixtures, pairing match/mismatch, duplicate-run detection, source-file mismatch detection.

---

## 7. Participant/session joint-alignment and mapping warnings

**Verdict: not ready / requires fix (cross-session joint-alignment is essentially absent).**

Layer 2.5 today operates on **one session at a time**. There is no module that compares two or more sessions' canonical link maps, and no `joint_alignment_report.csv`.

Answers to §7:

1. After selecting a participant, list sessions and their native link maps? **No.**
2. Compare canonical parent-child links across sessions? **No.**
3. Identify links present in all sessions? **No.**
4. Identify links missing from some sessions? **No.**
5. Identify topology changes between sessions? **No.**
6. Warn when a manifest feature exists in one session but not another? **Indirectly and crudely** — `resolve_session_links_from_manifest` raises `ManifestError("Session missing canonical link …")` for the *one* session being processed. There is no cross-session comparison, just a single-session presence check.
7. Warn about extra intermediate links (e.g. T3 `Neck_to_Neck2 + Neck2_to_Head` vs T1/T2 `Neck_to_Head`)? **No.** No composite-topology detection exists.
8. Prevent Layer 3 export when required features are not aligned? **Only within a single session** (ManifestError on missing/ambiguous link). Not across sessions.
9. Distinguish directly comparable from composite? **No.**
10. Avoid silently treating composite as direct? There is **no composite handling at all**, so a composite case would simply fail with `ManifestError` (fail-closed) on the canonical path — acceptable as a stop, but it produces no structured guidance. On the **legacy** path it would silently export whatever links the user checked, including non-comparable ones.
11. Require an explicit harmonization manifest? **No such concept exists.**
12. Produce a joint/link alignment report? **No.**
13. Classify links (direct/composite/not-comparable/missing/ambiguous)? **No.**
14. Require user decision for composite/ambiguous? **No.**

**Risk classification:** Per the prompt's own rule — "If Layer 2.5 can export matrices across sessions without joint-alignment warnings or harmonization manifest, report this as blocking." The legacy notebook path **can** do exactly this. **This is blocking for any multi-session / cross-timepoint comparison.**

**Recommendation:** build a `joint_alignment.py` that, given ≥2 selected sessions' link manifests, emits the `joint_alignment_report.csv` with the fields the prompt specifies (`canonical_link_name`, `present_in_sessions`, `missing_in_sessions`, `directly_comparable`, `requires_composite_mapping`, `not_comparable`, `native_link_ids_by_session`, `topology_warning`, `recommended_action`, `requires_user_decision`), and gate export on it.

---

## 8. Feature manifest and canonical feature resolution

**Verdict: ready for the canonical path; not enforced on the legacy/default path.**

Answers to §8 (1–20):

1. Manifest location: `config/group4_upper_body_pilot_feature_manifest.csv`.
2. Explicit/versioned/human-readable? Human-readable CSV, yes. **Versioning weak** — no version field, no hash; "Group4 upper-body pilot" identity is only in the `notes` text.
3. Specifies intended participant/session/timepoint/task/body-scope assumptions? **No** — there is no scope-binding metadata in the manifest, only `feature_scope=core_candidate` per row. Nothing stops it being used for any session/timepoint.
4. Each entry has `parent_canonical`, `child_canonical`, `axis`, `feature_name`? Yes (plus `canonical_link_name`, `source_layer2_column`).
5. Avoids `joint_id`/`J00x`? Yes — the manifest has no J00x column.
6. Defines exact feature order? Yes — row order, enforced by `expected_pilot_feature_order` / `pilot_feature_order`.
7. Requires complete rx/ry/rz triplets? Yes — `manifest_axes_for_link` requires exactly `[rx, ry, rz]`; validation re-checks triplets per link.
8. Distinguishes direct vs composite/harmonized? **No** — only direct links are representable.
9. Identifies excluded/non-comparable features? Partially — `include_in_pilot` boolean exists, but the committed manifest marks every row `true`; no excluded examples, no non-comparable concept.
10. Documents why included/excluded? Only free-text `notes`.
11. Code rejects missing required features? Yes (`validate_single_pilot_matrix` → `feature_presence`).
12. Rejects extra unapproved features? Yes (canonical path). **No** on legacy path.
13. Rejects incomplete rx/ry/rz triplets? Yes (`axes_per_link`).
14. Prevents duplicate canonical identity? Partially — `resolve_session_links_from_manifest` raises on **ambiguous** session links (two session links for one canonical pair). Duplicate manifest rows for the same parent/child/axis are not explicitly deduped, though `feature_name` uniqueness would surface order mismatches.
15. Records native Layer 2 `link_id` for traceability? Canonical path: `selected_link_ids` recorded in manifest JSON; long/flag outputs keep `link_id`. Yes.
16. Exports both canonical identity and display name? Yes (canonical path: `canonical_link_order`, `feature_order`, `selected_link_names`).
17. Stops if feature identity/order not exact? Yes (canonical path, hard gate).
18. Rejects same display name hiding different parent/child? Yes — resolution is by `(parent_canonical, child_canonical)`, not display string.
19. Rejects/warns inconsistent axis order? Yes (`axes_per_link` forces rx/ry/rz).
20. Fails/warns on features missing or topologically different across sessions? **Single-session only** — fails for the processed session if missing; no cross-session topology comparison (see §7).

**Risk:** "If a manifest can accidentally be used outside its intended scope without warning, report as a risk." The manifest has **no scope binding**, so it can be applied to any session/timepoint (including a T3 template it was never designed for) with no warning. **This is a real risk** — important, not strictly blocking, because the canonical path would fail-closed if a required link were missing, but it could silently succeed on a different session that *happens* to contain the same canonical pairs even if the movement/context differs.

---

## 9. Window selection logic

**Verdict: usable with caution (single-session, frame-only, no session-specific window mapping).**

Answers to §9:

1. Frame, time, or both? **Frame only.** `frame_start`/`frame_end` integers. Time is carried as metadata (`time_sec`) but not selectable.
2. Start/end convention? **Inclusive** on both ends (`frame >= start & frame <= end`; grid expects `range(start, end+1)`).
3. Frame boundaries preserved exactly? Yes.
4. Time boundaries preserved exactly? `time_sec` is carried per row from Layer 2; not independently validated.
5. Confirms window exists in both L1 and L2? L2: yes (grid completeness). L1: only that `frame_end < l1.n_frames`; qc_mask is windowed but missing L1 frames are not failed.
6. Frame/time alignment between L1 and L2? **Not checked** in the export path (see §5.12).
7. Off-by-one risks? Handled for L2 (`_validate_frame_window`: `frame_end >= n_frames` fails, so max valid index is `n_frames-1`). The L1 vs L2 indexing is assumed identical, not verified.
8. Preserves original frame numbers? Yes.
9. Preserves original `time_sec`? Yes.
10. Records boundary source / manual verification status? **No.**
11. Full-window and sub-window selection? Yes (arbitrary `[start,end]`).
12. Prevents accidental mixing of windows across repetitions? **No explicit guard** — relies on single-session processing.
13. Detects interval outside L1/L2 coverage? L2 via grid + `_validate_frame_window`; L1 partially.
14. Reports duration and frame count? Yes (`duration_frames`, `duration_sec`, `n_frames`).
15. Supports session-specific windows (same cue at different frame ranges across sessions)? **No** — there is no per-session window mapping; one `[start,end]` is applied to whatever session is loaded.
16. Avoids assuming one fixed frame range across sessions? **It assumes exactly that** for any multi-session use, because there is no per-session window resolution.

**Risk:** "If Layer 2.5 assumes one fixed frame range across sessions without validation, report as a risk." Today there is no multi-session path, but the moment one is built on this base it would inherit a single fixed window. Flag as **important** for the scaling phase.

---

## 10. Notebook warning / alert system

**Verdict: not ready / requires fix (no structured warning architecture in the export path).**

There is **no** `warnings.py` and no structured warning object in `pre_jvcpca_review`. The export path is **fail-fast via exceptions** (`WindowExportError`, `PilotExportValidationError`, `ValueError`, `ManifestError`). The notebook wraps calls in `try/except` and prints the exception text in red HTML. The robust subsystem (`validate_inputs`) *does* have a graduated model (`ValidationCheck` with `pass`/`warn`/`fail`, `blocking_errors`, `safe_to_open`) — but it is not used by the export notebook.

Answers to §10:

1. Warnings collected into a structured object/table? **No** (export path). Yes in the disconnected validator.
2. Machine-readable, not just stdout? Export path: only exceptions + the `pilot_export_validation_report.json` (canonical path only, on failure/pass). No graduated warning table.
3. Visible in Jupyter? Only as raised error text.
4. Written into export manifest? Errors are not; the manifest records `nan_count_matrix`, `missing_frame_link_combinations`, `nan_policy` (informational), but no warning records.
5. Included in a validation report? Only the canonical path writes `pilot_export_validation_report.json`.
6. Linked to participant/session/window/link/feature/frame? Partially (NaN records carry feature column + frames). No general schema.
7. Severity levels defined? Not in the export path. The validator has `pass/warn/fail`.
8. Compact critical-warning summary before export? **No.**
9. Detailed warning tables for review? **No** (only the descriptive review tables, which are not "warnings").
10. Explicit user approval for strong warnings? **No** — the only user gate is the `ALLOW_NAN_MATRIX` checkbox.
11. Auto-stop on blocking errors? Yes, via exceptions (so export does halt), but the notebook turns this into a printed message rather than a structured block.
12. L1 evidence warnings separated from L2 kinematic warnings? Not as warnings; only as separate review tables.
13. Feature-alignment vs QC warnings separated? **No** (no alignment warnings exist).
14. Topology/harmonization warnings visible? **No** (do not exist).
15. Stale-output/provenance warnings visible? **No** (do not exist in export path).
16. Warnings preserved in final outputs? **No.**

### Warning-coverage matrix

| warning / alert type | currently detected? | visible in notebook? | written to manifest? | severity | should block export? | recommended fix |
|---|---|---|---|---|---|---|
| Window overlaps L1 gap evidence | Yes (review tables) | Yes (review table) | No | info | no | also emit as structured warning record |
| High union-mask burden in window | Yes (%) | Yes | No | info | no | structured record, threshold flag |
| Affected markers outside selected region | Partial (region in tables) | Partial | No | info | no | explicit in-region/out-region flag |
| Affected markers inside selected region | Partial | Partial | No | warn | no (approval) | explicit flag + approval |
| Marker-set prefix change | No | No | No | warn | no | add marker_set_id check |
| Marker-set identity differs across sessions | No | No | No | strong | yes | cross-session marker-set check |
| Large gap evidence irrelevant to features | Partial (scoping) | Partial | No | info | no | structured record |
| Stage 07 jump warning/fail in window | Yes (flag log + tables) | Yes | Partial (flag log) | warn | no (approval) | summarize jump in-window in manifest |
| Stage 08 masked analysis frames in window | Yes (flag log) | Yes | No | warn | depends | summarize masked count in manifest |
| Feature low eligible percent | Yes (pilot safety report, full-session) | If run | No | warn | no (approval) | compute per selected window |
| NaN/inf in analysis-clean values | Yes (hard gate) | Yes (error) | Yes (`nan_count_matrix`) | error | yes (default) | already blocks; keep |
| Provenance missing/stale | No | No | No | strong | yes | add provenance check |
| Native filtered used instead of analysis | N/A (matrix uses analysis) | — | — | error | yes | keep; add explicit assertion in legacy path |
| Required feature missing | Yes (canonical only) | Yes (error) | Yes (report) | error | yes | extend to legacy path |
| Extra unapproved feature | Yes (canonical only) | Yes | Yes (report) | error | yes | legacy path lacks this |
| Incomplete rx/ry/rz triplet | Yes (canonical only) | Yes | Yes | error | yes | legacy path lacks this |
| Feature order mismatch | Yes (canonical only) | Yes | Yes | error | yes | legacy path lacks this |
| Duplicate canonical identity | Partial (ambiguous link) | Yes (error) | No | error | yes | strengthen |
| J00x/joint_id-only identity used | **Not flagged** | **No** | No (silently used) | strong | **yes** | block legacy path for L3 |
| Manifest used outside intended scope | No | No | No | strong | yes | add scope binding + check |
| Link directly matches across sessions | No | No | No | info | no | joint-alignment report |
| Link missing vs another session | No | No | No | strong | yes | joint-alignment report |
| Session has extra intermediate topology | No | No | No | strong | yes | joint-alignment report |
| Direct link needs composite in other template | No | No | No | strong | yes | harmonization manifest |
| Composite attempted without approval | No | No | No | error | yes | harmonization gate |
| Non-comparable link in matrix | No (legacy allows it) | No | No | error | yes | canonical/harmonization gate |
| Multiple L1 runs for session | No | No | No | warn | no (choice) | discovery index |
| Multiple L2 runs for session | No | No | No | warn | no (choice) | discovery index |
| L1/L2 source files mismatch | No (export path) | No | No | strong | yes | pairing check |
| L1/L2 frame ranges mismatch | No (export path) | No | No | strong | yes | pairing check |
| L1/L2 time ranges mismatch | No (export path) | No | No | warn | no | pairing check |
| Missing L1 output | Yes (FileNotFoundError) | Yes (error) | No | error | yes | keep |
| Missing L2 output | Yes (FileNotFoundError) | Yes | No | error | yes | keep |
| Missing L2 provenance | No | No | No | strong | yes | provenance check |
| Stale archived output | No | No | No | warn | no | fingerprint/index |

**Recommendation:** introduce `src/pre_jvcpca_review/warnings.py` with the prompt's `warning_id/severity/category/...` schema, have every stage append records, render a compact "critical before export" summary + detailed tables in the notebook, write all records into `window_export_manifest.json` (and a `window_warnings.csv`), and require explicit approval for `strong` warnings and hard-block on `error`/`blocking`.

---

## 11. Matrix construction logic

**Verdict: ready computationally on the canonical path; the legacy path is structurally fine but feature-identity-unsafe.**

Answers to §11:

1. Rows → matrix rows: one row per frame in `[start, end]` (contiguous).
2. Columns → features: per selected link × {rx,ry,rz}.
3. Metadata separated from feature columns? Yes — `MATRIX_IDENTITY_COLUMNS = [session_id, run_label, frame, time_sec]`; everything else is a feature.
4. Frame/time retained as metadata only? Yes.
5. `session_id`/`run_label` as metadata only? Yes.
6. rx/ry/rz placed in correct feature columns? Yes — `zip(FEATURE_AXES, MATRIX_SOURCE_COLUMNS, strict=True)`.
7. Sorted by frame/time? Yes — frames asserted ascending contiguous.
8. Duplicate frames handled? Yes — `matrix_df["frame"].duplicated()` → error; grid check rejects duplicate frame×link.
9. Missing frames handled? Yes — grid completeness check errors on any missing frame×link.
10. NaN/inf rejected by default? Yes — `build_*_matrix` fails on NaN unless `allow_nan_matrix`; canonical validator additionally fails on inf.
11. `allow_nan_matrix` disabled by default? Yes (default `False`; notebook checkbox default unchecked).
12. Validation fails before writing bad matrices? Canonical path: yes (`validate_before_write` before `write_window_exports`). Legacy path: matrix builder raises before write, but there is **no manifest-membership / canonical-identity gate**.
13. Output columns stable across sessions? Canonical: yes (manifest order). Legacy: depends on selected link IDs and their J00x — **not stable** if J00x differs across sessions.
14. Feature order exactly manifest-defined? Canonical: yes. Legacy: order is "manifest order of session link IDs," i.e. session-local, not a frozen cross-session manifest.
15. All matrices compatible with Layer 3? Canonical: yes. Legacy: only if Layer 3 tolerates J00x-prefixed names and identical J00x across sessions (fragile).
16. Explicitly separates metadata vs PCA features? Yes (constant lists + summary `.md` "Likely metadata/feature columns").
17. Includes a manifest listing feature columns in order? Yes — `feature_order` in `window_export_manifest.json`.
18. Fails if a required manifest feature is unavailable? Canonical: yes. Legacy: there is no required-feature concept; you get whatever you selected.

**Forbidden content check:** The matrix correctly excludes raw markers, quaternions, Euler angles, and metadata-as-features, and uses analysis (not native) values. **However** the legacy path **permits** `J00x`-only-adjacent semantic identity (J00x prefix), and **permits non-comparable links** (the committed example includes lower-body links in an "upper-body pilot" context). Composite features are not representable at all.

---

## 12. QC propagation into Layer 2.5 outputs

**Verdict: ready (rich QC propagation), with the union-mask caveat from §4.**

1. Preserves L1 frame-level QC flags? Yes — `l1_frame_*` columns in `window_joint_frame_flag_log.csv`.
2. Summarizes L1 evidence inside the window? Yes (review tables).
3. Relative to region/features? Yes (per-link regional percentages).
4. Preserves affected markers and reason codes? Yes (`qc_event_review_table.csv`).
5. Preserves `stage08_analysis_eligible`? Yes.
6. Preserves `stage08_mask_reason`? Yes.
7. Logs which links/frames masked? Yes (`block_filter_frame`, `jump_fail_rad_frame` derived columns).
8. Exports a joint/link/frame flag log? Yes (`window_joint_frame_flag_log.csv`).
9. Reports jump warnings/fails in window? Yes (flag log + link review table).
10. Reports L1 gaps/artifacts in window? Yes.
11. Distinguishes raw-marker vs solved-kinematic QC? Yes (`l1_frame_*` vs `stage0x_*`).
12. Gives Layer 3 enough provenance to explain accept/reject/review? Partially — provides evidence, but no recorded decision rationale and no provenance hashes.
13. Avoids over-interpreting union mask as whole-window decision? Yes (no auto-decision), but the replicated `l1_frame_*` per link is a UX trap (see §4 caveat).

---

## 13. Latest Layer 2.5 output files reviewed

Reviewed under `outputs/pre_jvcpca_review/session_window/` (the latest export) plus validation/review outputs.

| output file | purpose | producer | key fields | human-readable | machine-readable | Layer 3 ready | issues |
|---|---|---|---|---|---|---|---|
| `window_jvcpca_matrix.parquet` | JcvPCA input matrix | `export_window.write_window_exports` (legacy) | `session_id,run_label,frame,time_sec` + `J0xx_parent_to_child_{rx,ry,rz}` | no | yes | **No (J00x identity)** | feature identity carries J00x; mixes upper+lower body; no canonical gate |
| `window_jvcpca_matrix_summary.md` | Human matrix summary | inspect/summary script | columns, dtypes, NaN/inf, metadata vs feature | yes | partly | n/a | confirms J00x naming; no canonical identity block |
| `window_jvcpca_matrix_preview.xlsx` | Preview | export/inspect | sample rows | yes | no | n/a | convenience only |
| `window_selected_rotvecs_long.parquet` | Long per-frame-per-link rotvecs | `build_long_rotvec_export` | identity + raw/native/analysis rotvecs + family | no | yes | supportive | good; retains diagnostics clearly named |
| `window_joint_frame_flag_log.csv` | Per-frame-per-link QC flags | `build_joint_frame_flag_log` | `l1_frame_*`, `stage07/08_*`, derived masks | yes | yes | supportive | union L1 flags replicated per link (labelled) |
| `window_export_manifest.json` | Export provenance/manifest | `build_export_manifest` | source dirs/files, `feature_order`, naming policy, nan policy | yes | yes | partial | **no checksums/hashes; no warnings; `feature_naming_policy=link_id_parent_to_child_axis`** |
| `link_joint_review_table.csv` | Per-link L1/L2 evidence | `tables.link_joint_review_dataframe` | regional gap/artifact %, jump/block % | yes | yes | review | good |
| `qc_event_review_table.csv` | Per-event L1 evidence | `tables.qc_event_review_dataframe` | frames, qc_type, reason, marker, mapping | yes | yes | review | good |
| `qc_evidence_summary_table.csv` | Aggregated L1 evidence | `tables.qc_evidence_summary_dataframe` | counts, durations, families | yes | yes | review | good |
| `window_decision_summary.csv` | One-row window summary | `tables.window_decision_summary_dataframe` | selections, union %, jump/block % | yes | yes | review | informational only; no decision |
| `mapping_logic_table.csv` | Marker→bone→link mapping | `mapping.build_mapping_table` | mapping source/status/level | yes | yes | review | heuristic if no DataDescriptions |
| `outputs/segmentation_validation/.../validation_summary.json` + `.md` + `.csv` | Identity/alignment/integrity gate | `validate_inputs` | identity, frame alignment, 43 checks | yes | yes | **gate (but disconnected)** | strong content; not invoked by export path |
| `outputs/pilot_review/group4_upper_body_pilot_safety_report.csv` | Per-link safety recs | `pilot_safety_report` | eligible %, jump/mask, NaN, recommendation | yes | yes | review | full-session, not per-window |

**Cross-output consistency:** the export manifest and matrix summary agree (52 columns, 48 features, 0 NaN). The `validation_summary.json` (from the validator subsystem) shows exact frame alignment 0..30603 and identity match — good, but for the *fixture* folder, produced by a different command than the export.

---

## 14. Cross-session validation

**Verdict: requires fix (exists only for the canonical pilot path; string/order-based; no semantic re-derivation; no direct-vs-composite check).**

`validate_cross_session_pilot_exports` (in `pilot_export_validation.py`) does:
- Confirms each export's feature columns equal the pilot manifest `pilot_feature_order` (string compare).
- Confirms `feature_naming_policy == canonical_parent_child_axis` in the export manifest JSON.
- Confirms recorded `feature_order` equals the reference order.

Answers to §14:

1. Identical feature columns? Yes (string compare to manifest reference).
2. Identical order? Yes.
3. Identical canonical identity (not just names)? **Indirectly** — because the canonical feature names *are* `parent_to_child_axis`, equal names imply equal canonical identity *for canonical-path exports*. It does **not** re-derive identity from each session's link manifest; it trusts the recorded names.
4. Metadata schema? **Not checked.**
5. NaN/inf status? Not in the cross-session function (the single-matrix gate does this per export).
6. Frame counts/durations? **Not checked.**
7. L1/L2 provenance consistency? **No.**
8. Windows within intended scope? **No.**
9. Clear pass/fail report? Yes (writes a report on failure).
10. Stops Layer 3 export on failure? It raises, but it is a **post-hoc** check over already-written export dirs, not an in-line export gate, and **nothing in the notebook calls it**.
11. Detects stale/mismatched Layer 2 provenance? **No.**
12. Detects incompatible L1 marker-set evidence? **No.**
13. Rejects string-equal but semantically-different identity? For **legacy** exports (J00x names), this function would reject them anyway because their names ≠ the canonical reference — but that is a side effect, not a semantic safeguard. It would **not** catch two canonical-path sessions where a session's link manifest mislabels parent/child, because it trusts recorded names.
14. Rejects when required features unavailable in one session? Per-session single-matrix gate yes; cross-session yes by order mismatch.
15. Rejects topology changes requiring composite mapping? **No** — no composite concept.

**Risk:** "If cross-session validation can pass while semantic identities differ, report as blocking" and "if it passes without checking direct-vs-composite comparability, report as blocking." The current check passes on name/order alone and has **no direct-vs-composite check** → **blocking for cross-session/cross-template use.**

---

## 15. Safety / review report logic

**Verdict: usable with caution (a good per-link safety report exists, but full-session not per-window, and it is not wired into the export gate or notebook).**

`pilot_safety_report.build_pilot_safety_report` produces, per session × per canonical link:
- `axis_triplet_present`, `n_frames`, `eligible_percent`, `jump_fail_count`, `jump_warning_count`, `masked_frame_count`, `nan_inf_count_analysis`, and a `recommendation` ∈ {`include`, `include_with_caution`, `exclude_from_pilot`} with a `reason`.

Answers to §15:

1. Lists proposed links/features? Yes.
2. Triplet completeness? Yes.
3. Eligible percent? Yes.
4. Jump warnings/fails? Yes.
5. Masked frame count? Yes.
6. NaN/inf count? Yes.
7. L1 evidence relevant to selected features? **No** — this report is Layer-2-only; L1 evidence lives in the separate review tables.
8. Recommends include/caution/exclude? Yes.
9. Evidence-based, not hidden? Yes — thresholds are explicit in `_recommend_link` (NaN→exclude; jump fail / warning / masked / eligible<90% → caution).
10. Avoids final scientific decisions? Yes — recommendations, not enforced verdicts.
11. Flags distal hand/forearm risks? Indirectly via jump/mask counts; the manifest notes "review jump history" for `*FArm_to_*Hand`.
12. Separates evidence from final decisions? Yes.
13. Flags topology/feature-availability issues? Only "link absent from session parquet" → exclude. No topology classification.
14. Surfaces warnings in notebook before export? **No** — the export notebook never displays this report.

**Gaps:** it computes over the **full session**, not the selected window; it does not fuse Layer 1 evidence; and it is not a precondition of export.

---

## 16. Template / topology harmonization readiness

**Verdict: not ready / requires planning (no harmonization concept exists).**

1. Direct links matched by `parent_canonical + child_canonical`? Yes (single-session).
2. Composite mappings representable? **No** — would require new logic and a harmonization manifest.
3. Non-comparable links excluded clearly? Only via `include_in_pilot=false`/absence; no "not_comparable" class.
4. Distinguishes direct / composite / not-comparable? **No.**
5. Keeps non-harmonized template differences out of Layer 3? Canonical path fails-closed if a canonical pair is missing (good); legacy path does **not** (bad).
6. Warns when neck/spine/topology differs? **No.**
7. Requires user approval before composite? **No composite path exists.**
8. Prevents composite being treated as direct? N/A (no composite) — but legacy path would happily export whatever the user checked.
9. Export manifest states direct/composite/excluded? **No** — only direct features exist; the field is absent.
10. Warns the notebook user when sessions need harmonization? **No.**

**Statement (as required):** *Cross-template comparison is currently possible only if every required canonical parent→child link exists identically in every session (pure direct comparability). The program has no mechanism to prove this across sessions, and no explicit harmonization manifest for composite mappings (e.g. T3 `Neck→Neck2→Head` vs T1/T2 `Neck→Head`, or T3 multi-segment spine vs T1/T2 `Ab→Chest`). Therefore cross-template comparison is NOT currently supported safely.*

---

## 17. Existing tests and missing tests

### Present (good coverage)
- **Canonical resolution:** `test_resolve_links_by_parent_child_not_joint_id`, `test_pilot_export_uses_canonical_feature_names`, `test_manifest_loads_with_canonical_names` (`tests/test_canonical_pilot_export.py`).
- **Manifest order rejection:** `test_pilot_export_validation_rejects_bad_order`.
- **NaN rejection:** `test_pilot_export_fails_on_nan_without_allow`; `test_window_export_for_jvcpca` (legacy) asserts fail-fast then allow-NaN.
- **Identity/alignment (validator subsystem):** `tests/test_validate_inputs.py` — identity pass/mismatch/force, run_label-not-identity, frame alignment exact/mismatch-overlap, duplicate frame×link, link-manifest join pass/fail, fingerprint mutation, missing parquet column.
- **Window math:** `tests/test_window_summary.py` (inclusive boundaries, brute-force parity, 50-link full session, refuse invalid validation, no-input-mutation).
- **QC events / mapping:** `tests/test_qc_events.py`, `tests/test_marker_family.py` (incl. `test_no_link_id_in_result`).
- **Display/CLI:** `tests/test_display_tables.py`, `tests/test_cli.py`, `tests/test_notebook_review.py`.

### Notable existing test that *enshrines the risk*
- `test_window_export_feature_naming_policy` and `test_window_export_for_jvcpca` **assert** `feature_naming_policy == "link_id_parent_to_child_axis"` (J00x naming). I.e. the J00x legacy behaviour is a *tested contract*, not a deprecation. There is **no** test asserting the legacy path is blocked/marked unsafe for Layer 3.

### Missing tests (recommended; do not implement)
- J00x mismatch does not affect canonical matching (only canonical resolution is tested; no cross-session J00x-shift test).
- Same J00x but different parent/child fails.
- Same parent/child but different axis order corrected or rejected (partially via `axes_per_link`; no negative test).
- Missing one axis fails (no explicit negative test for a 2-axis link).
- Extra unapproved link fails (canonical gate has the code; add explicit test).
- A session cannot pass a manifest unless explicitly in scope (no scope-binding exists → no test).
- Cross-template direct links pass if canonical parent/child/axis match.
- Composite links cannot be silently treated as direct equivalents.
- L1 QC handoff missing `marker_set_id` reported.
- L2 provenance mismatch reported.
- NaN/inf in matrix fails by default (covered for NaN; add inf via legacy path).
- Discovery detects multiple candidate runs and requires explicit choice/warning.
- L1/L2 source-file mismatch reported.
- Joint-alignment report flags composite topology.
- Composite mapping requires explicit user approval.
- Notebook warning objects written to manifest/output.
- Blocking warnings prevent export.
- **New, specifically recommended:** a test asserting that the legacy `export_window_for_jvcpca` either (a) refuses to run for Layer-3-bound output, or (b) stamps the manifest with `layer3_safe=false`.

---

## 18. Program-level audit on available data

Only **one** participant/session is materially present: **671_T1_P1_R1** (fixtures in `input/` and `reevluate_project/`; the only Layer 2 export folder). No T2/T3 or other participants are available in Layer 2.5, so multi-session behaviour can be assessed only architecturally (and is found absent — §7, §14, §16).

Concrete export reviewed (`outputs/pre_jvcpca_review/session_window/window_export_manifest.json` + matrix summary):

| field | value |
|---|---|
| session_id | 671_T1_P1_R1 |
| timepoint | T1 |
| repetition | R1 |
| start_frame / end_frame | 14280 / 15240 |
| duration | 961 frames (8.0083 s @ 120 Hz) |
| n_rows | 961 |
| n_features | 48 |
| feature_count_expected (pilot) | 48 (canonical) |
| feature_count_actual | 48 (but **J00x-named**, and links are 16 mixed upper+lower body, not the upper-body pilot set) |
| NaN count | 0 |
| inf count | 0 (not separately asserted on legacy path) |
| L1 evidence burden in window | not summarized in this export (review tables are a separate run) |
| L1 affected markers in window | not in this export |
| L1 evidence relevant to features | not in this export |
| L2 masked/link burden | flag log present (separate from manifest summary) |
| jump warnings/fails in window | flag log carries `stage07_jump_status`; not summarized in manifest |
| feature manifest status | **legacy: no manifest membership enforced** |
| joint-alignment status | n/a (single session) |
| validation status | export-path: only window/grid/NaN checks passed; identity/provenance not checked |
| L1/L2 pairing status | both dirs = same `reevluate_project` folder (manual) |
| warnings produced | none structured |
| verdict | **usable with caution for computation; not canonically safe for cross-session L3** |

Per-session table (only one session available):

| session | rows | features | feature_order_match | canonical_alignment_ok | nan_inf_ok | layer1_evidence_ok | layer2_qc_ok | output_pairing_ok | validation_status | warning_status | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 671_T1_P1_R1 (legacy export) | 961 | 48 | session-local only | **No (J00x identity)** | Yes | Yes (separate tables) | Yes | manual (same folder) | partial | none | usable with caution |

Note the inconsistency: the link manifest and `config` describe a **16-link upper-body pilot**, but the committed export selected **16 links spanning upper and lower body** (`LShin->LFoot`, `671->LThigh`, etc.). The legacy path permitted this without warning.

I did **not** run the export scripts to regenerate outputs, to honour the no-overwrite rule; I read the committed artifacts and the parquet schema (read-only) instead.

---

## 19. Trustworthiness for Layer 3 JcvPCA

1. Matrices clean and numeric? Yes (0 NaN/inf in the committed example).
2. Metadata separated? Yes.
3. Feature columns identical and ordered? Within a session yes; **across sessions, not guaranteed on the legacy path**.
4. Semantically identical by canonical parent/child/axis? **Only on the canonical path. The legacy/default notebook path uses J00x-prefixed identity.**
5. Direct / composite-harmonized / excluded? Only direct; no composite/harmonization; legacy allows non-comparable.
6. Local QC problems preserved? Yes.
7. Bad windows rejected or marked? Evidence preserved; no automatic rejection/marking decision recorded.
8. Provenance sufficient? Source paths yes; **checksums/hashes/commit no**.
9. Feature manifest frozen and included? Canonical: yes. Legacy: no frozen manifest.
10. L1 evidence summarized without over-interpreting union masks? Yes.
11. L2 analysis-clean used (not native/debug)? Yes.
12. Participant/session selection recorded and reproducible? Partially (identity recorded; selection via manual paths).
13. Warning records preserved? No.
14. Matrix safe for JcvPCA computation? Computationally yes; semantically risky on legacy path.
15. Matrix safe for scientific interpretation? **Not without canonical identity + cross-session alignment + provenance.**

**Separate verdicts:**
- **Computationally ready for Layer 3:** YES (single session, canonical path; also legacy path produces a clean numeric matrix).
- **Scientifically usable with caution:** ONLY via the canonical `--pilot-export` path, single session, with manual identity confidence.
- **Not ready:** for cross-session / cross-template comparison, and for the default notebook export wiring (J00x identity, no provenance, no warnings).

---

## 20. Weak points and risks

1. **Legacy J00x export is the notebook default** (blocking for L3 semantic safety).
2. **No L1↔L2 source-recording cross-check in the export path** (blocking) — robust validator exists but is disconnected.
3. **No discovery/index/pairing** (requires planning) — manual paths, no participant/session enumeration.
4. **No provenance hashing** (`git_commit` null, no config/input hash) (important).
5. **No cross-session joint-alignment report / no harmonization manifest** (blocking for multi-session).
6. **Cross-session validation is name/order-only and post-hoc, not wired in** (blocking for multi-session).
7. **No structured warning architecture in the export path** (important).
8. **Manifest has no scope binding** (important) — can be misapplied to other sessions/templates.
9. **Window selection is single-session, frame-only, no per-session window mapping** (important for scaling).
10. **Pilot safety report is full-session, not per-window, and not surfaced in the notebook** (important).
11. **Two parallel subsystems with overlapping but inconsistent contracts** (important) — duplicated `discovery`/load logic, divergent `feature_naming_policy` constants between modules (`export_window.FEATURE_NAMING_POLICY = "link_id_parent_to_child_axis"` vs `canonical_manifest.CANONICAL_NAMING_POLICY = "canonical_parent_child_axis"`).
12. **Union L1 flags replicated per link in the flag log** (minor/UX) — labelled but easy to over-read.
13. **A passing test suite enshrines the J00x naming as a contract** (important) — "tests pass" must not be read as "L3-safe."

---

## 21. Recommended changes based on audit findings

For each: issue / evidence / why / recommended update / affected module / risk of change / risk of inaction / blocks L3? / user approval? / priority.

### R1 — Make the canonical path the only Layer-3 export; demote legacy J00x
- Issue: notebook exports via `export_window_for_jvcpca` (J00x identity).
- Evidence: `notebooks/pre_jvcpca_review.ipynb` imports/calls `export_window_for_jvcpca`; `window_export_manifest.json` shows `feature_naming_policy: "link_id_parent_to_child_axis"` and `J004_Neck_to_Head_rx`.
- Why: J00x can shift across sessions/templates and silently corrupt cross-session L3 input.
- Update: rewire the export button to `export_pilot_window_for_jvcpca`; mark legacy output `layer3_safe=false` in its manifest and forbid it as L3 input; keep legacy only for ad-hoc diagnostics.
- Affected: `notebooks/pre_jvcpca_review.ipynb`, `export_window.py`, `build_pre_jvcpca_review.py`.
- Risk of change: low/medium (notebook UX change).
- Risk of inaction: silent wrong-joint comparison.
- Blocks L3: **Yes.** User approval: yes (changes default behaviour). Priority: **critical.**

### R2 — Wire identity/alignment/provenance validation into export
- Issue: export never runs `validate_inputs.run_all_validations`.
- Evidence: `export_window.py` loads L1/L2 independently; no identity/frame-count comparison; `validation_summary.json` is produced only by the disconnected CLI.
- Why: prevents pairing the wrong L1 with the wrong L2 / stale outputs.
- Update: call the validator (or an equivalent) as a precondition; block on identity/alignment fail; record results in the export manifest.
- Affected: `export_window.py`, `validate_inputs.py`, notebook.
- Risk of change: medium. Risk of inaction: wrong-session matrices. Blocks L3: **Yes.** Approval: no. Priority: **critical.**

### R3 — Real discovery/session index + notebook dropdowns
- Issue: no discovery; manual paths.
- Evidence: `discovery.py` only checks file existence; notebook defaults to `reevluate_project`.
- Why: eliminate manual-path mistakes; enable scaling.
- Update: implement the §6 session-index plan; drive the notebook from the index.
- Affected: new `discovery.py`/`session_index.py`, notebook, tests.
- Risk of change: medium. Risk of inaction: operator error. Blocks L3: no (but blocks safe scaling). Approval: no. Priority: **important.**

### R4 — Joint-alignment report + harmonization manifest + gate
- Issue: no cross-session alignment, no composite handling.
- Evidence: no `joint_alignment*` symbols in `src/`; `resolve_session_links_from_manifest` is single-session.
- Why: cross-template comparison is unsafe without it.
- Update: build `joint_alignment.py` → `joint_alignment_report.csv`; add a harmonization manifest schema; require approval for composite; block non-comparable links.
- Affected: new module, `canonical_manifest.py`, export gate, tests.
- Risk of change: medium/high. Risk of inaction: comparing non-equivalent joints. Blocks L3 (multi-session): **Yes.** Approval: yes. Priority: **critical (before any multi-session L3).**

### R5 — Structured warning architecture
- Issue: no structured warnings; exceptions + red text only.
- Evidence: no `warnings.py`; notebook `try/except` prints.
- Why: surface graduated risks; require approval for strong warnings.
- Update: `warnings.py` with the prompt schema; render summary + tables; write to manifest + `window_warnings.csv`; approval gate for `strong`, hard-block `error`.
- Affected: new module, export functions, notebook, tests.
- Risk of change: medium. Risk of inaction: silent risky exports. Blocks L3: partially. Approval: no. Priority: **important.**

### R6 — Provenance hashing and stale-output detection
- Issue: no checksums/commit/config hash consumed.
- Evidence: `window_export_manifest.json` has paths but no hashes; L2 summary `git_commit: null`.
- Why: detect stale/mismatched inputs.
- Update: capture input fingerprints (the validator already has `_file_fingerprint`) into the export manifest; require L2 provenance fields; warn/stop when missing.
- Affected: `export_window.py`, `validate_inputs.py`. Risk of change: low. Risk of inaction: stale-input corruption. Blocks L3: no (strong warn). Approval: no. Priority: **important.**

### R7 — Manifest scope binding
- Issue: manifest applies to any session/template.
- Evidence: `config/...csv` has no scope columns; all rows `include_in_pilot=true`.
- Why: prevent applying the upper-body pilot to an out-of-scope session/template.
- Update: add `intended_template`, `intended_timepoints`, `intended_body_scope`, `manifest_version` columns + a scope check at load.
- Affected: config CSV, `canonical_manifest.py`, tests. Risk of change: low. Risk of inaction: silent misapplication. Blocks L3: no. Approval: yes (config change). Priority: **important.**

### R8 — Per-window safety report fused with L1 evidence, surfaced pre-export
- Issue: safety report is full-session, L2-only, not shown in notebook.
- Evidence: `pilot_safety_report.build_pilot_safety_report` iterates whole-session frames.
- Why: the user should see windowed include/caution/exclude + L1 evidence before exporting.
- Update: compute over the selected window; merge L1 regional evidence; display before the export button.
- Affected: `pilot_safety_report.py`, notebook. Risk of change: low. Blocks L3: no. Approval: no. Priority: **nice-to-have/important.**

### R9 — Unify the two subsystems
- Issue: duplicated/divergent contracts (`discovery`, naming-policy constants, load logic).
- Evidence: `layer2_motive.segmentation` vs `pre_jvcpca_review`.
- Why: one safety spine; avoid drift.
- Update: consolidate loaders/validators; single naming policy.
- Affected: both packages, scripts, notebooks, tests. Risk of change: high. Blocks L3: no. Approval: yes. Priority: **important (debt).**

### Separation
- **Critical before Layer 3:** R1, R2, R4 (for multi-session).
- **Important before scaling participants:** R3, R5, R6, R7, R9.
- **Nice-to-have:** R8.

---

## 22. What should be reviewed in the Jupyter notebook

The operator should, before trusting any export, verify in-notebook:
1. That export uses the **canonical** path (manifest-driven), not the J00x legacy button.
2. That the displayed `session_id`/`run_label` match the intended participant/timepoint/repetition (currently must be eyeballed against manual paths).
3. The **per-window** Layer 2 safety table (eligible %, jump fail/warning, masked frames, NaN/inf) — currently must be generated separately.
4. The Layer 1 evidence tables scoped to the selected joints (`link_joint_review_table.csv`, `qc_event_review_table.csv`).
5. The `feature_order` and that it equals the frozen manifest order (currently shown only as raw J00x names on the legacy path).
6. NaN policy (keep `Allow NaN` **unchecked** for L3-bound exports).
7. (When multi-session arrives) the joint-alignment report and any harmonization decisions — **does not exist yet**.

---

## 23. Open questions for the user

1. Should the legacy J00x export be **removed** for Layer 3, or retained as an explicitly-marked diagnostic only?
2. What are the authoritative **discovery roots** for Layer 1 and Layer 2 outputs (the canonical run directories), so a real index can be built?
3. For T1/T2/T3 comparisons, do you want **direct-only** comparability (drop non-matching links) or **composite harmonization** (e.g. compose T3 `Neck→Neck2→Head` to compare with T1/T2 `Neck→Head`)? The latter requires a scientific decision on how composite rotations are combined.
4. Is the "Group4 upper-body pilot" the intended frozen feature set, given the committed export actually exported mixed upper+lower-body links?
5. Should window selection become **per-session** (cue-aligned) rather than a single absolute frame range?
6. Do you require git-commit/config-hash provenance to be **mandatory** (hard block) or **warn-only** when missing?

---

## 24. Independent auditor observations beyond the requested questions

**Observation 1 — The "discovery.py" name is misleading.**
Why it matters: a future maintainer may assume discovery/pairing exists because the file is named `discovery.py`, when it only resolves files in one folder. Severity: important. Next step: rename to `path_resolve.py` and reserve `discovery.py` for the real index. Requires user decision: no.

**Observation 2 — Divergent naming-policy constants coexist.**
`export_window.FEATURE_NAMING_POLICY = "link_id_parent_to_child_axis"` and `canonical_manifest.CANONICAL_NAMING_POLICY = "canonical_parent_child_axis"` live in the same package and are both written into manifests depending on path. Why it matters: downstream Layer 3 code must branch on policy or risk mis-parsing identity. Severity: important. Next step: single canonical policy; legacy stamped `layer3_safe=false`. User decision: no.

**Observation 3 — The committed pilot export contradicts the pilot's own definition.**
The "upper-body pilot" manifest is 16 upper-body links, yet `window_export_manifest.json` exported 16 links including `LShin→LFoot`, `LThigh→LShin`, `671→LThigh`, etc. Why it matters: shows the legacy path imposes no scope discipline; an analyst could PCA a mixed upper+lower set thinking it is the pilot. Severity: blocking (for scientific correctness of that artifact). Next step: regenerate via canonical path; treat the committed matrix as not L3-safe. User decision: yes.

**Observation 4 — Layer 1 `session_id` vs Layer 2 `session_id` string mismatch.**
L1 manifest `session_id = "T1_P1_R1"` while its `run_key = "671_T1_P1_R1"`; L2 `session_id = "671_T1_P1_R1"`. The robust validator correctly matches on `run_key == session_id`, but the export path reads `l2` identity and never reconciles with `l1`. Why it matters: a naive identity check on `session_id` strings alone would *fail* a correct pairing or *pass* a wrong one. Severity: important. Next step: standardize identity keys across layers; document the canonical key. User decision: maybe.

**Observation 5 — `time_sec` is trusted, never validated.**
The matrix carries `time_sec` from Layer 2 with no monotonicity/spacing check and no comparison to Layer 1 time. Why it matters: if Layer 2 time were corrupted, it would silently propagate. Severity: minor (frame is canonical join key). Next step: add a monotonic/Δt sanity check. User decision: no.

**Observation 6 — Heuristic marker mapping when DataDescriptions absent.**
`mapping.build_mapping_entry` falls back to `671:`-prefix heuristics with no warning severity attached. Why it matters: evidence-to-link attribution could be wrong, weakening the L1 evidence tables. Severity: minor/important. Next step: emit a structured warning when mapping is heuristic. User decision: no.

**Observation 7 — Outputs directory is full of ad-hoc smoke/debug runs.**
`outputs/notebook_review/` and `outputs/window_review/` contain many `smoke_*`, `debug_*`, `investigate_q`, `verify_fix_now` folders. Why it matters: these can be mistaken for real deliverables; provenance hygiene is weak. Severity: minor. Next step: separate `outputs/_scratch/`. User decision: no.

**Observation 8 — Excel preview generation.**
`window_jvcpca_matrix_preview.xlsx` exists in outputs but no producer is in the export functions I read (likely an inspect script). Why it matters: undocumented output provenance. Severity: minor. Next step: document/locate the producer. User decision: no.

**Observation 9 — Passing tests give false confidence.**
The suite passes and even *locks in* J00x naming. Per the prompt's own warning, this must not be read as L3-safety. Severity: important. Next step: add the "legacy path is not L3-safe" test (R-tests in §17). User decision: no.

---

## 25. Final verdict

### Per-area verdicts

| area | verdict |
|---|---|
| Layer 1 evidence-only input alignment | **usable with caution** |
| Layer 2 analysis-clean input alignment | **ready** |
| Layer 1 / Layer 2 direct loading and discovery | **requires fix** (loading ok; discovery/pairing absent) |
| Notebook participant/session selection workflow | **requires planning** |
| Window selection | **usable with caution** (single-session, frame-only) |
| Feature manifest architecture | **usable with caution** (good schema; no scope binding; not default) |
| Canonical feature resolution | **ready** (canonical path) / **requires fix** (legacy default in notebook) |
| Participant/session joint-alignment warning system | **requires fix** (absent) |
| Structured warning / alert system | **requires fix** (absent in export path) |
| Matrix construction | **ready** (canonical) / **usable with caution** (legacy identity) |
| QC propagation | **ready** |
| Cross-session validation | **requires fix** (name/order-only, post-hoc, not wired, no composite) |
| Template / topology harmonization readiness | **requires planning** (absent) |
| Layer 3 compatibility | **usable with caution** (canonical path, single session) / **not ready** (default notebook path, multi-session) |

### Layer 2.5 outputs verdict
**Usable with caution — and only via the canonical `--pilot-export` path, for a single session, with manual identity confidence.**

The caution, stated exactly:
1. The **default notebook export produces J00x-identity matrices** with no canonical/manifest gate — not L3-safe for cross-session work.
2. There is **no enforced L1↔L2 source-recording / provenance check** in the export path.
3. There is **no cross-session joint-alignment or harmonization** — multi-session/cross-template comparison is unsafe today.
4. There is **no structured warning system** to stop or flag risky exports in the notebook.
5. Provenance is **path-level only** (no hashes/commit), so stale inputs are undetectable.

### Overall program verdict
**Layer 2.5 program is: NOT READY** as a general, safe, scalable bridge.
It is **usable with caution** as a *single-session pilot tool* when the operator deliberately bypasses the notebook's legacy export button and uses the canonical export path with manual identity verification. The canonical building blocks are sound; the program becomes trustworthy only after R1–R2 (critical, single-session safety) and R4 (critical, multi-session), supported by R3/R5/R6/R7 for safe scaling.
