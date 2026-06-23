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
| Session ID | `T3_P1_R1` |
| Input file | `671_T3_P1_R1_Take 2026-02-03 08.05.01 PM_000.csv` |
| Motive version | `Motive:Body 3.4.0.2` |
| Export type detected | `consistent_with_marker_xyz` |
| Frame rate | `120.0` Hz |
| Frame range | `0-31673` |
| Duration | `263.942` seconds |
| Units | `Meters` |
| Labeled markers | `54` |
| Unlabeled marker tracks | `20` |
| Parse validation | `pass` |

---

## 2. Per-marker gap evidence (≥0.5 s)

**Dominant gap marker:** `ChestTop` — `1.635411`% of session frames in that marker's gaps; `1.635475`% of session duration in gap.

| Marker (canonical) | Body region | Gaps ≥0.5 s | Total gap (s) | Longest gap (s) | % frames in gap | % session time in gap |
|---|---|---:|---:|---:|---:|---:|
| `ChestTop` | `torso_chest_back` | `1` | `4.3167` | `4.3167` | `1.635411` | `1.635475` |
| `RHandOut` | `wrist_hand` | `2` | `4.0167` | `2.8` | `1.521753` | `1.521814` |
| `RHandIn` | `wrist_hand` | `2` | `1.6167` | `1.0` | `0.61249` | `0.612522` |

See `tables/layer1_marker_gap_evidence.csv` for the full table.

---

## 3. Union frame mask (any marker can trigger a frame flag)

| Flag | % of frames |
|---|---:|
| `flag_gap_0p5` | `3.769653` |
| `flag_gap_0p2` | `2.222643` |
| `flag_artifact_sigma` | `0.448317` |
| `flag_segment_swap` | `1.310223` |
| Any flag | `6.869988` |
| Dominant interval criterion | `artifact_sigma` |

Union `flag_gap_0p5` can match a single bad marker — compare with §2 before excluding body regions.

---

## 4. Marker set identity

| Field | Value |
|---|---|
| Asset prefix(es) observed | `T3_671` |
| Canonical marker count | `54` |
| Marker set ID (hash) | `f843d515a491ec5b` |
| Marker set warning | `ASSET_PREFIX_T3_671 (participant 671; compare canonical_marker_names / marker_set_id across sessions)` |

---

## 5. Marker completeness and gap structure

| Metric | Value |
|---|---:|
| Labeled marker missingness | `0.165422%` |
| Markers with any missing frames | `22` |
| Total continuous labeled-marker gaps | `128` |
| Gaps >=0.2 s | `28` |
| Gaps >=0.5 s | `5` |
| Longest labeled-marker gap | `4.316667` s on `T3_671:ChestTop` |
| Markers with gap >=0.5 s | `T3_671:ChestTop;T3_671:RHandIn;T3_671:RHandOut` |
| Critical body-region large gaps present | `yes` |

**Gap summary:** Longest labeled gap: T3_671:ChestTop (4.317s); 5 gaps >=0.5s across 3 marker(s).

See `tables/gaps_over_0p5s.csv` for per-marker gap intervals (includes `marker_name_canonical`).

---

## 6. Unlabeled-marker burden

| Metric | Value |
|---|---:|
| Frames with any unlabeled marker | `587` |
| Percent frames with unlabeled markers | `1.853255%` |
| Max unlabeled markers in one frame | `3` |
| Longest unlabeled burst | `1.65` s |

---

## 7. Candidate artifact screening (labeled markers only)

| Metric | Value |
|---|---:|
| Artifact events | `192` |
| Single-frame events | `170` |
| Short bursts (2-5 frames) | `12` |
| Sustained events (>5 frames) | `10` |
| Frames with velocity candidate | `142` |
| Frames with acceleration candidate | `0` |
| Frames with **both** vel and accel | `0` |

See `tables/artifact_events.csv` for per-marker artifact events.

### Markers with gaps >=0.5 s (top rows)

| Marker (canonical) | Body region | Total gap (s) | Longest gap (s) |
|---|---|---:|---:|
| `RHandOut` | `wrist_hand` | `4.0167` | `2.8` |
| `RHandIn` | `wrist_hand` | `1.6167` | `1.0` |
| `ChestTop` | `torso_chest_back` | `4.3167` | `4.3167` |

---

---

## 8. Analysis windows (0.5 s)

- **0.5 s windows:** 528 total; 102 with gap overlap; 68 with artifact events; 106 with non-empty reason_codes.
- **1.0 s windows:** 264 total; 77 with gap overlap; 48 with artifact events; 77 with non-empty reason_codes.

---

## 9. Frame flag summary

| Reason code | Frames (analysis mask) |
|---|---:|
| `none` | 25226 |
| `ARTIFACT_EVENT_IN_WINDOW` | 2580 |
| `CRITICAL_GROUP_GAP` | 1800 |
| `SUSTAINED_ARTIFACT_IN_WINDOW` | 1500 |
| `GAP_OVERLAP` | 1260 |
| `LARGE_GAP` | 1194 |
| `LARGE_GAP_OVERLAP` | 1140 |
| `MODERATE_GAP` | 628 |

### Flagged intervals (labeled markers; see `qc_mask_intervals.csv`)

| Start | End | Duration | Body groups | Dominant gap marker | Reason |
|---:|---:|---:|---|---|---|
| 2148 | 2159 | 0.091667 | torso_chest_back | `T3_671:ChestTop` | Labeled gap >=0.5 s overlaps this interval; Gap in critical body region (torso/pelvis/head/legs) |
| 2160 | 2279 | 0.991667 | torso_chest_back | `T3_671:ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 2280 | 2519 | 1.991667 | torso_chest_back | `T3_671:ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 2520 | 2639 | 0.991667 | torso_chest_back | `T3_671:ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 2640 | 2665 | 0.208333 | torso_chest_back | `T3_671:ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 8100 | 8219 | 0.991667 | torso_chest_back | `nan` | Sustained artifact event (>5 frames) in window |
| 8880 | 8939 | 0.491667 | thigh_knee | `T3_671:LThighFront` | Gap in critical body region (torso/pelvis/head/legs) |
| 10620 | 10679 | 0.491667 | thigh_knee | `T3_671:LThighFront` | Gap in critical body region (torso/pelvis/head/legs) |
| 11700 | 11759 | 0.491667 | thigh_knee | `T3_671:LThighFront` | Gap in critical body region (torso/pelvis/head/legs) |
| 12240 | 12283 | 0.358333 | thigh_knee | `T3_671:LThighFront` | Gap in critical body region (torso/pelvis/head/legs) |
| 12284 | 12309 | 0.208333 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.2 s overlaps interval; Gap in critical body region (torso/pelvis/head/legs) |
| 12310 | 12359 | 0.408334 | thigh_knee | `T3_671:LThighFront` | Gap in critical body region (torso/pelvis/head/legs) |
| 12376 | 12409 | 0.275 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 12420 | 12479 | 0.491667 | thigh_knee | `T3_671:LThighFront` | Gap in critical body region (torso/pelvis/head/legs) |
| 12480 | 12481 | 0.008333 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 12482 | 12505 | 0.191666 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 15923 | 15959 | 0.3 | wrist_hand | `T3_671:RHandIn` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window |
| 15960 | 16019 | 0.491667 | wrist_hand | `T3_671:RHandIn` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window |
| 16020 | 16042 | 0.183333 | wrist_hand | `T3_671:RHandIn` | Labeled gap >=0.5 s overlaps this interval |
| 16620 | 16679 | 0.491667 | shoulder_upper_arm;torso_chest_back | `T3_671:RFArm` | One or more artifact events overlap analysis window |
| 16920 | 16979 | 0.491667 | wrist_hand | `nan` | One or more artifact events overlap analysis window |
| 17280 | 17285 | 0.041667 | shoulder_upper_arm | `nan` | Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 17286 | 17309 | 0.191667 | shoulder_upper_arm;torso_chest_back;wrist_hand | `T3_671:RFArm` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 17310 | 17339 | 0.241667 | shoulder_upper_arm;torso_chest_back;wrist_hand | `T3_671:LFArm` | Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 17340 | 17399 | 0.491667 | torso_chest_back | `nan` | One or more artifact events overlap analysis window |
| 17473 | 17519 | 0.383334 | shoulder_upper_arm;wrist_hand | `T3_671:LHandIn` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.5 s overlaps this analysis window |
| 17520 | 17528 | 0.066667 | wrist_hand | `T3_671:LHandIn` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.2 s overlaps analysis window |
| 17529 | 17579 | 0.416667 | shoulder_upper_arm;wrist_hand | `T3_671:RFArm` | Labeled gap >=0.2 s overlaps analysis window |
| 17580 | 17639 | 0.491667 | shoulder_upper_arm;wrist_hand | `T3_671:RFArm` | Sustained artifact event (>5 frames) in window |
| 17816 | 17819 | 0.025 | shoulder_upper_arm | `T3_671:RFArm` | Labeled gap >=0.2 s overlaps interval |

---

## 10. Reason code glossary

See `qc_reason_codes.md` in the run folder for full code definitions.

---

## Summary

Layer 1 recorded 192 artifact events and 5 labeled gaps >=0.5 s on 3 marker(s). Union frame mask: 3.769653% of frames have `flag_gap_0p5` (dominant marker `ChestTop`: 1.635411% of frames in its gaps). Use `layer1_marker_gap_evidence.csv`, `gaps_over_0p5s.csv`, `artifact_events.csv`, and `layer1_qc_handoff.csv` for downstream planning.


## Validation messages

- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
