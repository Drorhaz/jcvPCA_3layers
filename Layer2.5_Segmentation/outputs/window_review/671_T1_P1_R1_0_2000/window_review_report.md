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

- Frames: 0..2000 (inclusive)
- Duration (sec): 16.6750
- Window frames: 2001

## Validation

- Safe to open: `True`
- Exact frame alignment: `True`

## Layer 1 summary

- Use frames: 1518 (75.8621%)
- Caution frames: 148 (7.3963%)
- Exclude frames: 335 (16.7416%)

### Flag counts

- flag_gap_0p2: 0
- flag_gap_0p5: 335
- flag_artifact_sigma: 0
- flag_segment_swap: 408
- flag_edge_effect: 16

## Layer 2 summary

- Rows: 100050
- Links: 50
- Analysis eligible rows: 30015 (30.0%)
- Analysis ineligible rows: 70035
- Jump context rows: 0
- Stage 07 fail rows: 18009
- Stage 07 warn rows: 20010

## Combined QC events

- Total combined events: 75289
- Layer 1 events: 1252
- Layer 2 events: 74037

### Top Layer 1 reasons

- GAP_GE_0P5;SEGMENT_SWAP: 268
- SEGMENT_SWAP: 132
- GAP_GE_0P5: 67
- SEGMENT_SWAP;EDGE_EFFECT: 8
- EDGE_EFFECT: 8

### Top Layer 2 mask reasons

- excluded_feature_scope: 64032
- manual_review_provisional: 4002
- stage07_jump_status=warning: 4002
- blocked_needs_review: 2001

## Optional gap files

- gaps_over_0p2s.csv: present_not_parsed_in_phase_5a
- gaps_over_0p5s.csv: present_not_parsed_in_phase_5a

## Limitations

Layer 1 marker QC is summarized as frame/window evidence only in V1. It is not mapped to specific Layer 2 links.
