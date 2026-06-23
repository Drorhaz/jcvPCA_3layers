# Raw Motive Marker QC Report

## Layer guide

- **Layer 2:** per-marker gaps and missingness (evidence).
- **Layer 4:** kinematic artifact **events** on gap-safe segments (candidates only).
- **Layer 3:** fixed 0.5 s windows — final **safe for PCA/jPCA?** verdict using L2 + L4.

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
| Overall QC status | `caution` |

---

## 2. Marker completeness and gap structure

| Metric | Value |
|---|---:|
| Labeled marker missingness | `0.304154%` |
| Markers with any missing frames | `20` |
| Total continuous labeled-marker gaps | `279` |
| Gaps >=0.2 s | `47` |
| Gaps >=0.5 s | `11` |
| Longest labeled-marker gap | `3.25` s |
| Critical body-region large gaps | `yes` |

**Key finding:** Review before preprocessing: 2 marker(s) with sustained dropout.

---

## 3. Unlabeled-marker burden

| Metric | Value |
|---|---:|
| Frames with any unlabeled marker | `719` |
| Percent frames with unlabeled markers | `2.349366%` |
| Max unlabeled markers in one frame | `3` |
| Longest unlabeled burst | `0.825` s |

---

## 4. Candidate artifact screening (labeled markers only)

| Metric | Value |
|---|---:|
| Artifact events | `272` |
| Single-frame events | `216` |
| Short bursts (2-5 frames) | `24` |
| Sustained events (>5 frames) | `32` |
| Frames with velocity candidate | `188` |
| Frames with acceleration candidate | `0` |
| Frames with **both** vel and accel | `0` |

**Interpretation:** Most detections are single-frame spikes; review sustained events and critical-region overlaps first.

---

## 5. Analysis window safety (0.5 s)

- **0.5 s windows:** 511 total; 154 with gap overlap; 143 with artifact events; 92 caution, 77 exclude.
- **1.0 s windows:** 256 total; 102 with gap overlap; 95 with artifact events; 55 caution, 56 exclude.

---

## 6. BVH analysis mask

| Status | Number of frames | Meaning |
|---|---:|---|
| use | 20297 | Merged L2+L3 frame mask |
| caution | 5369 | Merged L2+L3 frame mask |
| exclude_or_review | 4938 | Merged L2+L3 frame mask |

### Exclusion/caution intervals (labeled markers only; unlabeled excluded)

| Start | End | Duration | Status | Body groups | Reason | Action |
|---:|---:|---:|---|---|---|---|
| 1080 | 1610 | 4.416667 | exclude_or_review | pelvis_waist;torso_chest_back;wrist_hand | Sustained artifact event (>5 frames) in window | exclude_from_bvh_analysis |
| 5100 | 5939 | 6.991667 | exclude_or_review | shoulder_upper_arm;torso_chest_back | Sustained artifact event (>5 frames) in window | exclude_from_bvh_analysis |
| 5940 | 5999 | 0.491667 | caution | shoulder_upper_arm | One or more artifact events overlap analysis window | review |
| 7179 | 7212 | 0.275 | caution | wrist_hand | Labeled gap >=0.2 s overlaps interval | review |
| 7800 | 7859 | 0.491667 | exclude_or_review | wrist_hand | Sustained artifact event (>5 frames) in window | exclude_from_bvh_analysis |
| 11682 | 11715 | 0.275 | caution | wrist_hand | Labeled gap >=0.2 s overlaps interval | review |
| 12117 | 12599 | 4.016667 | exclude_or_review | torso_chest_back;wrist_hand | Labeled gap >=0.5 s overlaps this interval | exclude_from_bvh_analysis |
| 14280 | 14339 | 0.491667 | exclude_or_review | pelvis_waist;wrist_hand | Sustained artifact event (>5 frames) in window | exclude_from_bvh_analysis |
| 14340 | 14379 | 0.325 | caution | wrist_hand | Labeled gap >=0.2 s overlaps analysis window | review |
| 14380 | 14473 | 0.775 | exclude_or_review | shoulder_upper_arm;torso_chest_back;wrist_hand | Labeled gap >=0.5 s overlaps this interval | exclude_from_bvh_analysis |
| 14580 | 14639 | 0.491667 | caution | shoulder_upper_arm;wrist_hand | Labeled gap >=0.2 s overlaps analysis window | review |
| 14700 | 14819 | 0.991667 | caution | shoulder_upper_arm;wrist_hand | One or more artifact events overlap analysis window | review |
| 14940 | 15134 | 1.616667 | caution | shoulder_upper_arm;wrist_hand | Labeled gap >=0.2 s overlaps analysis window | review |
| 15180 | 15192 | 0.1 | caution | wrist_hand | Labeled gap >=0.2 s overlaps analysis window | review |
| 15193 | 15269 | 0.633334 | exclude_or_review | wrist_hand | Labeled gap >=0.5 s overlaps this interval | exclude_from_bvh_analysis |
| 15270 | 15419 | 1.241667 | caution | shoulder_upper_arm;torso_chest_back;wrist_hand | Labeled gap >=0.2 s overlaps analysis window | review |
| 15420 | 15479 | 0.491667 | exclude_or_review | shoulder_upper_arm;torso_chest_back;wrist_hand | Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) | exclude_from_bvh_analysis |
| 15480 | 15539 | 0.491667 | caution | torso_chest_back;wrist_hand | One or more artifact events overlap analysis window | review |
| 15540 | 15719 | 1.491667 | exclude_or_review | shoulder_upper_arm;torso_chest_back;wrist_hand | Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window | exclude_from_bvh_analysis |
| 15720 | 15779 | 0.491667 | caution | shoulder_upper_arm;torso_chest_back;wrist_hand | Labeled gap >=0.2 s overlaps interval | review |
| 15780 | 16019 | 1.991667 | exclude_or_review | elbow_forearm;shoulder_upper_arm;torso_chest_back;wrist_hand | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) | exclude_from_bvh_analysis |
| 16020 | 16139 | 0.991667 | caution | shoulder_upper_arm;torso_chest_back | Labeled gap >=0.2 s overlaps interval | review |
| 16140 | 16199 | 0.491667 | exclude_or_review | shoulder_upper_arm;torso_chest_back;wrist_hand | Labeled gap >=0.2 s overlaps interval; Labeled gap >=0.5 s overlaps this analysis window; Gap in critical body region (torso/pelvis/head/legs) | exclude_from_bvh_analysis |
| 16200 | 16259 | 0.491667 | caution | shoulder_upper_arm;torso_chest_back | Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs) | review |
| 16260 | 16379 | 0.991667 | exclude_or_review | shoulder_upper_arm;torso_chest_back;wrist_hand | Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window | exclude_from_bvh_analysis |
| 16380 | 16400 | 0.166667 | caution | wrist_hand | Labeled gap >=0.2 s overlaps analysis window | review |
| 16401 | 16473 | 0.6 | exclude_or_review | shoulder_upper_arm | Labeled gap >=0.5 s overlaps this interval | exclude_from_bvh_analysis |
| 16500 | 16679 | 1.491667 | exclude_or_review | elbow_forearm;shoulder_upper_arm;torso_chest_back;wrist_hand | Labeled gap >=0.2 s overlaps analysis window; Gap in critical body region (torso/pelvis/head/legs); Sustained artifact event (>5 frames) in window | exclude_from_bvh_analysis |
| 16680 | 16747 | 0.558333 | caution | shoulder_upper_arm;torso_chest_back | Labeled gap >=0.2 s overlaps interval | review |
| 16860 | 16919 | 0.491667 | caution | shoulder_upper_arm | One or more artifact events overlap analysis window | review |

---

## 7. Reason code glossary

See `qc_reason_codes.md` in the run folder for full code definitions.

---

## Final QC conclusion

Raw marker-level QC status is `caution`. Artifact screening found 272 events; 0 frames had both velocity and acceleration candidates. Use window quality tables and qc_intervals for PCA/jPCA planning.


## Validation messages

- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
- **[INFO] BODY_GROUPS_EXCLUDED_FROM_ANALYSIS:** Body groups excluded from QC calculations: fingers.
