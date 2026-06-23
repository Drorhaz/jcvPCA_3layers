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

## Validation

- Safe to open: `True`
- Exact frame alignment: `True`

## Layer 1 summary

- Use frames: 619 (61.8382%)
- Caution frames: 174 (17.3826%)
- Exclude frames: 208 (20.7792%)

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
- Analysis ineligible rows: 35157
- Jump context rows: 1159
- Stage 07 fail rows: 9009
- Stage 07 warn rows: 10010

## Combined QC events

- Total combined events: 37952
- Layer 1 events: 915
- Layer 2 events: 37037

### Top Layer 1 reasons

- GAP_GE_0P5: 122
- GAP_GE_0P2: 118
- GAP_GE_0P5;GAP_GE_0P2: 82
- EDGE_EFFECT: 29
- GAP_GE_0P2;SEGMENT_SWAP: 19
- ARTIFACT_SIGMA: 7
- GAP_GE_0P5;ARTIFACT_SIGMA: 3
- GAP_GE_0P2;ARTIFACT_SIGMA;SEGMENT_SWAP: 1
- GAP_GE_0P5;GAP_GE_0P2;ARTIFACT_SIGMA: 1

### Top Layer 2 mask reasons

- excluded_feature_scope: 31056
- manual_review_provisional: 2002
- stage07_jump_status=warning: 1880
- stage07_jump_context: 1159
- blocked_needs_review: 940

## Optional gap files

- gaps_over_0p2s.csv: present_not_parsed_in_phase_5a
- gaps_over_0p5s.csv: present_not_parsed_in_phase_5a

## Limitations

Layer 1 marker QC is summarized as frame/window evidence only in V1. It is not mapped to specific Layer 2 links.
