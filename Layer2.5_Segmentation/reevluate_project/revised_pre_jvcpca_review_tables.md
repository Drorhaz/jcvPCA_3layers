# Revised Pre-JcvPCA Segment / Joint Review Tables

## Core correction

The backend should stay simple:

1. Read Layer 1 QC evidence.
2. Read Layer 2 link/window usability evidence.
3. Read optional DataDescriptions for marker-to-bone mapping.
4. Build a clear mapping topology table.
5. Let the user select joints/links for analysis.
6. Generate compact review tables only for the selected frame window and selected joints.

No recommendation engine. No arbitrary thresholds. No unlabeled markers in the main computation. Layer 1 remains regional marker evidence. Layer 2 remains solved-link problem evidence.

---

# Required inputs

## Layer 1 QC folder

| File name | Required? | Used for |
|---|---:|---|
| `layer1_segmentation_notebook_manifest.json` | Yes | Session identity, frame rate, frame count, frame/time conventions |
| `qc_mask.csv` | Yes | Frame-level QC flags; used for flagged-frame percentages if needed |
| `qc_mask_intervals.csv` | Preferred | Interval-level QC evidence when specific event files are unavailable |
| `gaps_over_0p2s.csv` | Preferred if available | Labeled-marker gap evidence, >=0.2 s |
| `gaps_over_0p5s.csv` | Preferred if available | Labeled-marker gap evidence, >=0.5 s |
| `artifact_events.csv` | Preferred if available | Labeled-marker artifact and segment-length/swap evidence |

## Layer 2 export folder

| File name | Required? | Used for |
|---|---:|---|
| `layer2_session_filtered_rotvecs.parquet` | Yes | Per-frame, per-link Layer 2 status/problem fields |
| `layer2_session_link_manifest.csv` | Yes | Link names, link IDs, parent/child bones, available joint/link list |
| `layer2_session_summary.json` | Yes | Session identity and run metadata |

## Optional mapping file

| File name | Required? | Used for |
|---|---:|---|
| `*_DataDescriptions.csv` | Recommended | Marker -> attached bone -> marker/joint family mapping |

---

# Required display flow

## Step 1: Mapping topology before joint selection

Before the user chooses joints/links, show the mapping topology table. This lets the user see which labeled markers map to which joint families and candidate Layer 2 links.

## Step 2: User selects joints/links

The widget should let the user choose actual Layer 2 links/joints from `layer2_session_link_manifest.csv`, for example:

```text
J005 LUArm->LFArm
J007 LFArm->LHand
J020 LThigh->LShin
```

This replaces vague `export_scope` language in the final display. If presets still exist, define them clearly as joint-selection presets only.

---

# Table 0 / Table 5 displayed first — `mapping_logic_table.csv`

## Purpose

Show the mapping topology before joint selection.

This table answers:

```text
Which labeled markers are available?
Which markers map to known bones/families?
Which candidate Layer 2 links may be related?
Which labeled markers are unmapped and need review?
```

## Rules

- Include labeled markers only.
- Exclude unlabeled markers completely from main computation and display.
- Do not include `input_type`, `is_labeled_marker`, or `is_unlabeled_marker` in the main table.
- Do not include `template_mapping_status` in the main table.
- If a labeled marker is unmapped, show its name, not only a count.
- Candidate links are candidate/regional only, not exact affected links.

## Columns

| Column | Meaning |
|---|---|
| `raw_marker_or_region` | Original marker or labeled region name from Layer 1 evidence |
| `normalized_marker_or_region` | Clean marker/region name without asset prefix |
| `component_markers` | For marker-pair/region rows, list the component labeled markers; blank for single marker |
| `attached_bone` | Bone from DataDescriptions or heuristic, if known |
| `attached_bone_canonical` | Canonical bone name used for candidate link lookup |
| `marker_family` | Marker/body family |
| `related_joint_family` | Joint family used for regional overlay |
| `candidate_layer2_links` | Candidate Layer 2 links from bone adjacency or regional mapping |
| `candidate_layer2_link_ids` | Candidate Layer 2 link IDs |
| `mapping_source` | `datadescriptions`, `heuristic`, `regional_pair`, or `unmapped` |
| `mapping_status` | `mapped` or `unmapped` |
| `candidate_mapping_level` | `bone_adjacency_candidate`, `regional_family_proxy`, `segment_pair_regional`, or `unmapped_unknown` |
| `included_in_review` | True for mapped labeled markers and retained unmapped labeled markers |
| `review_note` | Short explanation if unmapped or uncertain |

## Demo

| raw_marker_or_region | normalized_marker_or_region | component_markers | attached_bone | attached_bone_canonical | marker_family | related_joint_family | candidate_layer2_links | candidate_layer2_link_ids | mapping_source | mapping_status | candidate_mapping_level | included_in_review | review_note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 671:LWristOut | LWristOut |  | 671_LFArm | LFArm | left_elbow_forearm | left_elbow_forearm | J005 LUArm->LFArm; J007 LFArm->LHand | J005; J007 | datadescriptions | mapped | bone_adjacency_candidate | true |  |
| 671:LHandIn | LHandIn |  | 671_LHand | LHand | left_wrist_hand | left_wrist_hand | J007 LFArm->LHand | J007 | datadescriptions | mapped | bone_adjacency_candidate | true |  |
| ChestTop__WaistCBack | ChestTop__WaistCBack | ChestTop; WaistCBack | mixed | mixed | trunk_chest; pelvis_hip | trunk_chest; pelvis_hip | J002 671->Ab; J003 Ab->Chest | J002; J003 | datadescriptions | mapped | segment_pair_regional | true | regional pair, not exact link evidence |
| 671:UnknownMarker | UnknownMarker |  | unknown | unknown | unknown | unknown |  |  | unmapped | unmapped | unmapped_unknown | true | retained as unknown labeled marker |

---

# Table 1 — `window_decision_summary.csv`

## Purpose

One-row summary of what entered the review.

## Important corrections

- Replace vague `export_scope` with clear joint-selection fields.
- If `export_scope` remains in code, define it as a joint-selection preset.
- `layer1_total_labeled_markers` must state its source.
- `layer1_unmapped_labeled_markers` should be a list of names, not only a count.
- `unlabeled_marker_evidence_included` is not needed as a computation field because unlabeled evidence must be excluded. A note can state this once.
- Remove mean/min usable percent and below-threshold counts.
- Add Layer 2 problem summaries for selected links: jump-fail and block-filter frame percentages by link.

## Columns

| Column | Meaning |
|---|---|
| `session_id` | Session key |
| `run_label` | Layer 2 run label |
| `frame_start` | Selected frame start |
| `frame_end` | Selected frame end |
| `duration_frames` | `frame_end - frame_start + 1` |
| `duration_sec` | `duration_frames / fps` |
| `selected_qc_evidence_types` | Main QC evidence types included |
| `joint_selection_preset` | Optional preset, e.g. `core_candidate`; define clearly if used |
| `selected_layer2_links` | Actual selected link names from widget |
| `selected_layer2_link_ids` | Actual selected link IDs from widget |
| `layer1_labeled_marker_source` | Source used for labeled-marker inventory |
| `layer1_total_labeled_markers` | Number of labeled markers found from source |
| `layer1_mapped_labeled_markers` | Number of labeled markers mapped to joint families/candidate links |
| `layer1_unmapped_labeled_marker_names` | Names of unmapped labeled markers |
| `unlabeled_marker_policy` | Always `excluded_from_main_review` |
| `layer2_total_links_available` | Total links in `layer2_session_link_manifest.csv` |
| `layer2_selected_links_count` | Number of selected links shown in Table 3 |
| `datadescriptions_used` | True/false |
| `mapping_source_summary` | Short summary of mapping sources |
| `n_gap_0p5_events` | Count of normalized labeled-marker events |
| `n_gap_0p2_events` | Count of normalized labeled-marker events |
| `n_artifact_sigma_events` | Count of normalized labeled-marker events |
| `n_segment_swap_events` | Count of normalized labeled-marker events |
| `gap_0p5_flagged_frame_percent` | Frame-level percent from `qc_mask.csv`, if used |
| `gap_0p2_flagged_frame_percent` | Frame-level percent from `qc_mask.csv`, if used |
| `artifact_sigma_flagged_frame_percent` | Frame-level percent from `qc_mask.csv`, if used |
| `segment_swap_flagged_frame_percent` | Frame-level percent from `qc_mask.csv`, if used |
| `jump_fail_rad_links_frame_percent` | Per selected link: percent of window frames affected by `jump_fail_rad` |
| `block_filter_links_frame_percent` | Per selected link: percent of window frames affected by `block_filter` |

## Demo

| session_id | frame_start | frame_end | duration_frames | duration_sec | selected_qc_evidence_types | joint_selection_preset | selected_layer2_links | selected_layer2_link_ids | layer1_labeled_marker_source | layer1_total_labeled_markers | layer1_mapped_labeled_markers | layer1_unmapped_labeled_marker_names | unlabeled_marker_policy | layer2_total_links_available | layer2_selected_links_count | datadescriptions_used | mapping_source_summary | n_gap_0p5_events | n_gap_0p2_events | n_artifact_sigma_events | n_segment_swap_events | gap_0p5_flagged_frame_percent | gap_0p2_flagged_frame_percent | artifact_sigma_flagged_frame_percent | segment_swap_flagged_frame_percent | jump_fail_rad_links_frame_percent | block_filter_links_frame_percent |
|---|---:|---:|---:|---:|---|---|---|---|---|---:|---:|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 671_T1_P1_R1 | 16000 | 17000 | 1001 | 8.34 | gap_0p5; gap_0p2; artifact_sigma; segment_swap | core_candidate | LUArm->LFArm; LFArm->LHand; LThigh->LShin | J005; J007; J020 | DataDescriptions + Layer1 event files | 54 | 53 | UnknownMarker | excluded_from_main_review | 50 | 3 | true | 53 datadescriptions-mapped; 1 unmapped | 2 | 4 | 12 | 4 | 0.8 | 2.1 | 1.4 | 0.6 | J007 LFArm->LHand: 6.1% | J007 LFArm->LHand: 100.0% |

---

# Table 2 — `qc_evidence_summary_table.csv`

## Purpose

Compact summary of what labeled-marker QC evidence entered the review.

## Important corrections

- `gap_0p5` event durations should be at least 60 frames per 0.5 s event at 120 Hz. If the demo has `gap_0p5 event_count = 2`, total event duration should usually be >=120 frames.
- Remove `mapping_confidence_summary`; the only important mapping decision here is mapped vs unmapped.

## Columns

| Column | Meaning |
|---|---|
| `qc_type` | `gap_0p5`, `gap_0p2`, `artifact_sigma`, or `segment_swap` |
| `event_count` | Number of normalized labeled-marker events |
| `total_event_duration_frames` | Sum of event durations; not unique affected frames |
| `total_event_duration_percent_of_window` | Event duration burden divided by window frames |
| `unique_marker_or_region_count` | Number of distinct markers/regions involved |
| `markers_or_regions` | Names of markers/regions involved |
| `related_joint_families` | Joint families touched by these events |
| `mapping_status_summary` | Example: `mapped:4; unmapped:0` |
| `source_files` | Source files contributing events |

## Demo

| qc_type | event_count | total_event_duration_frames | total_event_duration_percent_of_window | unique_marker_or_region_count | markers_or_regions | related_joint_families | mapping_status_summary | source_files |
|---|---:|---:|---:|---:|---|---|---|---|
| gap_0p5 | 2 | 145 | 14.5 | 2 | 671:LElbowOut; 671:LShoulderTop | left_elbow_forearm; left_shoulder_arm | mapped:2; unmapped:0 | gaps_over_0p5s.csv |
| gap_0p2 | 4 | 89 | 8.9 | 3 | 671:RFArm; 671:LWristOut; 671:HeadFront | right_elbow_forearm; left_elbow_forearm; head_neck | mapped:4; unmapped:0 | gaps_over_0p2s.csv |
| artifact_sigma | 12 | 156 | 15.6 | 4 | 671:LHandIn; 671:ChestTop; 671:LWristOut; 671:RHandOut | left_wrist_hand; trunk_chest; left_elbow_forearm; right_wrist_hand | mapped:11; unmapped:1 | artifact_events.csv |
| segment_swap | 4 | 62 | 6.2 | 1 | ChestTop__WaistCBack | trunk_chest; pelvis_hip | mapped:4; unmapped:0 | artifact_events.csv |

---

# Table 3 — `link_joint_review_table.csv`

## Purpose

Per selected Layer 2 link/joint table for review before JcvPCA.

## Important corrections

Remove these columns from the main table:

```text
parent_canonical
child_canonical
feature_scope
included_by_export_scope
window_total_frames
layer2_usable_frames
layer2_usable_percent
layer2_ineligible_frames
layer2_jump_context_frames
qc_event_count_related_to_link
layer2_qc_status
scope_review_status
```

Add explicit Layer 2 problem percentages:

```text
layer2_ineligible_jump_fail_rad_frame_percent
layer2_ineligible_block_filter_frame_percent
```

Show mapped related markers as a list of names, not a count.

## Columns

| Column | Meaning |
|---|---|
| `link_id` | Layer 2 link ID |
| `link_or_joint` | Display name, e.g. `LFArm->LHand` |
| `joint_family` | Joint family |
| `l1_regional_gap_0p5_event_frames` | Regional event-duration burden from mapped markers |
| `l1_regional_gap_0p5_event_percent` | Same divided by window frame count |
| `l1_regional_gap_0p2_event_frames` | Regional event-duration burden |
| `l1_regional_gap_0p2_event_percent` | Same divided by window frame count |
| `l1_regional_artifact_sigma_event_frames` | Regional artifact burden |
| `l1_regional_artifact_sigma_event_percent` | Same divided by window frame count |
| `l1_regional_segment_swap_event_frames` | Regional segment/swap burden |
| `l1_regional_segment_swap_event_percent` | Same divided by window frame count |
| `layer2_ineligible_jump_fail_rad_frame_percent` | Percent of this link's window frames affected by jump-fail/radian flag |
| `layer2_ineligible_block_filter_frame_percent` | Percent of this link's window frames affected by block-filter policy |
| `mapped_qc_marker_names_related_to_link` | List of related mapped QC markers/regions |
| `layer2_problem_notes` | Descriptive notes only |

## Demo

| link_id | link_or_joint | joint_family | l1_regional_gap_0p5_event_frames | l1_regional_gap_0p5_event_percent | l1_regional_gap_0p2_event_frames | l1_regional_gap_0p2_event_percent | l1_regional_artifact_sigma_event_frames | l1_regional_artifact_sigma_event_percent | l1_regional_segment_swap_event_frames | l1_regional_segment_swap_event_percent | layer2_ineligible_jump_fail_rad_frame_percent | layer2_ineligible_block_filter_frame_percent | mapped_qc_marker_names_related_to_link | layer2_problem_notes |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| J005 | LUArm->LFArm | left_elbow_forearm | 0 | 0.0 | 71 | 7.1 | 2 | 0.2 | 0 | 0.0 | 0.0 | 0.3 | 671:LWristOut; 671:LElbowOut | 3 block-filter frames |
| J007 | LFArm->LHand | left_wrist_hand | 18 | 1.8 | 12 | 1.2 | 8 | 0.8 | 0 | 0.0 | 6.1 | 100.0 | 671:LWristOut; 671:LHandIn; 671:LHandOut | full-window block_filter; 61 jump_fail_rad frames |
| J020 | LThigh->LShin | left_thigh_knee | 0 | 0.0 | 0 | 0.0 | 0 | 0.0 | 0 | 0.0 | 0.0 | 0.0 |  | no Layer 2 problem flags in selected window |

---

# Table 4 — `qc_event_review_table.csv`

## Purpose

Detailed event-level Layer 1 evidence inside the selected window.

## Important corrections

Remove:

```text
start_sec
end_sec
```

## Columns

| Column | Meaning |
|---|---|
| `frame_start` | Event start frame |
| `frame_end` | Event end frame |
| `duration_frames` | Event duration in frames |
| `qc_type` | QC type |
| `reason` | Original or normalized reason |
| `source_file` | Source Layer 1 file |
| `raw_marker_or_region` | Marker/region involved |
| `related_joint_family` | Mapped joint family |
| `candidate_layer2_links` | Candidate links only |
| `candidate_mapping_level` | Candidate mapping type |
| `mapping_status` | `mapped` or `unmapped` |
| `included_in_review` | True/false |

## Demo

| frame_start | frame_end | duration_frames | qc_type | reason | source_file | raw_marker_or_region | related_joint_family | candidate_layer2_links | candidate_mapping_level | mapping_status | included_in_review |
|---:|---:|---:|---|---|---|---|---|---|---|---|---|
| 16110 | 16180 | 71 | gap_0p2 | marker_gap | gaps_over_0p2s.csv | 671:LWristOut | left_elbow_forearm | J005 LUArm->LFArm; J007 LFArm->LHand | bone_adjacency_candidate | mapped | true |
| 16020 | 16038 | 19 | artifact_sigma | velocity_mad | artifact_events.csv | 671:LHandIn | left_wrist_hand | J007 LFArm->LHand | bone_adjacency_candidate | mapped | true |
| 16200 | 16235 | 36 | segment_swap | segment_length_violation | artifact_events.csv | ChestTop__WaistCBack | trunk_chest; pelvis_hip | J002 671->Ab; J003 Ab->Chest | segment_pair_regional | mapped | true |

---

# Final table order for display

1. `mapping_logic_table.csv` — show before joint selection.
2. User selects joints/links.
3. `window_decision_summary.csv`.
4. `qc_evidence_summary_table.csv`.
5. `link_joint_review_table.csv`.
6. `qc_event_review_table.csv`.

The core outputs may still be five CSV files, but the mapping table should be displayed first because it explains the topology used for joint selection. 
