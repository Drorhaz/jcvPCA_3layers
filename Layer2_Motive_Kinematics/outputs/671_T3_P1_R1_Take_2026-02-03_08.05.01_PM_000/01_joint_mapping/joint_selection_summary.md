# Joint selection summary (provisional — not frozen)

## Feature selection boundary

- `selected_joint_map_v0.csv` is **provisional** (`frozen = false`).
- This file does **not** define the final analysis feature set.
- Final analysis feature selection is deferred until after Layer 2 output validation and before Layer 3 JcvPCA. See `docs/FEATURE_SELECTION_BOUNDARY.md`.

## Overview

- Bones in inventory: 55
- Candidate parent-child joints: 55
- Provisional auto-included joints (heuristic only): 17
- Excluded distal/toe/finger candidates: 32
- Uncertain candidates requiring manual review: 8
- Structural population check: 0 fail, 0 warning (see `rotation_population_report.csv`)

## Detected skeleton / root anchor

Root/asset anchor bones are reported exactly as detected in the CSV. They are **not** renamed to Pelvis unless that name appears in the export.

- Source `T3_671:T3_671` → canonical `T3_671` (parent `Root`)

## Trunk chain / main hierarchy summary

- Chain 1: T3_671 → Ab → Spine2 → Spine3 → Spine4 → Chest → Neck → Neck2

## Provisional auto-included joints

- `Neck2` → `Head` (J003)
- `LUArm` → `LFArm` (J004)
- `LShin` → `LFoot` (J005)
- `LFArm` → `LHand` (J006)
- `LThigh` → `LShin` (J019)
- `Chest` → `LShoulder` (J020)
- `T3_671` → `LThigh` (J021)
- `LShoulder` → `LUArm` (J026)
- `Chest` → `Neck` (J027)
- `Neck` → `Neck2` (J028)
- `RUArm` → `RFArm` (J029)
- `RShin` → `RFoot` (J030)
- `RFArm` → `RHand` (J031)
- `RThigh` → `RShin` (J044)
- `Chest` → `RShoulder` (J045)
- `T3_671` → `RThigh` (J046)
- `RShoulder` → `RUArm` (J051)

## Root / trunk candidates requiring review

- `Root` → `T3_671` (reason=parent_is_root, review=True)
- `T3_671` → `Ab` (reason=trunk_or_root_candidate, review=True)
- `Spine4` → `Chest` (reason=trunk_or_root_candidate, review=True)
- `Ab` → `Spine2` (reason=trunk_or_root_candidate, review=True)
- `Spine2` → `Spine3` (reason=trunk_or_root_candidate, review=True)
- `Spine3` → `Spine4` (reason=trunk_or_root_candidate, review=True)

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

- `T3_671` → `Ab` (rule=trunk_or_root_candidate, reason=none)
- `Spine4` → `Chest` (rule=trunk_or_root_candidate, reason=none)
- `LFoot` → `LToe` (rule=distal_exclusion.cautious_keywords, reason=cautious_keyword:Toe)
- `RFoot` → `RToe` (rule=distal_exclusion.cautious_keywords, reason=cautious_keyword:Toe)
- `Ab` → `Spine2` (rule=trunk_or_root_candidate, reason=none)
- `Spine2` → `Spine3` (rule=trunk_or_root_candidate, reason=none)
- `Spine3` → `Spine4` (rule=trunk_or_root_candidate, reason=none)
- `Root` → `T3_671` (rule=exclude_root_children_by_default, reason=parent_is_root)

## Next step

Validate native skeleton documentation, provisional joint heuristics, and structural population reports for this file. Continue to Stage 02 only after review.
Do not treat `selected_joint_map_v0.csv` as the final Layer 3 feature set.
