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

- Frames: 16000..17000 (inclusive)
- Duration (sec): 8.3417
- Window frames: 1001

## Review policies

- Gap policy: `strict`
- Export scope: `core_candidate`
- Mapping version: `heuristic_v0`
- Mapping source: `marker_name_heuristic`
- Template mapping status: `missing_datadescriptions_fallback_to_heuristic`
- DataDescriptions used: `False`

## Validation

- Safe to open: `True`
- Exact frame alignment: `True`

## Layer 1 summary

- Use frames: 619 (61.8382%)
- Caution frames: 174 (17.3826%)
- Exclude frames: 208 (20.7792%)
- gap_0p2 counted in burden: `True`

### Flag counts

- flag_gap_0p2: 221
- flag_gap_0p5: 208
- flag_artifact_sigma: 12
- flag_segment_swap: 20
- flag_edge_effect: 29

## Layer 2 summary

- Rows: 50050
- Links: 50
- Analysis eligible rows: 14893 (29.7562%)
- Core usable %: 92.9883

## Display tables

- QC event display rows: 37507
- Link scope display rows: 16
- Combined audit events: 37952
- Unmapped markers: 1

## Limitations

Layer 1 marker QC is regional risk evidence only. It is not mapped to specific Layer 2 links and does not invalidate joints.
DataDescriptions improves marker-to-bone interpretation when provided; Layer 2 remains authoritative for kinematic parent-child links.

## Unmapped evidence

Some Layer 1 QC evidence could not be assigned to a joint family. This does not automatically invalidate the window, but it should be reviewed.

## Optional gap files

- gaps_over_0p2s.csv: present_not_parsed_in_phase_5a
- gaps_over_0p5s.csv: present_not_parsed_in_phase_5a