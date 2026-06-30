# GAGA Task Part 1 — Movement Groups, Exercises, and Timing

This document summarizes the proposed movement grouping for **GAGA Task Part 1**, based on the task transcript.  
The goal of this grouping is to create movement blocks that are long enough and biomechanically coherent enough for later analysis, including JcvPCA and estimation of natural variability.

---

## Recommended Grouping for Analysis

| Group | Group Name | Approx. Time Window | Approx. Duration | Exercises / Cues Included |
|---:|---|---:|---:|---|
| 1 | Trunk sagittal movement | 00:00:02.06–00:00:31.26 | ~29 s | Bend over as far as possible and roll up; look up and arch the spine |
| 2 | Upper-limb elevation and arm wave | 00:00:31.26–00:01:08.13 | ~37 s | Raise arms over head; stretch arms and yawn; create a wave across the arms from side to side; repeat to the other side |
| 3 | Axial rotation and reciprocal arm rotation | 00:01:08.13–00:01:52.11 | ~44 s | Look behind and twist the spine; return to center; repeat to the other side; arms out to the side; rotate one arm in and one out; switch |
| 4 | Curvilinear exploration | 00:01:52.11–00:02:53.15 | ~61 s | Draw curves with the hands; add curves with the elbows; add curves with the shoulders; add curves with the nose; use the whole body to draw curves |
| 5 | Single-leg balance with whole-body curves | 00:02:53.15–00:03:33.29 | ~40 s | Stand on one leg and draw curves with multiple body parts; stand on the other leg and draw curves with multiple body parts |
| 6 | Whole-body shaking / dance | 00:03:33.29–end of Part 1 | ≥12 s, depends on actual end time | Shake as many body parts as possible; keep shaking as you dance |

---

## Detailed Exercise-Level Segmentation

| Exercise No. | Transcript Time | Cue / Exercise | Proposed Group |
|---:|---:|---|---|
| 1 | 00:00:02.06 | Bend over as far as you can and then roll up | Group 1 — Trunk sagittal movement |
| 2 | 00:00:16.20 | Look up and arch your spine | Group 1 — Trunk sagittal movement |
| 3 | 00:00:31.26 | Raise your arms over your head. Stretch your arms and yawn | Group 2 — Upper-limb elevation and arm wave |
| 4 | 00:00:50.17 | Create a wave across your arms from side to side | Group 2 — Upper-limb elevation and arm wave |
| 5 | 00:00:58.14 | Other side | Group 2 — Upper-limb elevation and arm wave |
| 6 | 00:01:08.13 | Look behind you and twist your spine | Group 3 — Axial rotation and reciprocal arm rotation |
| 7 | 00:01:14.18 | Come back to the center. Repeat this on the other side. Put your arms out to the side. Rotate one in and one out | Group 3 — Axial rotation and reciprocal arm rotation |
| 8 | 00:01:40.23 | Switch | Group 3 — Axial rotation and reciprocal arm rotation |
| 9 | 00:01:52.11 | Draw curves with your hands | Group 4 — Curvilinear exploration |
| 10 | 00:02:02.26 | Add curves with your elbows | Group 4 — Curvilinear exploration |
| 11 | 00:02:14.05 | Add curves with your shoulders | Group 4 — Curvilinear exploration |
| 12 | 00:02:25.02 | Add curves with your nose | Group 4 — Curvilinear exploration |
| 13 | 00:02:34.09 | Now use your whole body including these body parts to draw curves | Group 4 — Curvilinear exploration |
| 14 | 00:02:53.15 | Stand on one leg and draw curves with multiple body parts | Group 5 — Single-leg balance with whole-body curves |
| 15 | 00:03:12.18 | Stand on the other leg and draw curves with multiple body parts | Group 5 — Single-leg balance with whole-body curves |
| 16 | 00:03:33.29 | Shake as many body parts as possible | Group 6 — Whole-body shaking / dance |
| 17 | 00:03:45.03 | Keep shaking as you dance | Group 6 — Whole-body shaking / dance |

---

## Notes for Implementation

### 1. Why use these grouped blocks?

Some individual cues are relatively short, especially the curve-related cues such as hands, elbows, shoulders, and nose.  
Analyzing each short cue separately may be unstable for PCA-based methods.  
Grouping related cues creates longer and more interpretable movement blocks.

### 2. Suggested minimum block duration

For JcvPCA-style analysis, it is preferable to use movement blocks of approximately **20–40 seconds or longer**, when possible.  
This is not a strict rule, but it helps ensure that each block contains enough movement variability for PCA.

### 3. Groups that are especially suitable

The following groups are relatively strong candidates for analysis:

- Group 1 — Trunk sagittal movement
- Group 3 — Axial rotation and reciprocal arm rotation
- Group 4 — Curvilinear exploration
- Group 5 — Single-leg balance with whole-body curves

### 4. Groups requiring caution

#### Group 2 — Upper-limb elevation and arm wave

This group is long enough, but it combines two related yet different movement types:

- arms overhead / stretch
- arm wave

It is acceptable as a combined block, but if very detailed interpretation is required, it may be useful to inspect the two parts separately.

#### Group 6 — Whole-body shaking / dance

This group depends on the actual end time of Task Part 1.  
If the shaking/dance section lasts only around 12–20 seconds, interpretation should be cautious.  
If it lasts around 30 seconds or more, it is more suitable as an independent block.

### 5. Natural variability estimation

For natural variability, compare the two repetitions of the same group within the same measurement point.

Example:

```text
T1, Group 4, repetition 1
vs.
T1, Group 4, repetition 2
```

This provides a within-measurement estimate of natural repetition-level variability for that group.

Then compare changes across measurement points:

```text
T1 Group 4 vs T2 Group 4
T1 Group 4 vs T3 Group 4
```

A change should be interpreted as more meaningful if it:

1. Exceeds the within-baseline repetition variability.
2. Appears in task-relevant PCs.
3. Shows a consistent direction across T2 and T3.
4. Appears across related movement groups or participants, if applicable.

---

## Compact Summary

| Group | Recommended Use |
|---:|---|
| 1 | Good independent block |
| 2 | Usable, but combines elevation and wave |
| 3 | Good independent block, but video verification of boundaries is recommended |
| 4 | Very good independent block |
| 5 | Very good independent block; can also inspect right/left leg separately |
| 6 | Usable only if the actual duration is long enough |
