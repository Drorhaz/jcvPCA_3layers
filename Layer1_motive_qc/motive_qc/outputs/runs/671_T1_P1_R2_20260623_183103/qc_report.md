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
| Session ID | `T1_P1_R2` |
| Input file | `671_T1_P1_R2_Take 2026-01-06 03.57.12 PM_003.csv` |
| Motive version | `Motive:Body 3.4.0.2` |
| Export type detected | `consistent_with_marker_xyz` |
| Frame rate | `120.0` Hz |
| Frame range | `0-30234` |
| Duration | `251.950` seconds |
| Units | `Meters` |
| Labeled markers | `54` |
| Unlabeled marker tracks | `33` |
| Parse validation | `pass` |

---

## 2. Per-marker gap evidence (≥0.5 s)

**Dominant gap marker:** `LShoulderTop` — `2.179593`% of session frames in that marker's gaps; `2.179679`% of session duration in gap.

| Marker (canonical) | Body region | Gaps ≥0.5 s | Total gap (s) | Longest gap (s) | % frames in gap | % session time in gap |
|---|---|---:|---:|---:|---:|---:|
| `LShoulderTop` | `shoulder_upper_arm` | `1` | `5.4917` | `5.4917` | `2.179593` | `2.179679` |
| `WaistLFront` | `pelvis_waist` | `1` | `4.625` | `4.625` | `1.835621` | `1.835682` |
| `ChestTop` | `torso_chest_back` | `1` | `4.325` | `4.325` | `1.716554` | `1.71661` |
| `LElbowOut` | `elbow_forearm` | `4` | `2.5083` | `0.75` | `0.995535` | `0.995555` |
| `LFArm` | `shoulder_upper_arm` | `2` | `2.0583` | `1.15` | `0.816934` | `0.816948` |
| `RFArm` | `shoulder_upper_arm` | `3` | `2.05` | `0.8167` | `0.813627` | `0.813654` |
| `RHandIn` | `wrist_hand` | `1` | `1.0417` | `1.0417` | `0.413428` | `0.413455` |

See `tables/layer1_marker_gap_evidence.csv` for the full table.

---

## 3. Union frame mask (any marker can trigger a frame flag)

| Flag | % of frames |
|---|---:|
| `flag_gap_0p5` | `7.061353` |
| `flag_gap_0p2` | `4.408798` |
| `flag_artifact_sigma` | `0.628411` |
| `flag_segment_swap` | `2.771622` |
| Any flag | `13.60344` |
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
| Labeled marker missingness | `0.357064%` |
| Markers with any missing frames | `23` |
| Total continuous labeled-marker gaps | `222` |
| Gaps >=0.2 s | `51` |
| Gaps >=0.5 s | `13` |
| Longest labeled-marker gap | `5.491667` s on `671:LShoulderTop` |
| Markers with gap >=0.5 s | `671:ChestTop;671:LElbowOut;671:LFArm;671:LShoulderTop;671:RFArm;671:RHandIn;671:WaistLFront` |
| Critical body-region large gaps present | `yes` |

**Gap summary:** Longest labeled gap: 671:LShoulderTop (5.492s); 13 gaps >=0.5s across 7 marker(s).

See `tables/gaps_over_0p5s.csv` for per-marker gap intervals (includes `marker_name_canonical`).

---

## 6. Unlabeled-marker burden

| Metric | Value |
|---|---:|
| Frames with any unlabeled marker | `827` |
| Percent frames with unlabeled markers | `2.735241%` |
| Max unlabeled markers in one frame | `2` |
| Longest unlabeled burst | `1.375` s |

---

## 7. Candidate artifact screening (labeled markers only)

| Metric | Value |
|---|---:|
| Artifact events | `266` |
| Single-frame events | `216` |
| Short bursts (2-5 frames) | `20` |
| Sustained events (>5 frames) | `30` |
| Frames with velocity candidate | `190` |
| Frames with acceleration candidate | `0` |
| Frames with **both** vel and accel | `0` |

See `tables/artifact_events.csv` for per-marker artifact events.

### Markers with gaps >=0.5 s (top rows)

| Marker (canonical) | Body region | Total gap (s) | Longest gap (s) |
|---|---|---:|---:|
| `LElbowOut` | `elbow_forearm` | `2.5083` | `0.75` |
| `RFArm` | `shoulder_upper_arm` | `2.05` | `0.8167` |
| `LFArm` | `shoulder_upper_arm` | `2.0583` | `1.15` |
| `LShoulderTop` | `shoulder_upper_arm` | `5.4917` | `5.4917` |
| `WaistLFront` | `pelvis_waist` | `4.625` | `4.625` |
| `ChestTop` | `torso_chest_back` | `4.325` | `4.325` |
| `RHandIn` | `wrist_hand` | `1.0417` | `1.0417` |

---

---

## 8. Analysis windows (0.5 s)

- **0.5 s windows:** 504 total; 150 with gap overlap; 107 with artifact events; 158 with non-empty reason_codes.
- **1.0 s windows:** 252 total; 97 with gap overlap; 75 with artifact events; 103 with non-empty reason_codes.

---

## 9. Frame flag summary

| Reason code | Frames (analysis mask) |
|---|---:|
| `none` | 20709 |
| `ARTIFACT_EVENT_IN_WINDOW` | 4200 |
| `CRITICAL_GROUP_GAP` | 2580 |
| `SUSTAINED_ARTIFACT_IN_WINDOW` | 2220 |
| `GAP_OVERLAP` | 2220 |
| `LARGE_GAP` | 2135 |
| `LARGE_GAP_OVERLAP` | 2040 |
| `MODERATE_GAP` | 1113 |
| `ELEVATED_MISSING` | 60 |
| `ELEVATED_MISSING_LABELED` | 7 |

### Flagged intervals (labeled markers; see `qc_mask_intervals.csv`)

| Start | End | Duration | Body groups | Dominant gap marker | Reason |
|---:|---:|---:|---|---|---|
| 952 | 959 | 0.058334 | pelvis_waist;torso_chest_back | `671:WaistLFront` | Labeled gap >=0.5 s overlaps this interval; Gap in critical body region (torso/pelvis/head/legs) |
| 960 | 1199 | 1.991667 | pelvis_waist;torso_chest_back | `671:WaistLFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 1200 | 1319 | 0.991667 | pelvis_waist;torso_chest_back;wrist_hand | `671:WaistLFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 1320 | 1499 | 1.491667 | pelvis_waist;torso_chest_back | `671:WaistLFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 1500 | 1508 | 0.066667 | pelvis_waist | `671:WaistLFront` | Labeled gap >=0.5 s overlaps this interval; Gap in critical body region (torso/pelvis/head/legs) |
| 4401 | 4425 | 0.2 | shoulder_upper_arm | `671:RFArm` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.2 s overlaps analysis window |
| 4440 | 4499 | 0.491667 | wrist_hand | `nan` | One or more artifact events overlap analysis window |
| 5018 | 5039 | 0.175 | shoulder_upper_arm | `671:LShoulderTop` | Labeled gap >=0.5 s overlaps this interval |
| 5040 | 5639 | 4.991667 | shoulder_upper_arm | `671:LShoulderTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window |
| 5640 | 5676 | 0.3 | shoulder_upper_arm | `671:LShoulderTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window |
| 6994 | 7017 | 0.191667 | wrist_hand | `671:RHandIn` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.2 s overlaps analysis window |
| 7018 | 7019 | 0.008334 | wrist_hand | `671:RHandIn` | Labeled gap >=0.2 s overlaps analysis window |
| 7560 | 7619 | 0.491667 | torso_chest_back | `nan` | Sustained artifact event (>5 frames) in window |
| 11963 | 11999 | 0.3 | wrist_hand | `671:RHandIn` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window |
| 12000 | 12059 | 0.491667 | wrist_hand | `671:RHandIn` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window |
| 12060 | 12087 | 0.225 | wrist_hand | `671:RHandIn` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window |
| 14161 | 14201 | 0.333334 | shoulder_upper_arm | `671:LFArm` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.2 s overlaps analysis window |
| 14220 | 14229 | 0.075 | wrist_hand | `671:RHandIn` | Labeled gap >=0.5 s overlaps this analysis window |
| 14230 | 14338 | 0.9 | shoulder_upper_arm;wrist_hand | `671:LFArm` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window |
| 14341 | 14365 | 0.2 | shoulder_upper_arm;torso_chest_back | `671:ChestLow` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 14366 | 14375 | 0.075 | shoulder_upper_arm | `671:LFArm` | Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 14376 | 14399 | 0.191667 | shoulder_upper_arm | `671:LFArm` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 14400 | 14459 | 0.491667 | shoulder_upper_arm | `671:LFArm` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window |
| 14460 | 14513 | 0.441667 | shoulder_upper_arm;wrist_hand | `671:LFArm` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; One or more artifact events overlap analysis window |
| 14514 | 14519 | 0.041667 |  | `nan` | Labeled gap >=0.2 s overlaps analysis window; One or more artifact events overlap analysis window |
| 14520 | 14540 | 0.166667 | torso_chest_back;wrist_hand | `671:ChestLow` | Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 14541 | 14562 | 0.175 | shoulder_upper_arm;torso_chest_back | `671:ChestLow` | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 14563 | 14579 | 0.133334 | shoulder_upper_arm;torso_chest_back | `671:RFArm` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 14580 | 14639 | 0.491667 | shoulder_upper_arm;torso_chest_back;wrist_hand | `671:RFArm` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 14640 | 14660 | 0.166667 | shoulder_upper_arm;torso_chest_back;wrist_hand | `671:RFArm` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |

---

## 10. Reason code glossary

See `qc_reason_codes.md` in the run folder for full code definitions.

---

## Summary

Layer 1 recorded 266 artifact events and 13 labeled gaps >=0.5 s on 7 marker(s). Union frame mask: 7.061353% of frames have `flag_gap_0p5` (dominant marker `LShoulderTop`: 2.179593% of frames in its gaps). Use `layer1_marker_gap_evidence.csv`, `gaps_over_0p5s.csv`, `artifact_events.csv`, and `layer1_qc_handoff.csv` for downstream planning.


## Validation messages

- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
