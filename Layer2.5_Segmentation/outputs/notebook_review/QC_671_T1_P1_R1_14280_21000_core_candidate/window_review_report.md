# Window QC Review Report

## Session identity

- Session key: `671_T1_P1_R1`
- Layer 1 run_key: `671_T1_P1_R1`
- Layer 2 session_id: `671_T1_P1_R1`
- Layer 2 run_label: `671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001`

## Input folders

- Layer 1: `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2.5_Segmentation/input/Layer1_QC/QC_671_T1_P1_R1`
- Layer 2: `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2.5_Segmentation/input/Layer2_Kinematics/671_T1_P1_R1`

## Selected window

- Frames: 14280..21000 (inclusive)
- Duration (sec): 56.0083
- Window frames: 6721

## Review policies

- Gap policy: `strict`
- Export scope: `core_candidate`
- Mapping version: `session_datadescriptions_unverified_v0`
- Mapping source: `session_datadescriptions_optional`
- Template mapping status: `session_datadescriptions_used_unverified`
- DataDescriptions used: `True`

## Validation

- Safe to open: `True`
- Exact frame alignment: `True`

## Layer 1 summary

- Use frames: 4995 (74.3193%)
- Caution frames: 1100 (16.3666%)
- Exclude frames: 626 (9.3141%)
- gap_0p2 counted in burden: `True`

### Flag counts

- flag_gap_0p2: 972
- flag_gap_0p5: 626
- flag_artifact_sigma: 71
- flag_segment_swap: 226
- flag_edge_effect: 93

## Layer 2 summary

- Rows: 336050
- Links: 50
- Analysis eligible rows: 100693 (29.9637%)
- Core usable %: 93.6365

## Display tables

- QC event display rows: 248814
- Link scope display rows: 16
- Combined audit events: 250646
- Unmapped markers: 5

## Limitations

Layer 1 marker QC is regional risk evidence only. It is not mapped to specific Layer 2 links and does not invalidate joints.
DataDescriptions improves marker-to-bone interpretation when provided; Layer 2 remains authoritative for kinematic parent-child links.

## Unmapped evidence

Some Layer 1 QC evidence could not be assigned to a joint family. This does not automatically invalidate the window, but it should be reviewed.

## Optional gap files

- gaps_over_0p2s.csv: present_parsed
- gaps_over_0p5s.csv: present_parsed
- artifact_events.csv: present_parsed
- artifacts_by_segment.csv: present_regional_summary