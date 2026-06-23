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
| Session ID | `T2_P1_R1` |
| Input file | `671_T2_P1_R1_Take 2026-01-15 04.35.25 PM_005.csv` |
| Motive version | `Motive:Body 3.4.0.2` |
| Export type detected | `consistent_with_marker_xyz` |
| Frame rate | `120.0` Hz |
| Frame range | `0-30355` |
| Duration | `252.958` seconds |
| Units | `Meters` |
| Labeled markers | `54` |
| Unlabeled marker tracks | `15` |
| Parse validation | `pass` |

---

## 2. Per-marker gap evidence (≥0.5 s)

**Dominant gap marker:** `ChestTop` — `1.574648`% of session frames in that marker's gaps; `1.574686`% of session duration in gap.

| Marker (canonical) | Body region | Gaps ≥0.5 s | Total gap (s) | Longest gap (s) | % frames in gap | % session time in gap |
|---|---|---:|---:|---:|---:|---:|
| `ChestTop` | `torso_chest_back` | `1` | `3.9833` | `3.9833` | `1.574648` | `1.574686` |
| `ChestLow` | `torso_chest_back` | `1` | `0.55` | `0.55` | `0.21742` | `0.217427` |

See `tables/layer1_marker_gap_evidence.csv` for the full table.

---

## 3. Union frame mask (any marker can trigger a frame flag)

| Flag | % of frames |
|---|---:|
| `flag_gap_0p5` | `1.792067` |
| `flag_gap_0p2` | `0.329424` |
| `flag_artifact_sigma` | `0.52049` |
| `flag_segment_swap` | `2.002899` |
| Any flag | `4.717354` |
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
| Labeled marker missingness | `0.063895%` |
| Markers with any missing frames | `15` |
| Total continuous labeled-marker gaps | `72` |
| Gaps >=0.2 s | `5` |
| Gaps >=0.5 s | `2` |
| Longest labeled-marker gap | `3.983333` s on `671:ChestTop` |
| Markers with gap >=0.5 s | `671:ChestLow;671:ChestTop` |
| Critical body-region large gaps present | `yes` |

**Gap summary:** Longest labeled gap: 671:ChestTop (3.983s); 2 gaps >=0.5s across 2 marker(s).

See `tables/gaps_over_0p5s.csv` for per-marker gap intervals (includes `marker_name_canonical`).

---

## 6. Unlabeled-marker burden

| Metric | Value |
|---|---:|
| Frames with any unlabeled marker | `335` |
| Percent frames with unlabeled markers | `1.103571%` |
| Max unlabeled markers in one frame | `2` |
| Longest unlabeled burst | `0.95` s |

---

## 7. Candidate artifact screening (labeled markers only)

| Metric | Value |
|---|---:|
| Artifact events | `242` |
| Single-frame events | `183` |
| Short bursts (2-5 frames) | `39` |
| Sustained events (>5 frames) | `20` |
| Frames with velocity candidate | `158` |
| Frames with acceleration candidate | `0` |
| Frames with **both** vel and accel | `0` |

See `tables/artifact_events.csv` for per-marker artifact events.

### Markers with gaps >=0.5 s (top rows)

| Marker (canonical) | Body region | Total gap (s) | Longest gap (s) |
|---|---|---:|---:|
| `ChestTop` | `torso_chest_back` | `3.9833` | `3.9833` |
| `ChestLow` | `torso_chest_back` | `0.55` | `0.55` |

---

---

## 8. Analysis windows (0.5 s)

- **0.5 s windows:** 506 total; 61 with gap overlap; 88 with artifact events; 104 with non-empty reason_codes.
- **1.0 s windows:** 253 total; 50 with gap overlap; 63 with artifact events; 72 with non-empty reason_codes.

---

## 9. Frame flag summary

| Reason code | Frames (analysis mask) |
|---|---:|
| `none` | 24116 |
| `ARTIFACT_EVENT_IN_WINDOW` | 3600 |
| `SUSTAINED_ARTIFACT_IN_WINDOW` | 1680 |
| `CRITICAL_GROUP_GAP` | 1560 |
| `LARGE_GAP` | 544 |
| `LARGE_GAP_OVERLAP` | 420 |
| `GAP_OVERLAP` | 360 |
| `MODERATE_GAP` | 100 |

### Flagged intervals (labeled markers; see `qc_mask_intervals.csv`)

| Start | End | Duration | Body groups | Dominant gap marker | Reason |
|---:|---:|---:|---|---|---|
| 1058 | 1079 | 0.175 | torso_chest_back | `671:ChestTop` | Labeled gap >=0.5 s overlaps this interval; Gap in critical body region (torso/pelvis/head/legs) |
| 1080 | 1499 | 3.491667 | torso_chest_back | `671:ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 1500 | 1535 | 0.291667 | torso_chest_back | `671:ChestTop` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 2700 | 2759 | 0.491667 | shoulder_upper_arm | `nan` | One or more artifact events overlap analysis window |
| 5280 | 5339 | 0.491667 | pelvis_waist | `nan` | One or more artifact events overlap analysis window |
| 7080 | 7139 | 0.491667 | torso_chest_back | `nan` | One or more artifact events overlap analysis window |
| 7500 | 7559 | 0.491667 | torso_chest_back | `nan` | One or more artifact events overlap analysis window |
| 10500 | 10559 | 0.491667 | torso_chest_back | `nan` | Sustained artifact event (>5 frames) in window |
| 14280 | 14317 | 0.308333 | torso_chest_back | `671:ChestLow` | Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 14318 | 14383 | 0.541666 | torso_chest_back | `671:ChestLow` | Labeled gap >=0.5 s overlaps this interval; Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) |
| 14460 | 14519 | 0.491667 | torso_chest_back | `671:ChestLow` | Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 14700 | 14759 | 0.491667 | torso_chest_back;wrist_hand | `671:LHandIn` | Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 15000 | 15059 | 0.491667 | torso_chest_back | `671:ChestLow` | Gap in critical body region (torso/pelvis/head/legs) |
| 15600 | 15659 | 0.491667 | torso_chest_back;wrist_hand | `671:ChestLow` | Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 15660 | 15719 | 0.491667 | wrist_hand | `nan` | Sustained artifact event (>5 frames) in window |
| 15840 | 15899 | 0.491667 | torso_chest_back | `671:ChestLow` | Gap in critical body region (torso/pelvis/head/legs) |
| 15900 | 15959 | 0.491667 | torso_chest_back | `671:ChestLow` | Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 16020 | 16079 | 0.491667 | torso_chest_back | `nan` | One or more artifact events overlap analysis window |
| 16200 | 16259 | 0.491667 | torso_chest_back;wrist_hand | `671:LHandIn` | One or more artifact events overlap analysis window |
| 16380 | 16439 | 0.491667 | torso_chest_back;wrist_hand | `671:ChestLow` | Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |
| 17160 | 17219 | 0.491667 | torso_chest_back | `nan` | Sustained artifact event (>5 frames) in window |
| 17220 | 17279 | 0.491667 | torso_chest_back | `671:ChestTop` | Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window |
| 17640 | 17699 | 0.491667 | torso_chest_back | `nan` | One or more artifact events overlap analysis window |
| 17820 | 17879 | 0.491667 | torso_chest_back | `nan` | One or more artifact events overlap analysis window |
| 18000 | 18059 | 0.491667 | wrist_hand | `nan` | Sustained artifact event (>5 frames) in window |
| 18480 | 18599 | 0.991667 | torso_chest_back;wrist_hand | `671:LHandIn` | One or more artifact events overlap analysis window |
| 19440 | 19559 | 0.991667 | thigh_knee;wrist_hand | `671:RHandIn` | Sustained artifact event (>5 frames) in window |
| 19680 | 19739 | 0.491667 | torso_chest_back | `671:ChestLow` | Gap in critical body region (torso/pelvis/head/legs) |
| 19920 | 20039 | 0.991667 | head_neck;wrist_hand | `nan` | One or more artifact events overlap analysis window |
| 20220 | 20279 | 0.491667 | pelvis_waist | `671:WaistLFront` | Gap in critical body region (torso/pelvis/head/legs); One or more artifact events overlap analysis window |

---

## 10. Reason code glossary

See `qc_reason_codes.md` in the run folder for full code definitions.

---

## Summary

Layer 1 recorded 242 artifact events and 2 labeled gaps >=0.5 s on 2 marker(s). Union frame mask: 1.792067% of frames have `flag_gap_0p5` (dominant marker `ChestTop`: 1.574648% of frames in its gaps). Use `layer1_marker_gap_evidence.csv`, `gaps_over_0p5s.csv`, `artifact_events.csv`, and `layer1_qc_handoff.csv` for downstream planning.


## Validation messages

- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
