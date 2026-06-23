# Joint selection summary (provisional — not frozen)

## Feature selection boundary

- `selected_joint_map_v0.csv` is **provisional** (`frozen = false`).
- This file does **not** define the final analysis feature set.
- Final analysis feature selection is deferred until after Layer 2 output validation and before Layer 3 JcvPCA. See `docs/FEATURE_SELECTION_BOUNDARY.md`.

## Overview

- Bones in inventory: 51
- Candidate parent-child joints: 51
- Provisional auto-included joints (heuristic only): 16
- Excluded distal/toe/finger candidates: 32
- Uncertain candidates requiring manual review: 5
- Structural population check: 0 fail, 0 warning (see `rotation_population_report.csv`)

## Detected skeleton / root anchor

Root/asset anchor bones are reported exactly as detected in the CSV. They are **not** renamed to Pelvis unless that name appears in the export.

- Source `671:671` → canonical `671` (parent `Root`)

## Trunk chain / main hierarchy summary

- Chain 1: 671 → Ab → Chest → Neck

## Provisional auto-included joints

- `Neck` → `Head` (J004)
- `LUArm` → `LFArm` (J005)
- `LShin` → `LFoot` (J006)
- `LFArm` → `LHand` (J007)
- `LThigh` → `LShin` (J020)
- `Chest` → `LShoulder` (J021)
- `671` → `LThigh` (J022)
- `LShoulder` → `LUArm` (J027)
- `Chest` → `Neck` (J028)
- `RUArm` → `RFArm` (J029)
- `RShin` → `RFoot` (J030)
- `RFArm` → `RHand` (J031)
- `RThigh` → `RShin` (J044)
- `Chest` → `RShoulder` (J045)
- `671` → `RThigh` (J046)
- `RShoulder` → `RUArm` (J051)

## Root / trunk candidates requiring review

- `Root` → `671` (reason=parent_is_root, review=True)
- `671` → `Ab` (reason=trunk_or_root_candidate, review=True)
- `Ab` → `Chest` (reason=trunk_or_root_candidate, review=True)

## Excluded distal / finger / toe candidates

- `LHand` → `LIndex1`: distal_keyword:Index
- `LIndex1` → `LIndex2`: distal_keyword:Index
- `LIndex2` → `LIndex3`: distal_keyword:Index
- `LHand` → `LMiddle1`: distal_keyword:Middle
- `LMiddle1` → `LMiddle2`: distal_keyword:Middle
- `LMiddle2` → `LMiddle3`: distal_keyword:Middle
- `LHand` → `LPinky1`: distal_keyword:Pinky
- `LPinky1` → `LPinky2`: distal_keyword:Pinky
- `LPinky2` → `LPinky3`: distal_keyword:Pinky
- `LHand` → `LRing1`: distal_keyword:Ring
- `LRing1` → `LRing2`: distal_keyword:Ring
- `LRing2` → `LRing3`: distal_keyword:Ring
- `LHand` → `LThumb1`: distal_keyword:Thumb
- `LThumb1` → `LThumb2`: distal_keyword:Thumb
- `LThumb2` → `LThumb3`: distal_keyword:Thumb
- `LFoot` → `LToe`: cautious_keyword:Toe
- `RHand` → `RIndex1`: distal_keyword:Index
- `RIndex1` → `RIndex2`: distal_keyword:Index
- `RIndex2` → `RIndex3`: distal_keyword:Index
- `RHand` → `RMiddle1`: distal_keyword:Middle
- `RMiddle1` → `RMiddle2`: distal_keyword:Middle
- `RMiddle2` → `RMiddle3`: distal_keyword:Middle
- `RHand` → `RPinky1`: distal_keyword:Pinky
- `RPinky1` → `RPinky2`: distal_keyword:Pinky
- `RPinky2` → `RPinky3`: distal_keyword:Pinky
- `RHand` → `RRing1`: distal_keyword:Ring
- `RRing1` → `RRing2`: distal_keyword:Ring
- `RRing2` → `RRing3`: distal_keyword:Ring
- `RHand` → `RThumb1`: distal_keyword:Thumb
- `RThumb1` → `RThumb2`: distal_keyword:Thumb
- `RThumb2` → `RThumb3`: distal_keyword:Thumb
- `RFoot` → `RToe`: cautious_keyword:Toe

## All uncertain candidates

- `Root` → `671` (rule=exclude_root_children_by_default, reason=parent_is_root)
- `671` → `Ab` (rule=trunk_or_root_candidate, reason=none)
- `Ab` → `Chest` (rule=trunk_or_root_candidate, reason=none)
- `LFoot` → `LToe` (rule=distal_exclusion.cautious_keywords, reason=cautious_keyword:Toe)
- `RFoot` → `RToe` (rule=distal_exclusion.cautious_keywords, reason=cautious_keyword:Toe)

## Next step

Validate native skeleton documentation, provisional joint heuristics, and structural population reports for this file. Continue to Stage 02 only after review.
Do not treat `selected_joint_map_v0.csv` as the final Layer 3 feature set.
