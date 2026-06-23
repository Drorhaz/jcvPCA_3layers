# Post-Layer 2 Segmentation Notebook Plan — Revised with Template-Level DataDescriptions Mapping

**Project:** Gaga / OptiTrack-Motive kinematic QC pipeline  
**Module:** `post_layer2_segmentation_review`  
**Purpose:** Human-guided, scientifically defensible segment/window review between Layer 2 and Layer 3  
**Status:** Revised after inspecting representative Motive DataDescriptions for:
- `Core + Passive Fingers (54)` / T1-T2 style skeleton
- `Biomech (57)` / T3 style skeleton

---

## 1. Purpose of this document

This document defines the post-Layer 2 segmentation notebook and its supporting Python modules.

The notebook is **not Layer 1**, **not Layer 2**, and **not Layer 3**.

It is a bridge between:

```text
Layer 1 raw marker QC
Layer 2 solved skeleton kinematic QC
future Layer 3 analysis
```

The notebook should help the user choose:

1. A scientifically defensible frame/time window.
2. A transparent set of usable links/joints.
3. A segment export that preserves QC labels, mapping confidence, user decisions, and limitations.

The notebook must not run:

```text
PCA
JcvPCA
JRW
statistics
final scientific analysis
```

It produces candidate segmented outputs only.

---

## 2. Core scientific constraint

Layer 1 and Layer 2 describe different entities.

Layer 1 describes raw optical marker quality:

```text
marker × frame
```

Layer 2 describes solved skeleton kinematics:

```text
relative parent-child link / joint × frame
```

Therefore:

```text
A raw marker artifact is not automatically a joint artifact.
A marker gap is not automatically proof that a solved Layer 2 link is invalid.
Layer 1 marker QC can provide regional risk evidence.
Layer 2 QC provides link-level kinematic usability evidence.
The human reviewer makes the final segment/link decision.
```

This principle must guide all UX labels, display tables, recommendations, and exports.

---

## 2A. Core user decision workflow: tables before plots and export

The notebook is primarily a **decision interface**, not only a visualization notebook.

The central workflow is:

```text
1. User loads one session.
2. User chooses a candidate frame window.
3. User chooses which QC evidence should be included in the review/export.
4. User chooses the link/joint export scope.
5. Notebook generates two robust decision tables:
   A. QC Event Review Table
   B. Link / Joint Decision Table
6. User reviews the tables as confirmation/context.
7. Notebook exports a new parquet containing only:
   selected frames × links included by the chosen export scope
   annotated with QC fields determined by the selected QC evidence policy
   plus mapping and user-decision metadata.
```

Plots may help the user visually understand the data, but plots are secondary. The two decision tables are the core review objects.

For V1, the user should **not** be forced to select links/joints twice. The pre-table link/joint export scope is the export decision. The Link / Joint Decision Table explains and audits that decision. A later advanced mode may allow manual per-link overrides, but this is not required for the first implementation.

### 2A.1 User choices before generating review tables

Before the notebook generates the main tables, the user should choose:

```text
frame_start
frame_end
gap_policy
Layer 1 QC evidence types to include in review
Layer 2 QC evidence types to include in review
link/joint export scope
```

Recommended controls:

```text
Frame window:
  start_frame
  end_frame

Gap policy:
  strict
  relaxed

Layer 1 QC evidence:
  gap_0p5
  gap_0p2
  artifact_sigma
  segment_swap
  unlabeled_burst
  other raw marker QC events if present

Layer 2 QC evidence:
  Stage 07 jumps
  Stage 08 masked frames
  Stage 08 analysis eligibility
  block_filter links
  manual-review links

Link/joint export scope:
  core_candidate only
  core_candidate + review_provisional
  all non-excluded links
  all links including excluded distal/finger/toe links, advanced/audit mode only
```

The user-selected QC evidence policy and link/joint export scope should be stored in all downstream review outputs and segment metadata.

Important distinction:

```text
Full audit evidence is never deleted.
User-selected review evidence controls what enters the compact decision tables and recommendation calculations.
```

### 2A.2 Table 1 — QC Event Review Table

This is the event-level evidence table.

It should answer:

```text
Which QC events occurred inside the selected frame window?
Where did they occur?
Which marker/region/link is involved?
Which joint family may be relevant?
How confident is that mapping?
Was this event included in the current user review?
```

Primary output file:

```text
qc_event_display.csv
```

Conceptual display:

```text
Frame start | Frame end | Duration | QC type        | Reason         | Marker / region | Related joint family | Confidence
16020       | 16038     | 19       | artifact_sigma | velocity spike | 671:LHandIn     | left_wrist_hand      | medium
16110       | 16180     | 71       | gap_0p2        | marker gap     | 671:LWristOut   | left_elbow_forearm   | attached_bone_observed_and_template_verified
16200       | 16235     | 36       | segment_swap   | segment length | ChestTop__Waist | trunk_chest/pelvis   | template_uncertain
```

Required implementation columns:

```text
frame_start
frame_end
duration_frames
duration_seconds
qc_type
reason
marker_or_region
normalized_marker_name
attached_bone
attached_bone_canonical
related_joint_family
adjacent_joint_family
mapping_source
mapping_confidence
template_mapping_status
source_layer
included_in_user_review
recommendation_impact
```

Rules:

- This table is compact and notebook-facing.
- It is generated after the user chooses the frame window and QC evidence policy.
- Layer 1 rows use marker/region information plus marker-family mapping.
- Layer 2 rows use parent→child link information.
- Use `related_joint_family`, not exact `related_joint`, unless future mapping has been validated.
- `included_in_user_review` must distinguish visible audit evidence from evidence counted in the current decision.
- `gap_0p2` remains visible in relaxed mode but is marked as not counted.

### 2A.3 Table 2 — Link / Joint Decision Table

This is the link-level decision table.

It should answer:

```text
For each candidate Layer 2 link in the selected frame window,
what Layer 1 regional marker risk is nearby,
what Layer 2 usability is observed,
what is the recommendation,
and what will be exported under the chosen scope?
```

Primary output file:

```text
layer2_link_scope_display.csv
```

Conceptual display:

```text
Link / joint      Family             L1 gap_0p5  L1 artifact %  L1 swap %  L2 usable %  Recommendation
LUArm→LFArm       left_elbow_forearm  0           0.8%           0.0%       100.0%       candidate_include
LFArm→LHand       left_wrist_hand     18          7.2%           0.0%       0.0%         blocked_needs_review
Ab→Chest          trunk_chest         0           3.1%           2.4%       96.2%        manual_review
LThigh→LShin      left_thigh_knee     0           0.0%           0.0%       99.8%        candidate_include
```

Required implementation columns:

```text
link_id
link_or_joint
parent_canonical
child_canonical
family
feature_scope
view_scope
n_gap_0p5_related_frames
gap_0p5_related_percent
n_gap_0p2_related_frames
gap_0p2_related_percent
gap_0p2_counted_in_burden
artifact_sigma_related_percent
segment_swap_related_percent
layer2_usable_percent
layer2_masked_percent
mapping_version
template_mapping_status
recommendation
export_scope
included_by_export_scope
user_override
user_note
```

Rules:

- One row per available Layer 2 link within the chosen display scope.
- Layer 1 columns are marker-family/regional risk overlays.
- Layer 2 usability comes from Stage 08 analysis eligibility.
- Layer 1 marker QC must not directly invalidate a link.
- `recommendation` is the system suggestion/context.
- `export_scope` records the user's pre-table scope choice.
- `included_by_export_scope` controls whether that link enters the exported parquet.
- `user_override` is optional and should be reserved for a later advanced mode; it is not required in V1.

### 2A.4 Three table states

The workflow must explicitly distinguish three table states.

#### State 1 — Full audit tables

Purpose:

```text
traceability and reproducibility
```

Examples:

```text
combined_qc_events.csv
segment_qc_events.csv
```

These tables preserve all events and should not be filtered destructively.

#### State 2 — User-filtered review tables

Purpose:

```text
human decision-making for the selected window
```

Examples:

```text
qc_event_display.csv
layer2_link_scope_display.csv
layer1_marker_family_risk.csv
combined_qc_event_summary.csv
window_qc_summary_display.csv
```

These tables reflect:

```text
selected frame window
selected gap policy
selected QC evidence types
selected link/joint export scope
```

#### State 3 — Final export decision tables

Purpose:

```text
record the chosen segment and user decisions
```

Examples:

```text
segment_joint_summary.csv
segment_selection_log.json
segment_metadata.json
segment_review_report.md
```

These must record:

```text
selected frames
selected/exported links
excluded links
export scope
optional user overrides, if advanced mode is implemented
user notes
gap policy
mapping version
template verification status
```

### 2A.5 Exported parquet contract

In V1, the user does not need to choose links/joints twice. The link/joint export scope chosen before table generation determines which links enter the export.

The exported parquet must contain only:

```text
selected frame window × Layer 2 links included by the chosen export scope
```

It must include kinematic rotation-vector features:

```text
rx_filtered_analysis
ry_filtered_analysis
rz_filtered_analysis
rotvec_norm_filtered_analysis
rx_filtered_native
ry_filtered_native
rz_filtered_native
rotvec_norm_filtered_native
```

It must also include QC provenance and user-decision metadata:

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
family
feature_scope
stage08_analysis_eligible
stage08_mask_reason
stage08_within_jump_context_window
stage07_jump_status
l1_related_gap_0p5
l1_related_gap_0p2
l1_related_artifact_sigma
l1_related_segment_swap
gap_policy
mapping_version
template_mapping_status
recommendation
export_scope
included_by_export_scope
user_override
```

The exported parquet is therefore not just “clean data.” It is:

```text
selected kinematic data + QC provenance + user decision metadata
```

### 2A.6 Updated notebook UX order

The user-facing notebook should follow this order:

```text
Load session
→ validate Layer 1 and Layer 2 alignment
→ verify mapping template if available
→ choose frame window
→ choose QC evidence policy
→ choose link/joint export scope
→ generate QC Event Review Table
→ generate Link / Joint Decision Table as review/confirmation
→ export selected segment parquet using the chosen export scope
→ export decision log and review report
```

This workflow should be treated as the central UX contract.

---

## 3. What Layer 2 owns versus what DataDescriptions owns

### 3.1 Layer 2 remains authoritative for kinematic parent-child links

Layer 2 parent-child links must continue to come from the validated Layer 2 skeleton hierarchy and Stage 06 relative-quaternion logic.

Layer 2 computation remains:

```text
parent_global_quaternion
child_global_quaternion
relative_quaternion = inverse(parent_global_quaternion) * child_global_quaternion
relative_rotation_vector = log(relative_quaternion)
filter / mask / export
```

DataDescriptions must **not** rewrite Layer 2 kinematic computation.

The following stay under Layer 2 authority:

```text
parent_canonical
child_canonical
link_id
relative quaternion
rotation-vector features
Stage 07 jump diagnostics
Stage 08 filtering/masking
analysis eligibility
feature_scope
```

### 3.2 DataDescriptions supports marker-to-bone interpretation

DataDescriptions can improve the mapping from:

```text
Layer 1 marker QC event
→ attached Motive bone / segment
→ joint family / possible related link family
```

This is useful for the notebook’s **marker-family risk overlay**.

DataDescriptions may be used to:

```text
parse Bone Marker rows
extract marker → attached bone
extract bone hierarchy for template verification
create template-level marker-to-bone maps
verify a session against an approved template map
annotate marker-derived risk evidence
```

DataDescriptions must not be used to silently change Layer 2 parent-child logic.

If DataDescriptions and Layer 2 hierarchy disagree:

```text
do not rewrite Layer 2
flag mismatch
set template_mapping_status = mismatch_manual_review
require manual review before using the mapping overlay
```

---

## 4. Current known skeleton templates and DataDescriptions findings

Two representative DataDescriptions files were reviewed.

### 4.1 Core + Passive Fingers (54)

Representative file:

```text
671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001_DataDescriptions.csv
```

Observed structure:

```text
51 Bone rows
54 Bone Marker rows
108 Marker rows
```

This corresponds to the T1/T2-style:

```text
Core + Passive Fingers (54)
```

Simplified trunk hierarchy:

```text
671 → Ab → Chest → Neck → Head
```

Important marker-to-attached-bone examples:

```text
LHandIn / LHandOut → 671_LHand
LWristOut / LFArm → 671_LFArm
LUArmHigh / LElbowOut → 671_LUArm
ChestTop / ChestLow / BackTop / BackLeft / BackRight → 671_Chest
WaistLFront / WaistRFront / WaistLBack / WaistRBack / WaistCBack → 671_671
LKneeOut / LThighFront / LThighSide → 671_LThigh
LAnkleOut / LShin → 671_LShin
LToeOut / LToeIn / LHeel → 671_LFoot
LToeTip → 671_LToe
```

Important interpretation:

```text
671_671 = asset-name-labeled hip/top segment / MotiveHip-top segment
```

Do not blindly call this “pelvis” without noting that it is Motive’s asset-name-labeled top/hip segment.

### 4.2 Biomech (57)

Representative file:

```text
671_T3_P1_R1_Take 2026-02-03 08.05.01 PM_000_DataDescriptions.csv
```

Observed structure:

```text
55 Bone rows
54 Bone Marker rows
108 Marker rows
```

This corresponds to the T3-style:

```text
Biomech (57)
```

Main difference from Core + Passive Fingers:

```text
same marker set size
different bone hierarchy
additional intermediate spine/neck bones
```

Simplified Biomech trunk path:

```text
T3_671 → Ab → Bone52 → Bone53 → Bone54 → Chest → Neck → Bone58 → Head
```

Important intermediate bones:

```text
Bone52
Bone53
Bone54
Bone58
```

Most limb marker mappings are stable relative to Core + Passive Fingers after stripping the asset prefix:

```text
LHandIn / LHandOut → LHand
LWristOut / LFArm → LFArm
LUArmHigh / LElbowOut → LUArm
LThighFront / LThighSide → LThigh
LShin → LShin
LToeIn / LToeOut / LHeel → LFoot
LToeTip → LToe
ChestTop / ChestLow / BackTop / BackLeft / BackRight → Chest
Head markers → Head
```

Important trunk/waist difference:

```text
Core:
WaistLFront → 671
WaistRFront → 671
WaistLBack  → 671
WaistRBack  → 671
WaistCBack  → 671

Biomech:
WaistLFront → T3_671
WaistRFront → T3_671
WaistLBack  → T3_671
WaistRBack  → T3_671
WaistCBack  → Bone53
```

This means:

```text
WaistCBack is template-sensitive.
In Biomech, WaistCBack maps to an intermediate spine/trunk bone, not directly to the top hip segment.
```

Therefore trunk, pelvis, waist, spine, chest, neck, and head mappings should remain cautious and template-aware.

---

## 5. Mapping architecture: approve once per skeleton template, verify every session

The correct architecture is **not** to generate a new mapping silently for every session.

The correct architecture is:

```text
Create one approved mapping per skeleton template/version.
Verify each session against that approved mapping.
Do not silently update the approved mapping.
Create a new mapping version only after manual review.
```

Current approved mapping targets:

```text
core_passive_fingers_54_v1
biomech_57_v1
```

### 5.1 Template mapping library

Recommended folder structure:

```text
mappings/
  core_passive_fingers_54_v1/
    marker_to_bone_map.csv
    bone_hierarchy.csv
    marker_to_joint_family_map.csv
    mapping_manifest.json
    mapping_review_report.md

  biomech_57_v1/
    marker_to_bone_map.csv
    bone_hierarchy.csv
    marker_to_joint_family_map.csv
    mapping_manifest.json
    mapping_review_report.md
```

### 5.2 Session verification

For every future session, if a `_DataDescriptions.csv` file is available:

1. Parse the session DataDescriptions.
2. Detect skeleton template.
3. Compare marker names, attached bones, bone count, marker count, and hierarchy signature against the approved template mapping.
4. If compatible, use the approved template mapping.
5. If mismatch, warn and require manual review.
6. Do not silently update the template mapping.

Possible session mapping statuses:

```text
verified_against_template
compatible_minor_name_difference
missing_datadescriptions_fallback_to_heuristic
template_mismatch_manual_review
session_datadescriptions_unapproved
```

### 5.3 If DataDescriptions is missing

The notebook must still work.

Fallback hierarchy:

```text
Priority 1:
approved_template_datadescriptions mapping, if session verifies against it

Priority 2:
session DataDescriptions mapping, only if manually approved as a new template version

Priority 3:
body_region_group + marker side

Priority 4:
marker-name heuristic

Priority 5:
unknown / unmapped
```

DataDescriptions is preferred but optional.

---

## 6. Mapping source and confidence fields

Use separate source and confidence fields.

Recommended fields:

```text
mapping_source
mapping_confidence
template_mapping_status
mapping_version
```

Recommended `mapping_source` values:

```text
approved_template_datadescriptions
session_datadescriptions_unapproved
body_region_group
marker_name_heuristic
unmapped
```

Recommended `mapping_confidence` values:

```text
attached_bone_observed_and_template_verified
attached_bone_observed_but_template_unverified
medium
low
template_uncertain
unmapped
```

Do not use `high` loosely.

Rationale:

```text
DataDescriptions gives strong marker→bone evidence.
It does not prove that a marker artifact invalidates a solved kinematic link.
```

---

## 7. Canonical joint families

Use these joint-family labels:

```text
head_neck
trunk_chest
pelvis_hip
left_shoulder_arm
left_elbow_forearm
left_wrist_hand
right_shoulder_arm
right_elbow_forearm
right_wrist_hand
left_thigh_knee
left_shank_ankle
left_foot
right_thigh_knee
right_shank_ankle
right_foot
bilateral_upper_limb
bilateral_lower_limb
fingers_excluded
toes_excluded
unknown
```

### 7.1 Why add fingers_excluded and toes_excluded

DataDescriptions confirms that the skeleton includes finger and toe marker/bone structures:

```text
LThumb / LIndex / LPinky / RThumb / RIndex / RPinky
LToeTip / RToeTip
```

These should not be silently grouped into ordinary hand/foot analysis.

Use:

```text
fingers_excluded
toes_excluded
```

to preserve visibility while respecting V0/V1 analysis policy.

---

## 8. Important mapping refinements from DataDescriptions

### 8.1 Wrist / forearm

DataDescriptions shows:

```text
LWristOut → LFArm
RWristOut → RFArm
LHandIn / LHandOut → LHand
RHandIn / RHandOut → RHand
```

Therefore do not simply map all wrist-named markers to `left_wrist_hand`.

Better:

```text
LWristOut:
  attached_bone = LFArm
  joint_family = left_elbow_forearm
  adjacent_joint_family = left_wrist_hand

LHandIn / LHandOut:
  attached_bone = LHand
  joint_family = left_wrist_hand
```

Equivalent right-side logic applies.

### 8.2 Waist / MotiveHip-top segment

Core template:

```text
Waist markers → 671_671
```

Biomech template:

```text
WaistLFront / WaistRFront / WaistLBack / WaistRBack → T3_671
WaistCBack → Bone53
```

Therefore waist markers should be treated as:

```text
pelvis_hip / trunk-spine regional risk
template_uncertain for exact link mapping
```

### 8.3 Chest / trunk

Chest and back markers map consistently to Chest in both inspected templates:

```text
ChestTop / ChestLow / BackTop / BackLeft / BackRight → Chest
```

Use:

```text
joint_family = trunk_chest
```

but retain caution because trunk topology differs by template.

### 8.4 Toes and fingers

ToeTip markers map to toe bones and should be labeled:

```text
toes_excluded
```

Finger markers should be labeled:

```text
fingers_excluded
```

unless a later analysis explicitly includes distal/finger/toe links.

---

## 9. Marker-derived risk is not link invalidation

Even when DataDescriptions maps a marker to a bone, do not write:

```text
this joint is invalid
```

Use language such as:

```text
marker-derived risk evidence
possible related link family
regional risk overlay
attached bone affected by marker QC event
```

Example:

```text
LHandIn marker gap → attached bone LHand → risk evidence for left_wrist_hand / possible LFArm→LHand context
```

Not:

```text
LFArm→LHand is invalid
```

A solved Layer 2 link may remain usable despite a local marker event, especially if Motive solved the skeleton robustly and Layer 2 Stage 07/08 diagnostics remain clean.

---

## 10. Updated notebook-facing display tables

### 10.1 Window QC summary display

File:

```text
window_qc_summary_display.csv
```

Required columns:

```text
session_key
frame_start
frame_end
duration_frames
duration_seconds
gap_policy
total_frames
gap_0p5_percent
gap_0p2_percent
gap_0p2_counted_in_burden
artifact_sigma_percent
segment_swap_percent
overall_raw_qc_status
layer2_core_usable_percent
layer2_review_usable_percent
layer2_excluded_usable_percent
n_layer1_display_events
n_layer2_display_events
n_unmapped_markers
n_unmapped_events
mapping_version
template_mapping_status
```

Rules:

- In relaxed mode, report `gap_0p2_percent` but set `gap_0p2_counted_in_burden = false`.
- Example display:

```text
gap_0p2: 4.2% — not counted under relaxed policy
```

- Do not mix excluded distal/finger/toe links into core usability.

### 10.2 QC event display table

File:

```text
qc_event_display.csv
```

Required columns:

```text
frame_start
frame_end
duration_frames
duration_seconds
qc_type
reason
marker_or_region
normalized_marker_name
attached_bone
attached_bone_canonical
related_joint_family
adjacent_joint_family
mapping_source
mapping_confidence
template_mapping_status
source_layer
recommendation_impact
```

Rules:

- Use `related_joint_family`, not exact `related_joint`, unless future mapping has been validated.
- Layer 1 rows may show attached bone and possible related family.
- Layer 2 rows use parent→child link as entity display and link family as related family.
- This table should be compact enough for notebook display.
- Full audit remains in `combined_qc_events.csv`.

### 10.3 Link-level usability + marker-family risk table

File:

```text
layer2_link_scope_display.csv
```

This table should not be called only “Layer 2 QC by link scope,” because it includes Layer 1 marker-derived regional-risk columns.

Required columns:

```text
link_id
link_or_joint
family
feature_scope
view_scope
n_gap_0p5_related_frames
gap_0p5_related_percent
n_gap_0p2_related_frames
gap_0p2_related_percent
gap_0p2_counted_in_burden
artifact_sigma_related_percent
segment_swap_related_percent
layer2_usable_percent
layer2_masked_percent
mapping_version
template_mapping_status
recommendation_placeholder
selection_default
```

Rules:

- Layer 1 columns are marker-family/regional risk overlays.
- Layer 2 usable percent comes from Stage 08 analysis eligibility.
- Layer 1 marker QC must not directly invalidate a link.
- `selection_default` remains false until recommendations are implemented.

### 10.4 Layer 1 marker-family risk table

File:

```text
layer1_marker_family_risk.csv
```

Required columns:

```text
session_id
run_label
marker_or_entity
normalized_marker_name
body_region_group
side
attached_bone
attached_bone_canonical
joint_family
adjacent_joint_family
mapping_source
mapping_confidence
mapping_version
template_mapping_status
n_events
n_frames_affected
gap_0p5_frames
gap_0p2_frames
artifact_sigma_frames
segment_swap_frames
severity_summary
recommendation_impact
notes
```

### 10.5 Combined event summary

File:

```text
combined_qc_event_summary.csv
```

Recommended grouping dimensions:

```text
source_layer
qc_type
severity
reason
joint_family
mapping_source
mapping_confidence
template_mapping_status
feature_scope
```

---

## 11. Gap policy

The user must be able to choose:

```text
strict:
  count both gap_0p2 and gap_0p5

relaxed:
  count gap_0p5 only
  ignore gap_0p2 when computing burden/recommendation impact
```

But relaxed mode must not hide `gap_0p2`.

Required behavior:

```text
gap_0p2 is always visible
gap_0p2 is counted only in strict mode
gap_policy is recorded in every relevant output
raw audit events are never deleted because of relaxed policy
```

CLI option:

```bash
--gap-policy strict|relaxed
```

---

## 12. Link/joint export scope and core-only default

The notebook must support a link/joint export-scope control. In V1, this single scope choice determines both what the main link table displays and what links are exported, unless a later advanced override mode is explicitly added.

```text
Export scope:
(o) Core candidate links only
( ) Core + manual-review links
( ) All non-excluded links
( ) All links including excluded distal/fingers/toes, advanced/audit mode only
```

Default:

```text
Core candidate links only
```

Rules:

- Core candidate links are exported by default.
- Manual-review links are included only if the user chooses the broader export scope.
- Excluded distal/finger/toe links are hidden/collapsed by default and should not be exported in normal V1 mode.
- Excluded links remain available in full audit.
- Excluded links must not be mixed into core usability percentages.
- A separate per-link manual override can be added later as an advanced mode, but it is not required for V1.

---

## 13. Unmapped evidence

Unmapped markers/entities must remain visible.

Unknown marker/entity mapping:

```text
joint_family = unknown
mapping_confidence = unmapped
mapping_source = unmapped
```

Required behavior:

- Unmapped rows remain in full audit outputs.
- Unmapped rows appear in display summaries.
- Unmapped count appears in window summary.
- Unmapped evidence does not automatically block analysis.
- Unmapped evidence is not silently dropped.

Notebook message if count > 0:

```text
Some Layer 1 QC evidence could not be assigned to a joint family.
This does not automatically invalidate the window, but it should be reviewed.
```

---

## 14. Audit outputs versus display outputs

Keep full audit separate from compact display.

Full audit outputs:

```text
combined_qc_events.csv
segment_qc_events.csv
```

Compact notebook-facing display outputs:

```text
window_qc_summary_display.csv
qc_event_display.csv
combined_qc_event_summary.csv
layer2_link_scope_display.csv
layer1_marker_family_risk.csv
```

Rules:

- Notebook shows compact display tables by default.
- Full audit is linked/downloadable or shown on demand.
- Display tables must be smaller than full audit tables.
- Audit completeness must be preserved.

Principle:

```text
Audit complete; display compact.
```

---

## 15. Expected implementation architecture

Recommended structure:

```text
notebooks/post_layer2_segmentation_review.ipynb

src/layer2_motive/segmentation/
  __init__.py
  schemas.py
  load_inputs.py
  validate_inputs.py
  qc_events.py
  window_summary.py
  marker_family.py
  template_mapping.py
  recommendations.py
  export_segment.py
  widgets.py

scripts/
  validate_segmentation_inputs.py
  review_segmentation_window.py
  build_template_mapping.py
  verify_session_mapping.py
```

### 15.1 `marker_family.py`

Purpose:

```text
fallback marker/body_region_group → joint_family mapping
normalization of marker names
side inference
pair-event handling
unmapped handling
```

### 15.2 `template_mapping.py`

Purpose:

```text
parse DataDescriptions
extract Bone Marker rows
extract Bone hierarchy rows
build template-level mapping artifacts
verify session DataDescriptions against approved template mapping
provide mapping_source / mapping_confidence / template_mapping_status
```

Important:

```text
template_mapping.py annotates marker-derived risk.
It does not rewrite Layer 2 parent-child links.
```

---

## 16. Recommended implementation phases

### Phase A — Current UX / marker-family checkpoint

Implement now:

```text
user-selected frame window
user-selected QC evidence policy
gap policy
compact decision tables before plots/export
QC Event Review Table
Link / Joint Decision Table
link/joint export scope fields with core-only default
unmapped visible
heuristic marker-family overlay
DataDescriptions fields/hooks, but not required
```

Outputs:

```text
window_qc_summary_display.csv
qc_event_display.csv
layer2_link_scope_display.csv
layer1_marker_family_risk.csv
combined_qc_event_summary.csv
combined_qc_events.csv
```

The first five are compact user-facing review outputs. `combined_qc_events.csv` remains the full audit output.

This phase must pass even without any DataDescriptions file.

### Phase B — Template-level DataDescriptions mapping

Implement next, as a controlled optional phase:

```text
build core_passive_fingers_54_v1 mapping from representative T1/T2 file
build biomech_57_v1 mapping from representative T3 file
write mapping artifacts
verify future sessions against approved mapping
fallback if DataDescriptions is absent
warn/block on mismatch
```

Outputs:

```text
mappings/<mapping_version>/marker_to_bone_map.csv
mappings/<mapping_version>/bone_hierarchy.csv
mappings/<mapping_version>/marker_to_joint_family_map.csv
mappings/<mapping_version>/mapping_manifest.json
mappings/<mapping_version>/mapping_review_report.md
mapping_verification_report.csv
mapping_verification_report.md
```

### Phase C — Recommendations

Implement later:

```text
recommend_links_for_window(...)
link_recommendations.csv
```

Recommendation classes:

```text
candidate_include
include_with_caution
manual_review
exclude_recommended
excluded_by_policy
blocked_needs_review
```

### Phase D — Segment export

Implement later:

```text
segment_filtered_rotvecs.parquet
segment_qc_events.csv
segment_joint_summary.csv
segment_metadata.json
segment_review_report.md
segment_selection_log.json
```

### Phase E — Notebook widgets

Implement after tested CLI/module logic:

```text
frame range widget
gap policy selector
core-only view selector
link selection widget
export widget
```

---

## 17. Testing requirements

### Phase A tests

Add tests for:

```text
strict vs relaxed gap policy
gap_0p2 counted in strict but not relaxed
gap_0p2 visible in relaxed mode
window QC summary display columns
QC event display columns
Layer 2 link scope display columns
Layer 1 marker-family risk columns
marker side inference
marker family mapping from body_region_group
pair-event mapping
trunk/pelvis template_uncertain mapping
unknown marker maps to unknown/unmapped
Layer 1 overlay does not assign exact Layer 2 link IDs
display outputs written by CLI
display tables smaller than full audit
unmapped rows visible in outputs
link/joint export scope fields with core-only default present
DataDescriptions not required
```

### Phase B tests

Add tests for:

```text
parse Core + Passive Fingers DataDescriptions
parse Biomech DataDescriptions
extract Bone Marker rows
extract Bone hierarchy rows
normalize marker names:
  671:LHandIn
  671_LHandIn
  LHandIn
match approved template mapping
detect marker count mismatch
detect attached-bone mismatch
detect hierarchy mismatch
fallback when DataDescriptions missing
do not update template mapping silently
do not rewrite Layer 2 parent-child links
```

Run:

```bash
pytest
ruff check src tests scripts
```

---

## 18. Stop-and-report requirements for Cursor/agent

After Phase A, report:

```text
files created/modified
display outputs created
strict vs relaxed comparison for the same window
gap_0p2 display behavior in relaxed mode
marker-family examples from the real fixture
number of unmapped markers/entities
whether unmapped rows are visible
whether link/joint export scope fields with core-only default are present
confirmation that DataDescriptions is not required
pytest/ruff results
limitations before recommendations/widgets
```

After Phase B, report:

```text
template mappings created
Core + Passive Fingers mapping summary
Biomech mapping summary
number of Bone Marker rows parsed per template
number of Bone rows parsed per template
major mapping differences between templates
session verification result
mismatches or unmapped entries
confirmation that Layer 2 parent-child logic was not changed
pytest/ruff results
limitations before recommendations/widgets/export
```

---

## 19. Segment export requirements for later phases

When export is implemented, exported segment folders should include:

```text
segment_filtered_rotvecs.parquet
segment_qc_events.csv
segment_joint_summary.csv
segment_metadata.json
segment_review_report.md
segment_selection_log.json
```

`segment_metadata.json` should include:

```text
session_id
run_label
segment_id
segment_name
created_at
input_layer1_qc_path
input_layer2_export_folder
start_frame
end_frame
start_time_sec
end_time_sec
selected_links
excluded_links
export_scope
gap_policy
mapping_version
template_mapping_status
user_notes
qc_summary
software_version
git_commit
```

---

## 20. Final scientific wording rules

Use:

```text
Layer 1 marker-derived regional risk
marker-family risk overlay
related_joint_family
attached_bone
possible related link family
Layer 2 link usability
analysis-clean mask
policy mask
manual review
template_uncertain
unmapped
```

Avoid:

```text
marker artifact invalidates joint
raw marker issue proves link is wrong
exact related joint
Layer 1 and Layer 2 merged as same entity
DataDescriptions rewrites Layer 2 links
```

Preferred phrasing:

```text
DataDescriptions improves marker-to-bone and marker-to-family interpretation.
Layer 2 remains authoritative for kinematic parent-child computation.
Marker-derived QC evidence is regional risk evidence, not proof of link invalidity.
```

---

## 21. Bottom-line implementation principle

```text
Audit complete.
Display compact.
Decision tables before plots/export.
Mapping conservative.
Template mappings approved once.
Sessions verified every time.
Layer 2 kinematics unchanged.
User chooses the frame window, QC evidence policy, and link/joint export scope once.
Export only selected frames × links included by that scope, annotated with the selected QC evidence policy and QC provenance.
```
