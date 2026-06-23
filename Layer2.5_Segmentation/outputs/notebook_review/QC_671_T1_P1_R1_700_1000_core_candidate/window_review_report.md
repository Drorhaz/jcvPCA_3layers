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

- Frames: 700..1000 (inclusive)
- Duration (sec): 2.5083
- Window frames: 301

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

- Use frames: 301 (100.0%)
- Caution frames: 0 (0.0%)
- Exclude frames: 0 (0.0%)
- gap_0p2 counted in burden: `True`

### Flag counts

- flag_gap_0p2: 0
- flag_gap_0p5: 0
- flag_artifact_sigma: 0
- flag_segment_swap: 0
- flag_edge_effect: 0

## Layer 2 summary

- Rows: 15050
- Links: 50
- Analysis eligible rows: 4515 (30.0%)
- Core usable %: 93.75

## Display tables

- QC event display rows: 11137
- Link scope display rows: 16
- Combined audit events: 11137
- Unmapped markers: 0

## Limitations

Layer 1 marker QC is regional risk evidence only. It is not mapped to specific Layer 2 links and does not invalidate joints.
DataDescriptions improves marker-to-bone interpretation when provided; Layer 2 remains authoritative for kinematic parent-child links.

## Optional gap files

- gaps_over_0p2s.csv: present_not_parsed_in_phase_5a
- gaps_over_0p5s.csv: present_not_parsed_in_phase_5a