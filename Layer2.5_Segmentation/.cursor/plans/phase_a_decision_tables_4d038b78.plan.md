---
name: Phase A+ Decision Tables
overview: "Implement the Phase A+ \"UX / marker-family checkpoint\" of the revised decision-scope design on top of the already-implemented load/validate/window-summary foundation: add gap policy, QC-evidence policy, link/joint export scope, a marker-family overlay with OPTIONAL session-level DataDescriptions enrichment plus heuristic fallback, and migrate the window-review CLI to emit the revised compact decision tables (QC Event Review Table + Link/Joint Decision Table) while keeping full audit intact. The pipeline works fully with or without a DataDescriptions file. The approved-template mapping library, cross-session verification, and mapping-approval workflow remain deferred to Phase B."
todos:
  - id: schemas
    content: "Extend schemas.py: joint-family list, Phase A+ mapping_source/mapping_confidence/template_mapping_status value sets, GAP_POLICIES, EXPORT_SCOPES (incl. all_links_audit), evidence-type sets, policy dataclasses, and the five revised display-table column tuples."
    status: completed
  - id: marker_family
    content: Create marker_family.py with optional session DataDescriptions parsing (load_session_datadescriptions_marker_map, normalize_marker_name, MarkerFamilyMapper(optional_marker_to_bone_map=None), map_marker_to_family) + heuristic fallback + tests/test_marker_family.py.
    status: completed
  - id: qc_events
    content: Add normalized_marker_name + attached_bone(+canonical) + family overlay columns to the Layer 1 event table via marker_family.py; update tests/test_qc_events.py.
    status: completed
  - id: window_summary
    content: Add gap-policy-aware counting and the five display-table builders to window_summary.py; migrate write_window_review_outputs to the revised file names keeping combined_qc_events.csv as audit.
    status: completed
  - id: cli
    content: Add --gap-policy, --export-scope (all_links_audit), --l1-evidence, --l2-evidence, --mapping-version, and an OPTIONAL ACTIVE --datadescriptions to review_segmentation_window.py; thread policies + mapper through and record choices in JSON/report.
    status: completed
  - id: tests
    content: Add tests/test_display_tables.py (gap policy, export scope, unmapped visibility, display<audit, no exact link id for L1) and DataDescriptions present/absent tests; update tests/test_window_summary.py for renamed outputs.
    status: completed
  - id: smoke
    content: Run strict vs relaxed + core vs broader export-scope + with/without DataDescriptions smoke on 671_T1_P1_R1, pytest, ruff; produce the Phase A+ stop-and-report.
    status: completed
isProject: false
---

## 0. What changed: Phase A -> Phase A+

Previously DataDescriptions parsing was fully deferred to Phase B; Phase A only added placeholder mapping fields and an inert `--datadescriptions` flag. This revision upgrades that to **Phase A+**: minimal optional session-level DataDescriptions parsing is implemented now, but the pipeline still runs fully without it.

Principle:

```text
If a DataDescriptions file is provided:
  parse it -> extract marker -> attached bone
  use it before heuristic marker-family mapping
  record mapping_source = session_datadescriptions_optional (unverified)
If no DataDescriptions file is provided:
  fall back to heuristic / body_region_group / unmapped
  continue normally
```

Still deferred to Phase B (NOT in this checkpoint): `mappings/core_passive_fingers_54_v1/`, `mappings/biomech_57_v1/`, approved template mapping artifacts, cross-session template verification, mapping-version approval workflow, `build_template_mapping.py`, `verify_session_mapping.py`, automatic cross-session mismatch blocking. Phase B remains the approved-template system; Phase A+ only does optional, unverified session-level enrichment.

## 1. Current state (what already exists)

The foundation (older `dcfeb921` V1 plan, Phases 0-6) is implemented and tested:

- [src/layer2_motive/segmentation/schemas.py](src/layer2_motive/segmentation/schemas.py): enums (`RECOMMENDATION_CLASSES`, `FEATURE_SCOPES`, `MAPPING_CONFIDENCE`, `SEVERITY_CLASSES`), column lists, bundles, `RecommendationThresholds`.
- [src/layer2_motive/segmentation/load_inputs.py](src/layer2_motive/segmentation/load_inputs.py): read-only Layer 1 / Layer 2 loaders.
- [src/layer2_motive/segmentation/validate_inputs.py](src/layer2_motive/segmentation/validate_inputs.py): full validation suite (identity, alignment, join, integrity, fingerprints).
- [src/layer2_motive/segmentation/qc_events.py](src/layer2_motive/segmentation/qc_events.py): Layer 1 event normalization (`marker_raw_name`, `body_region_group`; no family mapping; no name normalization).
- [src/layer2_motive/segmentation/window_summary.py](src/layer2_motive/segmentation/window_summary.py): window subset, L1/L2 summaries, per-link summary (`percent_analysis_eligible`), `build_combined_qc_event_table`, output writer.
- CLIs: [scripts/validate_segmentation_inputs.py](scripts/validate_segmentation_inputs.py), [scripts/review_segmentation_window.py](scripts/review_segmentation_window.py).
- 31 tests under [tests/](tests/); sample outputs under `outputs/window_review/`.

## 2. What of the revised plan is already satisfied

- User-selected frame window: yes (`--start-frame/--end-frame`, clamped to overlap).
- Tables-before-export ordering: partially (window review tables exist, no export yet — export is Phase D, correctly out of scope).
- Layer 2 link-level usability via Stage 08 eligibility: yes (`_summarize_layer2_per_link`).
- Audit vs display separation: partially (`combined_qc_events.csv` is effectively audit; current display tables use old names/schemas).
- Layer 2 authority preserved; no marker->link invalidation: yes (combined table keeps `mapping_confidence in {n/a, body_region_only}`, never asserts link invalidity).

## 3. What is missing for Phase A+ (the gap)

- Gap policy strict/relaxed (gap_0p2 counted only in strict, always visible).
- QC evidence policy (which L1/L2 evidence types enter compact tables / counting; `included_in_user_review`).
- Link/joint export scope field with core-only default + `included_by_export_scope`.
- Marker-family mapping module (`marker_family.py` does not exist), with optional DataDescriptions enrichment + heuristic fallback.
- Revised compact decision tables: `qc_event_display.csv`, `layer2_link_scope_display.csv`, `window_qc_summary_display.csv`, `layer1_marker_family_risk.csv`, `combined_qc_event_summary.csv`.
- Unmapped-marker visibility (count + rows).
- Mapping provenance fields (`mapping_source`, `mapping_confidence`, `template_mapping_status`, `mapping_version`) populated from DataDescriptions when present, else heuristic.
- Coarse `recommendation_placeholder` re-expressing existing manifest fields.

## 4. DataDescriptions decision (Phase A+)

DataDescriptions is now an **optional active input**. The CLI `--datadescriptions PATH` arg is used when supplied and silently ignored when absent (no failure, no requirement). It only ever supplies **marker-derived regional-risk evidence** (marker -> attached bone -> joint family). It must never rewrite Layer 2 parent-child links, relative-quaternion computation, Stage 07/08 logic, analysis eligibility, or `feature_scope`, and must never invalidate a link.

Scope of parsing implemented now: read the session `_DataDescriptions.csv`, extract `Bone Marker` rows -> `marker name -> attached bone/segment`, optionally capture basic skeleton/template label if trivially available, normalize marker names, and prefer this map over the heuristic. No approved-template artifacts, no cross-session verification (Phase B).

## 5. Files to create / modify

Create:
- [src/layer2_motive/segmentation/marker_family.py](src/layer2_motive/segmentation/marker_family.py): name normalization, side inference, OPTIONAL session DataDescriptions marker->bone parsing, marker->attached_bone->joint_family overlay (DataDescriptions-first, heuristic fallback), unmapped handling.
- [tests/test_marker_family.py](tests/test_marker_family.py)
- [tests/test_display_tables.py](tests/test_display_tables.py)

Modify:
- [src/layer2_motive/segmentation/schemas.py](src/layer2_motive/segmentation/schemas.py): add joint-family list, Phase A+ `mapping_source` / `mapping_confidence` / `template_mapping_status` value sets, `GAP_POLICIES`, `EXPORT_SCOPES` (incl. `all_links_audit`), evidence-type sets, dataclasses `GapPolicy`/`QCEvidencePolicy`/`ExportScopePolicy`, and the five new display-table column tuples.
- [src/layer2_motive/segmentation/window_summary.py](src/layer2_motive/segmentation/window_summary.py): gap-policy-aware counting; marker-family overlay on L1 rows; builders `build_window_qc_summary_display`, `build_qc_event_display`, `build_layer2_link_scope_display`, `build_layer1_marker_family_risk`, `build_combined_qc_event_summary`; migrate `write_window_review_outputs` to the revised file names; keep `combined_qc_events.csv` as audit.
- [src/layer2_motive/segmentation/qc_events.py](src/layer2_motive/segmentation/qc_events.py): add `normalized_marker_name`, `attached_bone`, `attached_bone_canonical`, and family-overlay columns to the Layer 1 event table (delegating to a `MarkerFamilyMapper` instance).
- [scripts/review_segmentation_window.py](scripts/review_segmentation_window.py): new CLI args (incl. optional active `--datadescriptions`); build the mapper from the file when present; thread policies through; record choices + mapping provenance in JSON/report.
- Tests: update [tests/test_window_summary.py](tests/test_window_summary.py) and [tests/test_qc_events.py](tests/test_qc_events.py) for the new columns/file names.

Decision on module placement: keep Phase A+ DataDescriptions logic inside `marker_family.py` (one small `load_session_datadescriptions_marker_map` helper + the mapper). Do NOT create `template_mapping.py` now; that name is reserved for the Phase B approved-template library.

Out of scope (later phases, do not build now): `recommendations.py` (Phase C), `export_segment.py` + parquet contract (Phase D), `widgets.py` + notebook (Phase E), Phase B approved-template library (`template_mapping.py`, `mappings/`, `build_template_mapping.py`, `verify_session_mapping.py`, cross-session verification).

## 6. CLI arguments to add (to `review_segmentation_window.py`)

- `--gap-policy {strict,relaxed}` (default `strict`).
- `--export-scope {core_candidate,core_plus_review,all_non_excluded,all_links_audit}` (default `core_candidate`).
- `--l1-evidence` comma list (default `gap_0p5,artifact_sigma,segment_swap,gap_0p2`; `gap_0p2` counting still gated by gap policy).
- `--l2-evidence` comma list (default `stage07_jump,stage08_masked,stage08_eligibility,block_filter,manual_review`).
- `--mapping-version` (default `heuristic_v0`; auto-set to `session_datadescriptions_unverified_v0` when a DataDescriptions file is supplied).
- `--datadescriptions PATH` (OPTIONAL ACTIVE): if provided, parse and use it for marker->bone enrichment; if absent, fall back to heuristic. Never fails when absent; warns (not errors) if provided but unparseable, then falls back.

## 7. Output files to generate (migrated revised names, under `outputs/window_review/<session>_<start>_<end>/`)

Compact display (State 2):
- `window_qc_summary_display.csv`
- `qc_event_display.csv` (QC Event Review Table)
- `layer2_link_scope_display.csv` (Link / Joint Decision Table)
- `layer1_marker_family_risk.csv`
- `combined_qc_event_summary.csv`

Full audit (State 1, unchanged behavior):
- `combined_qc_events.csv`

Supporting:
- `window_review_report.md` (updated: gap policy, evidence policy, export scope, mapping source, unmapped count, marker-family examples).
- `window_validation_summary.json` (add `gap_policy`, `qc_evidence_policy`, `export_scope`, `mapping_version`, `mapping_source`, `datadescriptions_used` bool, `n_unmapped_markers`).

The old `layer1_window_summary.csv` / `layer2_window_summary.csv` / `layer2_link_window_summary.csv` names are replaced by the revised tables.

## 8. Table schemas

`window_qc_summary_display.csv` (revised 10.1 + `export_scope`): `session_key, frame_start, frame_end, duration_frames, duration_seconds, gap_policy, export_scope, total_frames, gap_0p5_percent, gap_0p2_percent, gap_0p2_counted_in_burden, artifact_sigma_percent, segment_swap_percent, overall_raw_qc_status, layer2_core_usable_percent, layer2_review_usable_percent, layer2_excluded_usable_percent, n_layer1_display_events, n_layer2_display_events, n_unmapped_markers, n_unmapped_events, mapping_version, mapping_source, template_mapping_status`.

`qc_event_display.csv` (revised 2A.2/10.2): `frame_start, frame_end, duration_frames, duration_seconds, qc_type, reason, marker_or_region, normalized_marker_name, attached_bone, attached_bone_canonical, related_joint_family, adjacent_joint_family, mapping_source, mapping_confidence, template_mapping_status, source_layer, included_in_user_review, recommendation_impact`.

`layer2_link_scope_display.csv` (revised 2A.3/10.3): `link_id, link_or_joint, parent_canonical, child_canonical, family, feature_scope, view_scope, n_gap_0p5_related_frames, gap_0p5_related_percent, n_gap_0p2_related_frames, gap_0p2_related_percent, gap_0p2_counted_in_burden, artifact_sigma_related_percent, segment_swap_related_percent, layer2_usable_percent, layer2_masked_percent, mapping_version, template_mapping_status, recommendation_placeholder, export_scope, included_by_export_scope, selection_default, user_override, user_note`.

`layer1_marker_family_risk.csv` (revised 10.4): `session_id, run_label, marker_or_entity, normalized_marker_name, body_region_group, side, attached_bone, attached_bone_canonical, joint_family, adjacent_joint_family, mapping_source, mapping_confidence, mapping_version, template_mapping_status, n_events, n_frames_affected, gap_0p5_frames, gap_0p2_frames, artifact_sigma_frames, segment_swap_frames, severity_summary, recommendation_impact, notes`.

`combined_qc_event_summary.csv` (revised 10.5): grouped counts over `source_layer, qc_type, severity, reason, joint_family, mapping_source, mapping_confidence, template_mapping_status, feature_scope`.

`combined_qc_events.csv` (audit): existing `COMBINED_QC_EVENT_COLUMNS`, extended with `normalized_marker_name, attached_bone, attached_bone_canonical, related_joint_family, mapping_source, mapping_confidence, mapping_version, template_mapping_status` (audit-complete; retains ALL links regardless of export scope).

### Phase A+ placeholder + scope semantics

- `recommendation_placeholder` (re-expresses existing Layer 2 manifest only, no new science; NOT a final recommendation): `excluded_distal`/`excluded_toe` -> `excluded_by_policy`; `stage08_policy==block_filter` -> `blocked_needs_review`; `requires_manual_review` or `feature_scope==review_provisional` -> `manual_review`; else `candidate_include`.
- `included_by_export_scope`: derived from `--export-scope` vs `feature_scope` (`core_candidate`-> core links only; `core_plus_review`-> + `review_provisional`; `all_non_excluded`-> all except excluded_*; `all_links_audit`-> all links including excluded distal/toe).
- The main link table follows export scope by DEFAULT: `layer2_link_scope_display.csv` is filtered to `included_by_export_scope == true` and `view_scope` is set to the chosen `export_scope`. Excluded links are not dropped from the system — they remain in `combined_qc_events.csv` audit and are shown in the link table only when `--export-scope all_links_audit` is selected.
- `selection_default`: set equal to `included_by_export_scope` (no independent selection logic in Phase A+). It exists only to mirror the export-scope decision until the Phase C recommendation engine adds real selection.
- Mapping values WITHOUT DataDescriptions: `mapping_source in {marker_name_heuristic, body_region_group, unmapped}`; `mapping_confidence in {medium, low, template_uncertain, unmapped}` (never `high`); `template_mapping_status = missing_datadescriptions_fallback_to_heuristic`; `attached_bone`/`attached_bone_canonical` empty/null.
- Mapping values WITH DataDescriptions: `attached_bone`/`attached_bone_canonical` populated; `mapping_source = session_datadescriptions_optional`; `mapping_confidence = attached_bone_observed_but_template_unverified`; `template_mapping_status = session_datadescriptions_used_unverified`. Markers absent from the file fall back to heuristic values for those rows.
- Forbidden in Phase A+ (Phase B only): `approved_template_datadescriptions`, `attached_bone_observed_and_template_verified`, `verified_against_template`.

## 9. Marker-family module (`marker_family.py`) — DataDescriptions-first, heuristic fallback

Proposed API:

```text
normalize_marker_name(name) -> bare token (strip "671:", "671_", "T3_671_", side preserved)
load_session_datadescriptions_marker_map(path) -> dict[normalized_marker, attached_bone] | None
MarkerFamilyMapper(optional_marker_to_bone_map=None)
  .map_marker_to_family(raw_marker_name) -> MarkerFamilyResult
```

`MarkerFamilyResult` fields: `normalized_marker_name, side, attached_bone, attached_bone_canonical, joint_family, adjacent_joint_family, mapping_source, mapping_confidence, template_mapping_status`.

Resolution order inside `map_marker_to_family`:
1. If a DataDescriptions marker->bone map was loaded AND contains the normalized marker: use its `attached_bone`; derive `attached_bone_canonical` (strip asset prefix) and `joint_family` from a bone->family table; set provenance to the `session_datadescriptions_optional` / `attached_bone_observed_but_template_unverified` / `session_datadescriptions_used_unverified` triple.
2. Else heuristic marker-name table (grounded in the reviewed DataDescriptions): `LWristOut/LFArm -> LFArm -> left_elbow_forearm` (adjacent `left_wrist_hand`); `LHandIn/LHandOut -> LHand -> left_wrist_hand`; chest/back -> `trunk_chest`; waist -> `pelvis_hip` (`mapping_confidence=template_uncertain`, exact link mapping never asserted); fingers -> `fingers_excluded`; toes (`*ToeTip`) -> `toes_excluded`.
3. Else `body_region_group` (when only a region is known).
4. Else unmapped: `joint_family=unknown, mapping_source=unmapped, mapping_confidence=unmapped`.

Invariants:
- Returns `related_joint_family`/`adjacent_joint_family` only — never a Layer 2 `link_id`.
- Never writes/overwrites `parent_canonical`/`child_canonical` or any Layer 2 field.
- Waist/trunk markers stay `template_uncertain` for exact link mapping even when DataDescriptions is present (WaistCBack maps to different bones across Core vs Biomech templates).

## 10. Tests to add / update

`tests/test_marker_family.py`:
- Name normalization across the three forms (`671:LHandIn`, `671_LHandIn`, `LHandIn`).
- Side inference; `LWristOut` family + adjacency; waist `template_uncertain`; finger/toe excluded families; unknown -> unmapped.
- DataDescriptions ABSENT -> heuristic provenance triple; pipeline mapper still returns valid results.
- DataDescriptions PROVIDED -> marker->attached_bone map is used; `LHandIn -> LHand`; `LWristOut -> LFArm`; provenance = session_datadescriptions triple.
- `WaistCBack` may differ by template but remains `template_uncertain` for exact link mapping.
- Marker missing from the DataDescriptions map -> that row falls back to heuristic.
- Assert no function returns a Layer 2 `link_id`, and DataDescriptions mapping does not produce/alter `parent_canonical`/`child_canonical`.

`tests/test_display_tables.py`:
- Strict vs relaxed (gap_0p2 counted in strict, not relaxed; visible in both).
- Each display table has exactly its required columns (incl. `export_scope` in window summary).
- `included_in_user_review` distinguishes audit vs counted.
- `included_by_export_scope` honors core-only default and broader scopes; main link table filtered to scope by default; `all_links_audit` shows excluded links; `selection_default == included_by_export_scope`.
- Unmapped rows present + counted in window summary.
- Display tables have fewer rows than `combined_qc_events.csv`.
- Full pipeline runs with NO DataDescriptions (no failure) and WITH DataDescriptions (provenance fields flip); combined event carries no exact link id for Layer 1 rows.
- CLI writes all five revised display files + audit in both modes.

Update `tests/test_window_summary.py` / `tests/test_qc_events.py` for renamed outputs and new event columns. Keep all previous Phase A tests passing.

## 11. Smoke commands (real fixture `671_T1_P1_R1`)

```bash
# 1. No DataDescriptions, strict, core-only
python scripts/review_segmentation_window.py \
  --layer1-dir input/Layer1_QC/QC_671_T1_P1_R1 \
  --layer2-dir input/Layer2_Kinematics/671_T1_P1_R1 \
  --start-frame 16000 --end-frame 17000 \
  --gap-policy strict --export-scope core_candidate \
  --out outputs/window_review/671_T1_P1_R1_16000_17000_strict

# 2. No DataDescriptions, relaxed, broader scope
python scripts/review_segmentation_window.py \
  --layer1-dir input/Layer1_QC/QC_671_T1_P1_R1 \
  --layer2-dir input/Layer2_Kinematics/671_T1_P1_R1 \
  --start-frame 16000 --end-frame 17000 \
  --gap-policy relaxed --export-scope core_plus_review \
  --out outputs/window_review/671_T1_P1_R1_16000_17000_relaxed

# 3. WITH DataDescriptions (optional active), strict, core-only
python scripts/review_segmentation_window.py \
  --layer1-dir input/Layer1_QC/QC_671_T1_P1_R1 \
  --layer2-dir input/Layer2_Kinematics/671_T1_P1_R1 \
  --datadescriptions "data_description/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001_DataDescriptions.csv" \
  --start-frame 16000 --end-frame 17000 \
  --gap-policy strict --export-scope core_candidate \
  --out outputs/window_review/671_T1_P1_R1_16000_17000_strict_with_datadescriptions

pytest -q
ruff check src tests scripts
```

Then compare: strict vs relaxed `window_qc_summary_display.csv` (gap_0p2 counted flag flips); run 1 vs run 3 (`attached_bone` populated, `mapping_source`/`template_mapping_status` flip to the session-DataDescriptions triple) while Layer 2 columns are identical. Report unmapped count + marker-family examples.

## 12. Risks / ambiguities / possible over-scope

- Per-row marker-family mapping over the full qc_mask (30604 frames) via `DataFrame.apply` could be slow; mitigate by mapping per unique marker/region once then joining.
- `qc_mask.csv` frame rows often lack a marker name; those L1 events map to `region/unknown` and appear as unmapped — expected and must stay visible, not dropped.
- DataDescriptions row format is positional CSV (`Bone Marker, <marker>, <attached_bone>, <asset>, x, y, z`); parse defensively, warn-and-fallback on unexpected shape rather than failing the run.
- Revised doc tension on `recommendation` vs `recommendation_placeholder`: resolved to placeholder (real engine deferred to Phase C). `selection_default` mirrors `included_by_export_scope` only.
- Over-scope guard: do NOT build the Phase B approved-template library, cross-session verification, recommendations engine, export, widgets, or notebook now.
- Waist/trunk mappings stay `template_uncertain` even with DataDescriptions; do not assert exact pelvis/spine bone or exact link.

## 13. Recommended staged implementation order

1. `schemas.py` additions (joint families, Phase A+ mapping value sets, gap/export-scope enums incl. `all_links_audit`, policy dataclasses, five display-column tuples).
2. `marker_family.py` + `tests/test_marker_family.py`: heuristic first, then optional DataDescriptions parsing + DataDescriptions-first resolution. Get mapping + fallback correct before wiring.
3. Wire `normalized_marker_name`/`attached_bone(+canonical)`/family columns into `qc_events.py` event table; update `tests/test_qc_events.py`.
4. `window_summary.py`: gap-policy counting + the five display-table builders (link table follows export scope by default) + migrated writer.
5. `review_segmentation_window.py`: new args incl. optional active `--datadescriptions`, build mapper, thread policies, record provenance in JSON/report.
6. `tests/test_display_tables.py` (with/without DataDescriptions) + update `tests/test_window_summary.py`.
7. Run smoke commands (runs 1-3) + pytest/ruff; produce the Phase A+ stop-and-report.

## 14. Phase A+ stop-and-report (to deliver after implementation)

Report explicitly: what changed Phase A -> Phase A+; what remains deferred to Phase B; files/modules changed; how DataDescriptions is optional (used if present, ignored if absent, never fails); how heuristic fallback works (resolution order + per-marker fallback); how Layer 2 parent-child logic is protected (mapper never returns/edits `link_id`/`parent_canonical`/`child_canonical` or Layer 2 fields; DataDescriptions is regional-risk evidence only); strict vs relaxed gap_0p2 behavior; with vs without DataDescriptions provenance comparison; unmapped count; export-scope field presence + default-follows-scope behavior; and the tests that prove each of these.
