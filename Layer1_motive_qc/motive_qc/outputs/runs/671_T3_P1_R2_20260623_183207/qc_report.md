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
| Session ID | `T3_P1_R2` |
| Input file | `671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv` |
| Motive version | `Motive:Body 3.4.0.2` |
| Export type detected | `consistent_with_marker_xyz` |
| Frame rate | `120.0` Hz |
| Frame range | `0-31391` |
| Duration | `261.592` seconds |
| Units | `Meters` |
| Labeled markers | `54` |
| Unlabeled marker tracks | `61` |
| Parse validation | `pass` |

---

## 2. Per-marker gap evidence (≥0.5 s)

**Dominant gap marker:** `LThighFront` — `92.093527`% of session frames in that marker's gaps; `92.096474`% of session duration in gap.

| Marker (canonical) | Body region | Gaps ≥0.5 s | Total gap (s) | Longest gap (s) | % frames in gap | % session time in gap |
|---|---|---:|---:|---:|---:|---:|
| `LThighFront` | `thigh_knee` | `10` | `240.9167` | `103.3` | `92.093527` | `92.096474` |
| `ChestTop` | `torso_chest_back` | `2` | `5.5417` | `4.9417` | `2.118374` | `2.118454` |
| `LHandIn` | `wrist_hand` | `2` | `2.25` | `1.7` | `0.860092` | `0.860119` |
| `LHandOut` | `wrist_hand` | `2` | `1.45` | `0.7917` | `0.554281` | `0.554299` |
| `RFArm` | `shoulder_upper_arm` | `2` | `1.0333` | `0.525` | `0.395005` | `0.395005` |

See `tables/layer1_marker_gap_evidence.csv` for the full table.

---

## 3. Union frame mask (any marker can trigger a frame flag)

| Flag | % of frames |
|---|---:|
| `flag_gap_0p5` | `92.192278` |
| `flag_gap_0p2` | `2.471967` |
| `flag_artifact_sigma` | `0.525612` |
| `flag_segment_swap` | `1.860347` |
| Any flag | `92.549057` |
| Dominant interval criterion | `gaps_over_0p5` |

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
| Labeled marker missingness | `2.089771%` |
| Markers with any missing frames | `16` |
| Total continuous labeled-marker gaps | `114` |
| Gaps >=0.2 s | `43` |
| Gaps >=0.5 s | `18` |
| Longest labeled-marker gap | `103.3` s on `T3_671:LThighFront` |
| Markers with gap >=0.5 s | `T3_671:ChestTop;T3_671:LHandIn;T3_671:LHandOut;T3_671:LThighFront;T3_671:RFArm` |
| Critical body-region large gaps present | `yes` |

**Gap summary:** Longest labeled gap: T3_671:LThighFront (103.300s); 18 gaps >=0.5s across 5 marker(s).

See `tables/gaps_over_0p5s.csv` for per-marker gap intervals (includes `marker_name_canonical`).

---

## 6. Unlabeled-marker burden

| Metric | Value |
|---|---:|
| Frames with any unlabeled marker | `30797` |
| Percent frames with unlabeled markers | `98.104613%` |
| Max unlabeled markers in one frame | `4` |
| Longest unlabeled burst | `71.958333` s |

---

## 7. Candidate artifact screening (labeled markers only)

| Metric | Value |
|---|---:|
| Artifact events | `268` |
| Single-frame events | `187` |
| Short bursts (2-5 frames) | `52` |
| Sustained events (>5 frames) | `29` |
| Frames with velocity candidate | `165` |
| Frames with acceleration candidate | `0` |
| Frames with **both** vel and accel | `0` |

See `tables/artifact_events.csv` for per-marker artifact events.

### Markers with gaps >=0.5 s (top rows)

| Marker (canonical) | Body region | Total gap (s) | Longest gap (s) |
|---|---|---:|---:|
| `LThighFront` | `thigh_knee` | `240.9167` | `103.3` |
| `ChestTop` | `torso_chest_back` | `5.5417` | `4.9417` |
| `LHandIn` | `wrist_hand` | `2.25` | `1.7` |
| `LHandOut` | `wrist_hand` | `1.45` | `0.7917` |
| `RFArm` | `shoulder_upper_arm` | `1.0333` | `0.525` |

---

---

## 8. Analysis windows (0.5 s)

- **0.5 s windows:** 524 total; 488 with gap overlap; 97 with artifact events; 488 with non-empty reason_codes.
- **1.0 s windows:** 262 total; 246 with gap overlap; 63 with artifact events; 246 with non-empty reason_codes.

---

## 9. Frame flag summary

| Reason code | Frames (analysis mask) |
|---|---:|
| `CRITICAL_GROUP_GAP` | 29232 |
| `LARGE_GAP` | 28941 |
| `LARGE_GAP_OVERLAP` | 28680 |
| `ARTIFACT_EVENT_IN_WINDOW` | 3960 |
| `none` | 2160 |
| `SUSTAINED_ARTIFACT_IN_WINDOW` | 1860 |
| `GAP_OVERLAP` | 300 |
| `ELEVATED_MISSING` | 60 |
| `ELEVATED_MISSING_LABELED` | 5 |

### Flagged intervals (labeled markers; see `qc_mask_intervals.csv`)

| Start | End | Duration | Body groups | Dominant gap marker | Reason |
|---:|---:|---:|---|---|---|
| 0 | 1559 | 12.991667 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 1560 | 1576 | 0.133333 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Gap in critical body region (torso/pelvis/head/legs) |
| 1915 | 1919 | 0.033334 | torso_chest_back | `T3_671:ChestTop` | Labeled gap >=0.5 s overlaps this interval; Gap in critical body region (torso/pelvis/head/legs) |
| 1920 | 3359 | 11.991667 | thigh_knee;torso_chest_back;wrist_hand | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 3360 | 3370 | 0.083333 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Gap in critical body region (torso/pelvis/head/legs) |
| 5340 | 5340 | 0.0 |  | `nan` | Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 5341 | 5399 | 0.483334 | shoulder_upper_arm;thigh_knee;wrist_hand | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 5400 | 5459 | 0.491667 | shoulder_upper_arm;thigh_knee;wrist_hand | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 5460 | 7859 | 19.991667 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 7860 | 7900 | 0.333333 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 7961 | 7979 | 0.15 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Gap in critical body region (torso/pelvis/head/legs) |
| 7980 | 8039 | 0.491667 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 8040 | 8099 | 0.491667 | thigh_knee;wrist_hand | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 8100 | 8519 | 3.491667 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 8520 | 8639 | 0.991667 | thigh_knee;torso_chest_back | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 8640 | 15179 | 54.491667 | thigh_knee;wrist_hand | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 15180 | 15239 | 0.491667 | shoulder_upper_arm;thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 15240 | 15599 | 2.991667 | shoulder_upper_arm;thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 15600 | 15659 | 0.491667 | thigh_knee;wrist_hand | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 15660 | 15839 | 1.491667 | thigh_knee;wrist_hand | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 15840 | 16079 | 1.991667 | shoulder_upper_arm;thigh_knee;wrist_hand | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 16080 | 16199 | 0.991667 | shoulder_upper_arm;thigh_knee;wrist_hand | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 16200 | 16439 | 1.991667 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 16440 | 16499 | 0.491667 | shoulder_upper_arm;thigh_knee;torso_chest_back | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 16500 | 16559 | 0.491667 | shoulder_upper_arm;thigh_knee;wrist_hand | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 16560 | 16619 | 0.491667 | thigh_knee;wrist_hand | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 16620 | 16679 | 0.491667 | thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 16680 | 16799 | 0.991667 | shoulder_upper_arm;thigh_knee;torso_chest_back;wrist_hand | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 16800 | 16859 | 0.491667 | shoulder_upper_arm;thigh_knee;torso_chest_back | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 16860 | 17039 | 1.491667 | shoulder_upper_arm;thigh_knee | `T3_671:LThighFront` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |

---

## 10. Reason code glossary

See `qc_reason_codes.md` in the run folder for full code definitions.

---

## Summary

Layer 1 recorded 268 artifact events and 18 labeled gaps >=0.5 s on 5 marker(s). Union frame mask: 92.192278% of frames have `flag_gap_0p5` (dominant marker `LThighFront`: 92.093527% of frames in its gaps). Use `layer1_marker_gap_evidence.csv`, `gaps_over_0p5s.csv`, `artifact_events.csv`, and `layer1_qc_handoff.csv` for downstream planning.


## Validation messages

- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
