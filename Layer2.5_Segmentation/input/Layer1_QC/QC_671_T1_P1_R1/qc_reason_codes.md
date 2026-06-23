# QC reason codes

| Code | Meaning | Typical action |
|---|---|---|
| `ARTIFACT_CANDIDATE` | Short kinematic outlier event in window | Visual review recommended |
| `ARTIFACT_EVENT_IN_WINDOW` | One or more artifact events overlap analysis window | Review event duration and body segment |
| `CRITICAL_GROUP_GAP` | Gap in critical body region (torso/pelvis/head/legs) | PCA-relevant caution |
| `ELEVATED_MISSING` | >10% labeled markers missing in window | Document elevated missingness |
| `ELEVATED_MISSING_LABELED` | Elevated labeled marker missingness at frame level | Check occlusion or marker dropout |
| `GAP_OVERLAP` | Labeled gap >=0.2 s overlaps analysis window | Caution for window-based analysis |
| `HIGH_MISSING` | >20% labeled markers missing in window | Tracking/occlusion check |
| `HIGH_MISSING_LABELED` | High labeled marker missingness at frame level | Priority review |
| `LARGE_GAP` | Labeled gap >=0.5 s overlaps this interval | Review before gap-fill; consider BVH exclusion |
| `LARGE_GAP_OVERLAP` | Labeled gap >=0.5 s overlaps this analysis window | Review before PCA/jPCA window selection |
| `MODERATE_GAP` | Labeled gap >=0.2 s overlaps interval | Document; check Motive gap-fill settings |
| `SEVERE_ARTIFACT_CANDIDATE` | Severe or sustained kinematic outlier | Priority visual review; may exclude |
| `SUSTAINED_ARTIFACT_IN_WINDOW` | Sustained artifact event (>5 frames) in window | Likely exclude for PCA/jPCA |
| `UNLABELED_PRESENT` | Unlabeled markers present (if flagged in config) | Tracking stability indicator only |
