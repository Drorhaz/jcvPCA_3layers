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
| Session ID | `T1_P1_R1` |
| Input file | `671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv` |
| Motive version | `Motive:Body 3.4.0.2` |
| Export type detected | `consistent_with_marker_xyz` |
| Frame rate | `120.0` Hz |
| Frame range | `0-30603` |
| Duration | `255.025` seconds |
| Units | `Meters` |
| Labeled markers | `54` |
| Unlabeled marker tracks | `48` |
| Parse validation | `pass` |

---

## 2. Per-marker gap evidence (≥0.5 s)

**Dominant gap marker:** `LShoulderTop` — `1.274343`% of session frames in that marker's gaps; `1.274385`% of session duration in gap.

| Marker (canonical) | Body region | Gaps ≥0.5 s | Total gap (s) | Longest gap (s) | % frames in gap | % session time in gap |
|---|---|---:|---:|---:|---:|---:|
| `LShoulderTop` | `shoulder_upper_arm` | `1` | `3.25` | `3.25` | `1.274343` | `1.274385` |
| `ChestTop` | `torso_chest_back` | `1` | `2.7917` | `2.7917` | `1.094628` | `1.094677` |
| `LElbowOut` | `elbow_forearm` | `3` | `2.0583` | `0.8167` | `0.807084` | `0.807097` |
| `RFArm` | `shoulder_upper_arm` | `2` | `1.7333` | `1.125` | `0.67965` | `0.679659` |
| `RHandIn` | `wrist_hand` | `1` | `1.425` | `1.425` | `0.55875` | `0.558769` |
| `WaistLFront` | `pelvis_waist` | `1` | `1.4167` | `1.4167` | `0.555483` | `0.555514` |
| `LFArm` | `shoulder_upper_arm` | `1` | `0.7833` | `0.7833` | `0.307149` | `0.307146` |
| `LHandIn` | `wrist_hand` | `1` | `0.6417` | `0.6417` | `0.251601` | `0.251622` |

See `tables/layer1_marker_gap_evidence.csv` for the full table.

---

## 3. Union frame mask (any marker can trigger a frame flag)

| Flag | % of frames |
|---|---:|
| `flag_gap_0p5` | `4.973206` |
| `flag_gap_0p2` | `3.989675` |
| `flag_artifact_sigma` | `0.614299` |
| `flag_segment_swap` | `6.711541` |
| Any flag | `13.024441` |
| Dominant interval criterion | `artifact_sigma` |

Union `flag_gap_0p5` can match a single bad marker — compare with §2 before excluding body regions.

---

## 4. Marker set identity

| Field | Value |
|---|---|
| Asset prefix(es) observed | `671` |
| Canonical marker count | `54` |
| Marker set ID (hash) | `f843d515a491ec5b` |
| Marker set warning | `none` |

---

## 5. Marker completeness and gap structure

| Metric | Value |
|---|---:|
| Labeled marker missingness | `0.304154%` |
| Markers with any missing frames | `20` |
| Total continuous labeled-marker gaps | `279` |
| Gaps >=0.2 s | `47` |
| Gaps >=0.5 s | `11` |
| Longest labeled-marker gap | `3.25` s on `671:LShoulderTop` |
| Markers with gap >=0.5 s | `671:ChestTop;671:LElbowOut;671:LFArm;671:LHandIn;671:LShoulderTop;671:RFArm;671:RHandIn;671:WaistLFront` |
| Critical body-region large gaps present | `yes` |

**Gap summary:** Longest labeled gap: 671:LShoulderTop (3.250s); 11 gaps >=0.5s across 8 marker(s).

See `tables/gaps_over_0p5s.csv` for per-marker gap intervals (includes `marker_name_canonical`).

---

## 6. Unlabeled-marker burden

| Metric | Value |
|---|---:|
| Frames with any unlabeled marker | `719` |
| Percent frames with unlabeled markers | `2.349366%` |
| Max unlabeled markers in one frame | `3` |
| Longest unlabeled burst | `0.825` s |

---

## 7. Candidate artifact screening (labeled markers only)

| Metric | Value |
|---|---:|
| Artifact events | `272` |
| Single-frame events | `216` |
| Short bursts (2-5 frames) | `24` |
| Sustained events (>5 frames) | `32` |
| Frames with velocity candidate | `188` |
| Frames with acceleration candidate | `0` |
| Frames with **both** vel and accel | `0` |

See `tables/artifact_events.csv` for per-marker artifact events.

### Markers with gaps >=0.5 s (top rows)

| Marker (canonical) | Body region | Total gap (s) | Longest gap (s) |
|---|---|---:|---:|
| `LElbowOut` | `elbow_forearm` | `2.0583` | `0.8167` |
| `RFArm` | `shoulder_upper_arm` | `1.7333` | `1.125` |
| `LShoulderTop` | `shoulder_upper_arm` | `3.25` | `3.25` |
| `ChestTop` | `torso_chest_back` | `2.7917` | `2.7917` |
| `RHandIn` | `wrist_hand` | `1.425` | `1.425` |
| `WaistLFront` | `pelvis_waist` | `1.4167` | `1.4167` |
| `LFArm` | `shoulder_upper_arm` | `0.7833` | `0.7833` |
| `LHandIn` | `wrist_hand` | `0.6417` | `0.6417` |

---

---

## 8. Analysis windows (0.5 s)

- **0.5 s windows:** 511 total; 154 with gap overlap; 143 with artifact events; 169 with non-empty reason_codes.
- **1.0 s windows:** 256 total; 102 with gap overlap; 95 with artifact events; 111 with non-empty reason_codes.

---

## 9. Frame flag summary

| Reason code | Frames (analysis mask) |
|---|---:|
| `none` | 20297 |
| `ARTIFACT_EVENT_IN_WINDOW` | 4320 |
| `SUSTAINED_ARTIFACT_IN_WINDOW` | 4260 |
| `GAP_OVERLAP` | 2580 |
| `CRITICAL_GROUP_GAP` | 2040 |
| `LARGE_GAP` | 1522 |
| `LARGE_GAP_OVERLAP` | 1380 |
| `MODERATE_GAP` | 1063 |
| `ELEVATED_MISSING` | 60 |
| `ELEVATED_MISSING_LABELED` | 3 |

### Flagged intervals (labeled markers; see `qc_mask_intervals.csv`)

| Start | End | Duration | Body groups | Dominant gap marker | Reason |
|---:|---:|---:|---|---|---|
| 1080 | 1259 | 1.491667 | torso_chest_back;wrist_hand | `nan` | Sustained artifact event (>5 frames) in window |
| 1260 | 1275 | 0.125 | torso_chest_back;wrist_hand | `nan` | Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 1276 | 1319 | 0.358334 | torso_chest_back;wrist_hand | `671:ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 1320 | 1559 | 1.991667 | pelvis_waist;torso_chest_back;wrist_hand | `671:ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 1560 | 1610 | 0.416667 | torso_chest_back | `671:ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 5100 | 5459 | 2.991667 | torso_chest_back | `nan` | Sustained artifact event (>5 frames) in window |
| 5460 | 5466 | 0.05 | torso_chest_back | `nan` | Labeled gap >=0.2 s overlaps analysis window; Sustained artifact event (>5 frames) in window |
| 5467 | 5519 | 0.433334 | shoulder_upper_arm;torso_chest_back | `671:LShoulderTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Sustained artifact event (>5 frames) in window |
| 5520 | 5819 | 2.491667 | shoulder_upper_arm;torso_chest_back | `671:LShoulderTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Sustained artifact event (>5 frames) in window |
| 5820 | 5856 | 0.3 | shoulder_upper_arm;torso_chest_back | `671:LShoulderTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Sustained artifact event (>5 frames) in window |
| 5857 | 5881 | 0.2 | shoulder_upper_arm;torso_chest_back | `671:LShoulderTop` | Labeled gap >=0.2 s overlaps analysis window; Sustained artifact event (>5 frames) in window |
| 5882 | 5913 | 0.258333 | shoulder_upper_arm;torso_chest_back | `671:LShoulderTop` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.2 s overlaps analysis window; Sustained artifact event (>5 frames) in window |
| 5914 | 5939 | 0.208334 |  | `nan` | Labeled gap >=0.2 s overlaps analysis window; Sustained artifact event (>5 frames) in window |
| 5940 | 5999 | 0.491667 | shoulder_upper_arm | `nan` | One or more artifact events overlap analysis window |
| 7179 | 7212 | 0.275 | wrist_hand | `671:RHandIn` | Labeled gap >=0.2 s overlaps interval |
| 7800 | 7859 | 0.491667 | wrist_hand | `nan` | Sustained artifact event (>5 frames) in window |
| 11682 | 11715 | 0.275 | wrist_hand | `671:RHandIn` | Labeled gap >=0.2 s overlaps interval |
| 12117 | 12119 | 0.016667 | wrist_hand | `671:RHandIn` | Labeled gap >=0.5 s overlaps this interval |
| 12120 | 12239 | 0.991667 | torso_chest_back;wrist_hand | `671:RHandIn` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Sustained artifact event (>5 frames) in window |
| 12240 | 12287 | 0.391667 | torso_chest_back;wrist_hand | `671:RHandIn` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Sustained artifact event (>5 frames) in window |
| 12288 | 12299 | 0.091667 | torso_chest_back | `nan` | Labeled gap >=0.2 s overlaps analysis window; Sustained artifact event (>5 frames) in window |
| 12300 | 12599 | 2.491667 | torso_chest_back;wrist_hand | `nan` | Sustained artifact event (>5 frames) in window |
| 14280 | 14339 | 0.491667 | pelvis_waist;wrist_hand | `671:RHandIn` | Sustained artifact event (>5 frames) in window |
| 14340 | 14379 | 0.325 | wrist_hand | `671:RHandIn` | Labeled gap >=0.2 s overlaps analysis window |
| 14380 | 14399 | 0.158334 | shoulder_upper_arm | `671:LFArm` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window |
| 14400 | 14459 | 0.491667 | shoulder_upper_arm;torso_chest_back;wrist_hand | `671:LFArm` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; One or more artifact events overlap analysis window |
| 14460 | 14473 | 0.108333 | shoulder_upper_arm;wrist_hand | `671:LFArm` | Labeled gap >=0.5 s overlaps this interval |
| 14580 | 14586 | 0.05 |  | `nan` | Labeled gap >=0.2 s overlaps analysis window; One or more artifact events overlap analysis window |
| 14587 | 14610 | 0.191667 | shoulder_upper_arm;wrist_hand | `671:RHandIn` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.2 s overlaps analysis window; One or more artifact events overlap analysis window |
| 14611 | 14639 | 0.233334 | shoulder_upper_arm;wrist_hand | `671:LHandIn` | Labeled gap >=0.2 s overlaps analysis window; One or more artifact events overlap analysis window |

---

## 10. Reason code glossary

See `qc_reason_codes.md` in the run folder for full code definitions.

---

## Summary

Layer 1 recorded 272 artifact events and 11 labeled gaps >=0.5 s on 8 marker(s). Union frame mask: 4.973206% of frames have `flag_gap_0p5` (dominant marker `LShoulderTop`: 1.274343% of frames in its gaps). Use `layer1_marker_gap_evidence.csv`, `gaps_over_0p5s.csv`, `artifact_events.csv`, and `layer1_qc_handoff.csv` for downstream planning.


## Validation messages

- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
