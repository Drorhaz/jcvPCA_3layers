# Post-Layer 2 Segmentation Notebook — Per-Session QC Review and Segment Export Plan

## 1. Purpose of this document

This document defines a new post-Layer 2 workflow: an interactive Jupyter notebook for selecting scientifically defensible analysis windows and joint/link sets from a single motion-capture session.

The notebook is not part of Layer 1 or Layer 2 computation. It is a separate bridge between the quality-controlled kinematic outputs and later Layer 3 analysis.

Its purpose is to combine, for one session at a time:

1. Layer 1 raw marker QC outputs, which are marker-level and frame-level.
2. Layer 2 filtered kinematic outputs, which are relative-link/joint-level and frame-level.
3. Human review of a candidate frame range.
4. Human selection of the joint/link set to export.
5. A reproducible segment parquet and review log for later Layer 3 analysis.

The notebook should help the user answer:

- Is this frame range clean enough to analyze?
- Which raw marker QC problems occur in this window?
- Which Layer 2 kinematic QC flags occur in this window?
- Which joints/links are usable, review-only, excluded, or problematic?
- Which selected links and frames should be exported for Layer 3?

The notebook should not run PCA, JcvPCA, JRW, statistics, or final analysis. It produces candidate segmented outputs only.

---

## 2. Why this is a new post-Layer 2 project

Layer 1 and Layer 2 produce different kinds of evidence.

Layer 1 is about raw optical marker quality:

```text
marker × frame
```

Layer 2 is about solved relative skeleton kinematics:

```text
relative link/joint × frame
```

These are not naturally the same table. A raw marker artifact cannot automatically be treated as a joint artifact without a mapping layer.

Therefore, the segmentation notebook is not just a simple viewer. It needs a small scientific software architecture that can:

1. Load one session’s Layer 1 QC mask.
2. Load one session’s Layer 2 filtered parquet.
3. Normalize their schemas.
4. Optionally map marker-level events to segment/link-level risk evidence.
5. Let the user choose a frame range.
6. Summarize all QC evidence for that selected window.
7. Recommend joints/links for inclusion, caution, review, or exclusion.
8. Let the user choose the final link set.
9. Export a segment parquet and decision log.

This is a new post-Layer 2 module, not a continuation of Stage 08.

---

## 3. Expected per-session inputs

The notebook operates on one session/run at a time. It should not require a combined-across-session parquet.

### 3.1 Layer 2 per-session export folder

Expected folder:

```text
outputs/layer2_exports/<run_label>/
```

Expected files:

```text
layer2_session_filtered_rotvecs.parquet
layer2_session_link_manifest.csv
layer2_session_summary.json
layer2_session_report.md
layer2_session_assumptions_and_limitations.md
layer2_session_integrity_audit.csv
README.md
```

The most important file is:

```text
layer2_session_filtered_rotvecs.parquet
```

This should contain the Stage 08 filtered output for one session, with both native filtered values and analysis-clean masked values.

Expected key columns:

```text
session_id
run_label
frame
time_sec
link_id
parent_canonical
child_canonical
feature_scope
included_in_v0
requires_manual_review
rx_raw
ry_raw
rz_raw
rotvec_norm_raw
rx_filtered_native
ry_filtered_native
rz_filtered_native
rotvec_norm_filtered_native
rx_filtered_analysis
ry_filtered_analysis
rz_filtered_analysis
rotvec_norm_filtered_analysis
stage07_jump_status
stage07_jump_magnitude_rad
stage07_row_qc_status
stage07_link_qc_status
stage08_policy
stage08_filter_status
stage08_within_jump_context_window
stage08_analysis_eligible
stage08_mask_reason
stage08_output_scope
```

The Layer 2 parquet is the source of kinematic link-level and frame-level QC information.

### 3.2 Layer 1 per-session QC outputs

The exact Layer 1 files may vary, but the notebook should expect a per-session QC mask or event table derived from raw marker QC.

Possible Layer 1 artifacts may include:

```text
raw_marker_qc_report.csv
frame_qc_mask.csv
marker_gap_report.csv
marker_artifact_report.csv
unlabeled_marker_burden.csv
selected_window_artifact_score.csv
```

Layer 1 may report events in terms of:

```text
marker
frame
frame range
time
artifact type
gap length
severity
reason
```

The notebook should normalize Layer 1 output to an internal event schema.

Recommended normalized Layer 1 QC schema:

```text
session_id
run_label
source_file
source_layer
qc_type
severity
frame
start_frame
end_frame
time_sec
start_time_sec
end_time_sec
duration_frames
duration_seconds
marker_raw_name
marker_canonical
marker_group
reason
notes
```

Example QC types:

```text
marker_gap
marker_jump
velocity_spike
unlabeled_burst
tracking_artifact
raw_qc_warning
raw_qc_fail
```

---

## 4. Main conceptual constraint: marker-level QC versus link-level kinematics

Layer 1 QC does not directly describe joints or relative quaternions. It describes marker quality.

Layer 2 QC describes relative parent-child skeleton links, such as:

```text
MotiveHip/top segment → LThigh
LThigh → LShin
LUArm → LFArm
LFArm → LHand
Chest → Neck
```

Therefore, the notebook needs to support two modes of QC integration.

### 4.1 Frame-only integration

This is the minimal and safest V1 integration.

Layer 1 events are summarized by frame/window only:

```text
Frame 12000 has raw marker artifact.
Frame 12000 is inside selected segment.
```

This does not claim which joint is affected.

Pros:

- Simple.
- Conservative.
- Does not require marker-to-joint mapping.
- Useful for identifying bad windows.

Cons:

- Does not tell the user which Layer 2 links may be affected by marker issues.

### 4.2 Marker-to-segment-to-link integration

This is the stronger V2/V1.5 integration.

Mapping path:

```text
marker → skeleton segment/bone → parent-child relative link
```

This allows the notebook to say:

```text
Layer 1 marker issue on LHand marker may affect LFArm→LHand link.
```

Important: this is risk evidence, not proof that the link is invalid.

Recommended wording:

```text
marker-level QC risk mapped to this segment/link
```

Avoid wording like:

```text
this joint is invalid because this marker had an artifact
```

---

## 5. Marker-to-link mapping strategy

The notebook should support a marker-to-link mapping table, but it should not rely on it blindly.

Recommended mapping artifact:

```text
marker_to_segment_map.csv
marker_to_link_map.csv
```

These can be generated per session or loaded if already created.

### 5.1 Preferred mapping source: Motive CSV header

If the raw Motive CSV header contains marker rows with parent/bone/segment information, use that as the primary mapping source.

Preferred logic:

```text
marker name + marker parent in CSV header → mapped skeleton segment
```

Mapping metadata:

```text
mapping_source = csv_header_parent
mapping_confidence = high
```

### 5.2 Fallback mapping source: marker name patterns

If the CSV header does not provide parent/segment information, use conservative name-pattern inference.

Examples:

```text
marker contains LHand → LHand
marker contains LFArm → LFArm
marker contains LUArm → LUArm
marker contains LThigh → LThigh
marker contains LShin → LShin
marker contains LFoot → LFoot
marker contains Chest → Chest
marker contains Head → Head
```

Mapping metadata:

```text
mapping_source = name_pattern
mapping_confidence = medium or low
```

Unknown markers must be reported as unmapped, not silently dropped.

### 5.3 Template-aware trunk/hip caution

The study uses two skeleton templates:

```text
T1/T2 = Core + Passive Fingers (54)
T3    = Biomech (57)
```

The trunk/spine topology differs between templates.

Therefore, marker-to-link mapping around hip, trunk, spine, abdomen, chest, and neck should be flagged cautiously.

Recommended confidence labels:

```text
high
medium
low
template_uncertain
manual_review
unmapped
```

### 5.4 Marker-to-link propagation

If a marker maps to segment `S`, it can affect links where `S` appears as parent or child.

Relationship labels:

```text
child_segment_direct
parent_segment_direct
downstream_possible
template_uncertain
```

Example:

```text
LHand marker → LHand segment
LHand segment is child in LFArm→LHand
Therefore marker issue may affect LFArm→LHand as child_segment_direct.
```

For excluded fingers, the mapping can still exist, but the notebook should show that those links are excluded from likely V0 analysis.

---

## 6. Desired notebook workflow

The notebook should behave like a small scientific review application.

### Step 1 — Load one session

User provides or selects:

```text
Layer 1 QC file/folder
Layer 2 per-session export folder
```

The notebook loads:

```text
layer1_qc_events
layer2_filtered_rotvecs
layer2_link_manifest
layer2_session_summary
optional marker_to_link_map
```

Validation checks:

```text
session IDs match or are user-confirmed
frame ranges overlap
Layer 2 parquet has required columns
Layer 1 QC has frame or frame-range columns
Layer 2 link manifest joins to parquet by run_label + link_id
```

### Step 2 — Show session overview

Display:

```text
session_id
run_label
skeleton_template
frame_count
duration_sec
sampling_rate_hz
Layer 1 total artifact/gap frames
Layer 2 total links
core/review/excluded link counts
Stage 07 jump frames
Stage 08 jump-context rows
analysis-eligible row percentage
```

Also show a link overview table:

```text
link_id
parent→child
feature_scope
stage08_policy
stage08_output_scope
analysis eligible %
masked %
recommendation
```

### Step 3 — User chooses candidate frame range

Use widgets:

```text
IntRangeSlider for frame range
numeric start/end frame boxes
optional time display
Review Window button
```

The user chooses a candidate frame range.

No export happens yet.

### Step 4 — Window QC review

For the selected frame range, compute:

Layer 1 summary:

```text
number of raw marker artifact frames
number of raw marker gap frames
number of critical Layer 1 frames
percent of selected window affected
artifact clusters
markers/groups affected
```

Layer 2 summary:

```text
number of Stage 07 jump frames
number of Stage 08 jump-context rows
number of analysis-ineligible rows
number of NaN analysis rows
links affected by masks
critical links
review/provisional links
excluded links
```

Combined event table:

```text
source_layer
frame or frame range
time or time range
entity type
marker / segment / link
qc_type
severity
reason
recommended_action
mapping_confidence
```

### Step 5 — Joint/link recommendation table

For each available Layer 2 link, compute:

```text
link_id
parent_canonical
child_canonical
feature_scope
n_window_frames
n_analysis_eligible_frames
n_analysis_nan_frames
n_layer1_mapped_artifact_frames
n_layer2_jump_context_frames
percent_usable
has_critical_issue
recommendation
short_explanation
```

Recommended values:

```text
candidate_include
include_with_caution
manual_review
exclude_recommended
excluded_by_policy
blocked_needs_review
```

The recommendation should be transparent and rule-based.

### Step 6 — User chooses joints/links

Use an interactive widget, such as grouped checkboxes or a multi-select table.

Default selection:

```text
candidate_include links only
```

The user can override.

Recommended body groups:

```text
Head/neck
Left arm
Right arm
Left leg
Right leg
Trunk/review
Excluded distal/fingers
Excluded toes
```

The UI should show recommendation and usable percentage next to each link.

### Step 7 — User exports segment

User provides:

```text
segment_name
optional notes / justification
```

On submit, the notebook exports:

```text
segment_filtered_rotvecs.parquet
segment_qc_events.csv
segment_joint_summary.csv
segment_metadata.json
segment_review_report.md
segment_selection_log.json
```

---

## 7. Segment output specification

Each exported segment folder:

```text
outputs/segments/<session_id>/<segment_name>/
```

### 7.1 `segment_filtered_rotvecs.parquet`

Contains only selected frames and selected links.

Recommended columns:

```text
session_id
run_label
segment_id
segment_name
frame
time_sec
relative_frame
relative_time_sec
link_id
parent_canonical
child_canonical
feature_scope
rx_filtered_analysis
ry_filtered_analysis
rz_filtered_analysis
rotvec_norm_filtered_analysis
rx_filtered_native
ry_filtered_native
rz_filtered_native
rotvec_norm_filtered_native
stage08_analysis_eligible
stage08_mask_reason
stage08_within_jump_context_window
stage07_jump_status
stage08_policy
selected_for_segment
```

### 7.2 `segment_qc_events.csv`

One row per QC event inside the selected window.

Recommended columns:

```text
session_id
segment_id
source_layer
frame
start_frame
end_frame
time_sec
start_time_sec
end_time_sec
entity_type
entity_id
entity_name
marker_raw_name
mapped_segment
link_id
parent_canonical
child_canonical
mapping_confidence
qc_type
severity
reason
duration_frames
duration_seconds
recommended_action
```

### 7.3 `segment_joint_summary.csv`

One row per available or selected link.

Recommended columns:

```text
session_id
segment_id
link_id
parent_canonical
child_canonical
feature_scope
selected_for_segment
n_window_frames
n_analysis_eligible_frames
n_analysis_nan_frames
n_layer1_mapped_artifact_frames
n_layer2_masked_frames
percent_analysis_eligible
percent_masked
has_critical_issue
recommendation
short_explanation
```

### 7.4 `segment_metadata.json`

Machine-readable decision record:

```json
{
  "session_id": "...",
  "run_label": "...",
  "segment_id": "...",
  "segment_name": "...",
  "created_at": "...",
  "input_layer1_qc_path": "...",
  "input_layer2_export_folder": "...",
  "start_frame": 0,
  "end_frame": 0,
  "start_time_sec": 0.0,
  "end_time_sec": 0.0,
  "selected_links": [],
  "excluded_links": [],
  "user_notes": "...",
  "qc_summary": {},
  "software_version": "...",
  "git_commit": "..."
}
```

### 7.5 `segment_review_report.md`

Human-readable report:

```text
session identity
selected frame range
selected duration
selected links
excluded/review links
Layer 1 QC summary
Layer 2 QC summary
combined event summary
joint recommendation summary
user notes
limitations
statement that this is a candidate Layer 3 input, not final analysis
```

---

## 8. Implementation architecture

This should not be a giant notebook full of untested code.

Use a thin notebook plus reusable Python modules.

Recommended structure:

```text
notebooks/post_layer2_segmentation_review.ipynb
src/layer2_motive/segmentation/
  __init__.py
  schemas.py
  load_inputs.py
  validate_inputs.py
  marker_mapping.py
  qc_events.py
  window_summary.py
  recommendations.py
  export_segment.py
  widgets.py
```

The notebook should mostly call functions and display outputs.

### 8.1 `schemas.py`

Define required schemas and allowed values:

```text
Layer 1 normalized QC event schema
Layer 2 parquet schema
Marker-to-link mapping schema
Window event schema
Joint recommendation schema
Segment output schema
```

### 8.2 `load_inputs.py`

Functions:

```python
load_layer2_export(session_export_dir)
load_layer1_qc(layer1_qc_path)
load_marker_to_link_map(optional_path)
```

### 8.3 `validate_inputs.py`

Functions:

```python
validate_layer2_schema(df)
validate_layer1_schema(df)
validate_frame_alignment(layer1_events, layer2_df)
validate_link_manifest_join(layer2_df, link_manifest)
```

### 8.4 `marker_mapping.py`

Functions:

```python
build_marker_to_segment_map(raw_csv_header_or_layer1_markers, template_name)
build_marker_to_link_map(marker_to_segment_map, layer2_link_manifest)
map_layer1_events_to_links(layer1_events, marker_to_link_map)
```

This module should explicitly carry mapping confidence.

### 8.5 `window_summary.py`

Functions:

```python
summarize_window(layer1_events, layer2_df, start_frame, end_frame)
build_combined_qc_event_table(...)
compute_window_percentages(...)
```

### 8.6 `recommendations.py`

Functions:

```python
recommend_links_for_window(layer2_window_df, mapped_layer1_events, thresholds)
```

Rules should be explicit and configurable.

### 8.7 `export_segment.py`

Functions:

```python
export_segment(...)
write_segment_parquet(...)
write_segment_qc_events(...)
write_segment_joint_summary(...)
write_segment_metadata(...)
write_segment_report(...)
```

### 8.8 `widgets.py`

Functions:

```python
build_session_loader_widget(...)
build_frame_range_widget(...)
build_joint_selection_widget(...)
build_export_widget(...)
```

Widget state should be clear and not overly magical.

---

## 9. Recommended V1 implementation scope

V1 should be practical and stable.

### Include in V1

```text
load one session
load Layer 2 export folder
load Layer 1 QC event/mask file
normalize Layer 1 QC by frame
show session overview
frame-range widget
window QC summary
combined event table by frame/source
Layer 2 link recommendation table
joint/link selection widget
export segment parquet + logs
```

### Optional in V1 if feasible

```text
marker-to-link mapping from CSV header or name patterns
```

### Defer to V2

```text
timeline plots
video frame integration
automatic candidate-window suggestions
multi-session comparison
interactive body map
JcvPCA preparation
```

---

## 10. Recommendation logic for V1

The recommendation engine should not overclaim.

Basic rule examples:

### `candidate_include`

```text
feature_scope = core_candidate
percent_analysis_eligible >= 95%
no critical Layer 2 fail in selected window
no severe mapped Layer 1 issue
```

### `include_with_caution`

```text
core_candidate
90–95% analysis eligible
or isolated Layer 2 jump context
or small Layer 1 mapped artifact burden
```

### `manual_review`

```text
feature_scope = review_provisional
requires_manual_review = true
trunk/spine/hip mapping uncertainty
```

### `excluded_by_policy`

```text
feature_scope = excluded_distal or excluded_toe
stage08_policy = excluded_from_analysis
```

### `blocked_needs_review`

```text
core link has critical Layer 2 fail or large masked burden in the selected window
```

The notebook should allow the user to override, but overrides must be logged.

---

## 11. UX design requirements

The user experience should support scientific decision-making.

### 11.1 Progressive workflow

Do not show everything at once.

Recommended order:

```text
Load session
→ Session overview
→ Choose frame window
→ Review QC evidence
→ Review link recommendations
→ Choose links
→ Export segment
```

### 11.2 Decision transparency

Before export, show a final warning summary:

```text
Selected window contains:
- X Layer 1 artifact frames
- Y Layer 1 gap frames
- Z Layer 2 masked rows
- N selected links with caution
- M selected links requiring manual review
```

### 11.3 Human notes

If exporting with warnings, require a user note.

Example:

```text
This segment includes isolated Stage 8 jump-context masking on LFArm→LHand, accepted because only 61/12000 frames affected.
```

### 11.4 Avoid hidden auto-decisions

The notebook can recommend, but the user chooses.

All choices should be logged.

---

## 12. Testing strategy

Even though this is a notebook, the logic must be tested in modules.

Unit tests should cover:

```text
Layer 2 schema validation
Layer 1 QC normalization
frame-range subsetting
window summary percentages
combined QC event generation
marker-to-link mapping if implemented
joint recommendation rules
segment export files
metadata generation
```

Notebook should be manually tested, but core logic should be testable outside Jupyter.

---

## 13. Definition of done

The segmentation notebook V1 is complete when:

```text
1. The user can load one session.
2. The notebook validates Layer 1 and Layer 2 inputs.
3. The notebook shows a session overview.
4. The user can choose a frame range.
5. The notebook summarizes Layer 1 and Layer 2 QC for that range.
6. The notebook displays a combined QC event table.
7. The notebook recommends joints/links with explanations.
8. The user can select links with a widget.
9. The notebook exports a segment parquet.
10. The notebook exports QC/event logs and a review report.
11. Layer 1 and Layer 2 original outputs are never modified.
12. The exported segment preserves QC labels and user decisions.
```

---

## 14. Suggested implementation order

1. Define normalized schemas.
2. Implement Layer 2 export loader and validator.
3. Implement Layer 1 QC loader and normalizer.
4. Implement window frame-range subsetting.
5. Implement Layer 2 window QC summary.
6. Implement Layer 1 window QC summary.
7. Implement combined event table.
8. Implement basic joint recommendation table.
9. Implement segment export functions.
10. Build notebook widgets.
11. Add optional marker-to-link mapping support.
12. Add tests.
13. Run on one known session.
14. Review exported segment manually.
15. Only then extend to more sessions.

---

## 15. Recommended project name

Possible names:

```text
post_layer2_segmentation_review
segment_review_notebook
qc_guided_segmentation
```

Recommended name:

```text
post_layer2_segmentation_review
```

This name makes clear that this is not Layer 2 computation and not Layer 3 analysis.

---

## 16. Final summary

The next project should be an interactive, per-session segmentation notebook that integrates Layer 1 raw marker QC and Layer 2 filtered kinematic QC. The main challenge is that Layer 1 operates at marker × frame level, while Layer 2 operates at relative-link × frame level. The notebook should first support frame-level QC integration and then add marker-to-segment-to-link mapping with confidence labels.

The desired output is not a combined dataset. The desired output is a selected segment parquet plus a transparent review log documenting the chosen frame range, chosen links, QC events, masked frames, and human decisions.

This segmentation notebook is the human decision layer between Layer 2 and Layer 3.
