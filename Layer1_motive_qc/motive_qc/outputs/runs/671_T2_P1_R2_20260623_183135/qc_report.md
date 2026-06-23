# Raw Motive Marker QC Report

> **Evidence-only report.** Layer 1 records per-marker gaps, artifacts, and frame flags.
> It does not assign session go/no-go labels. Downstream layers choose marker subsets and windows.

## Layer guide

- **Layer 2:** per-marker gaps and missingness (evidence).
- **Layer 4:** kinematic artifact **events** on gap-safe segments (candidates only).
- **Layer 3:** fixed-duration windows with factual `reason_codes` (no verdict labels).
- **Layer 5:** `qc_mask.csv` frame flags + `gaps_over_0p5s.csv` / `artifact_events.csv` per-marker tables.

---

## 1. Session and export identity

| Field | Value |
|---|---|
| Session ID | `T2_P1_R2` |
| Input file | `671_T2_P1_R2_Take 2026-01-15 04.35.25 PM_009.csv` |
| Motive version | `Motive:Body 3.4.0.2` |
| Export type detected | `consistent_with_marker_xyz` |
| Frame rate | `120.0` Hz |
| Frame range | `0-30478` |
| Duration | `253.983` seconds |
| Units | `Meters` |
| Labeled markers | `108` |
| Unlabeled marker tracks | `23` |
| Parse validation | `pass_with_warnings` |

---

## 2. Per-marker gap evidence (≥0.5 s)

**Dominant gap marker:** `ChestTop` — `2.926605`% of session frames in that marker's gaps; `2.926688`% of session duration in gap.

| Marker (canonical) | Body region | Gaps ≥0.5 s | Total gap (s) | Longest gap (s) | % frames in gap | % session time in gap |
|---|---|---:|---:|---:|---:|---:|
| `ChestTop` | `torso_chest_back` | `3` | `7.4333` | `5.2667` | `2.926605` | `2.926688` |
| `LHandOut` | `wrist_hand` | `2` | `2.2417` | `1.6167` | `0.882575` | `0.882617` |
| `ChestLow` | `torso_chest_back` | `2` | `1.3167` | `0.7833` | `0.51839` | `0.51842` |
| `LThighFront` | `thigh_knee` | `1` | `0.5833` | `0.5833` | `0.229666` | `0.229661` |
| `RKneeOut` | `thigh_knee` | `1` | `0.5333` | `0.5333` | `0.209981` | `0.209974` |

See `tables/layer1_marker_gap_evidence.csv` for the full table.

---

## 3. Union frame mask (any marker can trigger a frame flag)

| Flag | % of frames |
|---|---:|
| `flag_gap_0p5` | `4.60645` |
| `flag_gap_0p2` | `1.410807` |
| `flag_artifact_sigma` | `0.551199` |
| `flag_segment_swap` | `1.76515` |
| Any flag | `8.48453` |
| Dominant interval criterion | `artifact_sigma` |

Union `flag_gap_0p5` can match a single bad marker — compare with §2 before excluding body regions.

---

## 4. Marker set identity

| Field | Value |
|---|---|
| Asset prefix(es) observed | `671;FKA-671` |
| Canonical marker count | `54` |
| Marker set ID (hash) | `f843d515a491ec5b` |
| Marker set warning | `MULTIPLE_ASSET_PREFIXES:671,FKA-671; ASSET_PREFIX_FKA-671 (participant 671; compare canonical_marker_names / marker_set_id across sessions)` |

---

## 5. Marker completeness and gap structure

| Metric | Value |
|---|---:|
| Labeled marker missingness | `0.161108%` |
| Markers with any missing frames | `73` |
| Total continuous labeled-marker gaps | `128` |
| Gaps >=0.2 s | `21` |
| Gaps >=0.5 s | `9` |
| Longest labeled-marker gap | `5.266667` s on `FKA-671_ChestTop` |
| Markers with gap >=0.5 s | `FKA-671_ChestLow;FKA-671_ChestTop;FKA-671_LHandOut;FKA-671_LThighFront;FKA-671_RKneeOut` |
| Critical body-region large gaps present | `yes` |

**Gap summary:** Longest labeled gap: FKA-671_ChestTop (5.267s); 9 gaps >=0.5s across 5 marker(s).

See `tables/gaps_over_0p5s.csv` for per-marker gap intervals (includes `marker_name_canonical`).

---

## 6. Unlabeled-marker burden

| Metric | Value |
|---|---:|
| Frames with any unlabeled marker | `2002` |
| Percent frames with unlabeled markers | `6.568457%` |
| Max unlabeled markers in one frame | `3` |
| Longest unlabeled burst | `8.416667` s |

---

## 7. Candidate artifact screening (labeled markers only)

| Metric | Value |
|---|---:|
| Artifact events | `227` |
| Single-frame events | `189` |
| Short bursts (2-5 frames) | `18` |
| Sustained events (>5 frames) | `20` |
| Frames with velocity candidate | `168` |
| Frames with acceleration candidate | `0` |
| Frames with **both** vel and accel | `0` |

See `tables/artifact_events.csv` for per-marker artifact events.

### Markers with gaps >=0.5 s (top rows)

| Marker (canonical) | Body region | Total gap (s) | Longest gap (s) |
|---|---|---:|---:|
| `ChestTop` | `torso_chest_back` | `7.4333` | `5.2667` |
| `LHandOut` | `wrist_hand` | `2.2417` | `1.6167` |
| `ChestLow` | `torso_chest_back` | `1.3167` | `0.7833` |
| `LThighFront` | `thigh_knee` | `0.5833` | `0.5833` |
| `RKneeOut` | `thigh_knee` | `0.5333` | `0.5333` |

---

---

## 8. Analysis windows (0.5 s)

- **0.5 s windows:** 508 total; 110 with gap overlap; 88 with artifact events; 130 with non-empty reason_codes.
- **1.0 s windows:** 254 total; 80 with gap overlap; 65 with artifact events; 86 with non-empty reason_codes.

---

## 9. Frame flag summary

| Reason code | Frames (analysis mask) |
|---|---:|
| `none` | 22675 |
| `CRITICAL_GROUP_GAP` | 3300 |
| `ARTIFACT_EVENT_IN_WINDOW` | 3180 |
| `SUSTAINED_ARTIFACT_IN_WINDOW` | 2100 |
| `LARGE_GAP` | 1404 |
| `LARGE_GAP_OVERLAP` | 1140 |
| `GAP_OVERLAP` | 1080 |
| `MODERATE_GAP` | 408 |

### Flagged intervals (labeled markers; see `qc_mask_intervals.csv`)

| Start | End | Duration | Body groups | Dominant gap marker | Reason |
|---:|---:|---:|---|---|---|
| 648 | 659 | 0.091667 | thigh_knee | `FKA-671_LThighFront` | Labeled gap >=0.5 s overlaps this interval; Gap in critical body region (torso/pelvis/head/legs) |
| 660 | 717 | 0.475 | thigh_knee | `FKA-671_LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 888 | 899 | 0.091667 | torso_chest_back | `FKA-671_ChestLow` | Labeled gap >=0.5 s overlaps this interval; Gap in critical body region (torso/pelvis/head/legs) |
| 900 | 1199 | 2.491667 | torso_chest_back | `FKA-671_ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 1200 | 1379 | 1.491667 | pelvis_waist;thigh_knee;torso_chest_back | `FKA-671_ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 1380 | 1499 | 0.991667 | torso_chest_back | `FKA-671_ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 1500 | 1534 | 0.283333 | torso_chest_back | `FKA-671_ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 4260 | 4319 | 0.491667 | torso_chest_back | `FKA-671_ChestTop` | Gap in critical body region (torso/pelvis/head/legs) |
| 4320 | 4379 | 0.491667 | torso_chest_back | `nan` | Sustained artifact event (>5 frames) in window |
| 5880 | 5939 | 0.491667 | torso_chest_back | `nan` | Sustained artifact event (>5 frames) in window |
| 7740 | 7799 | 0.491667 | thigh_knee | `FKA-671_LThighFront` | Gap in critical body region (torso/pelvis/head/legs) |
| 10980 | 11037 | 0.475 | thigh_knee | `FKA-671_LThighFront` | Gap in critical body region (torso/pelvis/head/legs) |
| 11038 | 11039 | 0.008334 | thigh_knee | `FKA-671_LThighFront` | Labeled gap >=0.2 s overlaps interval; Gap in critical body region (torso/pelvis/head/legs) |
| 11040 | 11082 | 0.35 | thigh_knee | `FKA-671_LThighFront` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 14220 | 14279 | 0.491667 | torso_chest_back | `nan` | One or more artifact events overlap analysis window |
| 14359 | 14389 | 0.25 | torso_chest_back | `FKA-671_ChestLow` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 14390 | 14459 | 0.575 | torso_chest_back;wrist_hand | `FKA-671_LHandIn` | Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 14460 | 14519 | 0.491667 | wrist_hand | `nan` | One or more artifact events overlap analysis window |
| 14580 | 14639 | 0.491667 | torso_chest_back | `FKA-671_ChestLow` | Gap in critical body region (torso/pelvis/head/legs) |
| 14640 | 14664 | 0.2 | torso_chest_back | `FKA-671_ChestLow` | Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 14665 | 14690 | 0.208334 | wrist_hand | `FKA-671_LHandIn` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 14760 | 14775 | 0.125 |  | `nan` | Labeled gap >=0.2 s overlaps analysis window; One or more artifact events overlap analysis window |
| 14776 | 14819 | 0.358334 | wrist_hand | `FKA-671_LHandOut` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; One or more artifact events overlap analysis window |
| 14820 | 14879 | 0.491667 | wrist_hand | `FKA-671_LHandOut` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window |
| 14880 | 14939 | 0.491667 | torso_chest_back;wrist_hand | `FKA-671_LHandOut` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 14940 | 14969 | 0.241667 | torso_chest_back;wrist_hand | `FKA-671_LHandOut` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 15116 | 15119 | 0.025 | wrist_hand | `FKA-671_LHandOut` | Labeled gap >=0.2 s overlaps interval |
| 15120 | 15159 | 0.325 | torso_chest_back;wrist_hand | `FKA-671_LHandOut` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 15160 | 15179 | 0.158334 | torso_chest_back | `FKA-671_ChestLow` | Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 15240 | 15299 | 0.491667 | torso_chest_back;wrist_hand | `FKA-671_ChestLow` | Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |

---

## 10. Reason code glossary

See `qc_reason_codes.md` in the run folder for full code definitions.

---

## Summary

Layer 1 recorded 227 artifact events and 9 labeled gaps >=0.5 s on 5 marker(s). Union frame mask: 4.60645% of frames have `flag_gap_0p5` (dominant marker `ChestTop`: 2.926605% of frames in its gaps). Use `layer1_marker_gap_evidence.csv`, `gaps_over_0p5s.csv`, `artifact_events.csv`, and `layer1_qc_handoff.csv` for downstream planning.


## Validation messages

- **[WARNING] PHANTOM_SKELETON_QUARANTINED:** Competing labeled skeleton(s) detected; using 'FKA-671' for analysis and quarantining phantom skeleton(s): 671.
- **[WARNING] PHANTOM_SKELETON_QUARANTINED:** Competing labeled skeleton(s) detected; using 'FKA-671' for analysis and quarantining phantom skeleton(s): 671.
- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
- **[WARNING] PHANTOM_SKELETON_QUARANTINED:** Competing labeled skeleton(s) detected; using 'FKA-671' for analysis and quarantining phantom skeleton(s): 671.
- **[WARNING] PHANTOM_SKELETON_QUARANTINED:** Competing labeled skeleton(s) detected; using 'FKA-671' for analysis and quarantining phantom skeleton(s): 671.
- **[WARNING] PHANTOM_SKELETON_QUARANTINED:** Competing labeled skeleton(s) detected; using 'FKA-671' for analysis and quarantining phantom skeleton(s): 671.
- **[WARNING] PHANTOM_SKELETON_QUARANTINED:** Competing labeled skeleton(s) detected; using 'FKA-671' for analysis and quarantining phantom skeleton(s): 671.
- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
- **[WARNING] PHANTOM_SKELETON_QUARANTINED:** Competing labeled skeleton(s) detected; using 'FKA-671' for analysis and quarantining phantom skeleton(s): 671.
- **[WARNING] PHANTOM_SKELETON_QUARANTINED:** Competing labeled skeleton(s) detected; using 'FKA-671' for analysis and quarantining phantom skeleton(s): 671.
