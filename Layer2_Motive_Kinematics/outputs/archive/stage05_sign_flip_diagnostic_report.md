# Stage 05 sign-flip diagnostic report

Diagnostic review of global quaternion sign-flip patterns across six 671 Part 1 files.
Read-only analysis; Stage 05 outputs and algorithm are unchanged.

## Executive summary

- **Files reviewed:** 6
- **R1 total flips:** 106,492
- **R2 total flips:** 0
- **Asymmetry:** All sign flips occur on R1 captures; all R2 captures have zero flips.
- **Stage 05 status:** Post-correction validation passed on all files; algorithm behavior is standard.
- **Likely cause:** R1-specific raw quaternion sign discontinuities on a **small subset of finger bones**, starting **mid-capture** (~53–60% through recording), not whole-skeleton from frame 0. R2 captures have none. This pattern is inconsistent with global biological motion and most consistent with export/solver/track representation artifacts on distal finger chains.

## Total flips by file

| File | Take | Rep | Total flips | Bones w/ flips | % bones | Max bone rate | Status |
|------|------|-----|-------------|----------------|---------|---------------|--------|
| `671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001` | T1 | R1 | 57,080 | 4/51 (7.8%) | 46.6% | `review` |
| `671_T1_P1_R2_Take_2026-01-06_03.57.12_PM_003` | T1 | R2 | 0 | 0/51 (0.0%) | 0.0% | `expected` |
| `671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005` | T2 | R1 | 26,098 | 2/51 (3.9%) | 43.0% | `review` |
| `671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009` | T2 | R2 | 0 | 0/51 (0.0%) | 0.0% | `expected` |
| `671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000` | T3 | R1 | 23,314 | 3/55 (5.5%) | 40.3% | `review` |
| `671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005` | T3 | R2 | 0 | 0/55 (0.0%) | 0.0% | `expected` |

## Total flips by repetition

| Repetition | Files | Total flips | Mean flips/file |
|------------|-------|-------------|-----------------|
| R1 | 3 | 106,492 | 35,497 |
| R2 | 3 | 0 | 0 |

## `671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001` (T1 R1)

- **Total flips:** 57,080 / 30,604 frames
- **Bones with any flips:** 4 (7.8%)
- **First flip frame:** 16334 (53.4% into capture)
- **Last flip frame:** 30603
- **Combined flip pattern:** clustered
- **Top-3 bone share:** 75.0%
- **Top-10 bone share:** 100.0%
- **Diagnostic status:** `review`

### Top 10 bones by flip count

| Rank | Bone | Region | Flips | Flip rate |
|------|------|--------|-------|-----------|
| 1 | `LPinky3` | finger_distal | 14,270 | 46.6% |
| 2 | `LIndex3` | finger_distal | 14,270 | 46.6% |
| 3 | `LRing3` | finger_distal | 14,270 | 46.6% |
| 4 | `LMiddle3` | finger_distal | 14,270 | 46.6% |
| 5 | `671` | other | 0 | 0.0% |
| 6 | `RHand` | limb | 0 | 0.0% |
| 7 | `RIndex1` | finger_distal | 0 | 0.0% |
| 8 | `RIndex2` | finger_distal | 0 | 0.0% |
| 9 | `RIndex3` | finger_distal | 0 | 0.0% |
| 10 | `RMiddle1` | finger_distal | 0 | 0.0% |

### Flip concentration by body region

- **finger_distal:** 57,080 flips (100.0%)

### Near-alternating or high-rate bones (>45% flip rate or median gap 1–2)

- `LIndex3` (finger_distal): 14,270 flips, rate=46.6%, pattern=frequent_alternating
- `LMiddle3` (finger_distal): 14,270 flips, rate=46.6%, pattern=frequent_alternating
- `LPinky3` (finger_distal): 14,270 flips, rate=46.6%, pattern=frequent_alternating
- `LRing3` (finger_distal): 14,270 flips, rate=46.6%, pattern=frequent_alternating

## `671_T1_P1_R2_Take_2026-01-06_03.57.12_PM_003` (T1 R2)

- **Total flips:** 0 / 30,235 frames
- **Bones with any flips:** 0 (0.0%)
- **First flip frame:** None
- **Last flip frame:** None
- **Combined flip pattern:** none
- **Top-3 bone share:** 0.0%
- **Top-10 bone share:** 0.0%
- **Diagnostic status:** `expected`

*No raw sign discontinuities; Stage 05 was a no-op.*

## `671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005` (T2 R1)

- **Total flips:** 26,098 / 30,356 frames
- **Bones with any flips:** 2 (3.9%)
- **First flip frame:** 17307 (57.0% into capture)
- **Last flip frame:** 30355
- **Combined flip pattern:** clustered
- **Top-3 bone share:** 100.0%
- **Top-10 bone share:** 100.0%
- **Diagnostic status:** `review`

### Top 10 bones by flip count

| Rank | Bone | Region | Flips | Flip rate |
|------|------|--------|-------|-----------|
| 1 | `RIndex2` | finger_distal | 13,049 | 43.0% |
| 2 | `RIndex3` | finger_distal | 13,049 | 43.0% |
| 3 | `671` | other | 0 | 0.0% |
| 4 | `RPinky2` | finger_distal | 0 | 0.0% |
| 5 | `RFArm` | limb | 0 | 0.0% |
| 6 | `RFoot` | limb | 0 | 0.0% |
| 7 | `RHand` | limb | 0 | 0.0% |
| 8 | `RIndex1` | finger_distal | 0 | 0.0% |
| 9 | `RMiddle1` | finger_distal | 0 | 0.0% |
| 10 | `RMiddle2` | finger_distal | 0 | 0.0% |

### Flip concentration by body region

- **finger_distal:** 26,098 flips (100.0%)

### Near-alternating or high-rate bones (>45% flip rate or median gap 1–2)

- `RIndex2` (finger_distal): 13,049 flips, rate=43.0%, pattern=frequent_alternating
- `RIndex3` (finger_distal): 13,049 flips, rate=43.0%, pattern=frequent_alternating

## `671_T2_P1_R2_Take_2026-01-15_04.35.25_PM_009` (T2 R2)

- **Total flips:** 0 / 30,479 frames
- **Bones with any flips:** 0 (0.0%)
- **First flip frame:** None
- **Last flip frame:** None
- **Combined flip pattern:** none
- **Top-3 bone share:** 0.0%
- **Top-10 bone share:** 0.0%
- **Diagnostic status:** `expected`

*No raw sign discontinuities; Stage 05 was a no-op.*

## `671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000` (T3 R1)

- **Total flips:** 23,314 / 31,674 frames
- **Bones with any flips:** 3 (5.5%)
- **First flip frame:** 18914 (59.7% into capture)
- **Last flip frame:** 31673
- **Combined flip pattern:** frequent_alternating
- **Top-3 bone share:** 100.0%
- **Top-10 bone share:** 100.0%
- **Diagnostic status:** `review`

### Top 10 bones by flip count

| Rank | Bone | Region | Flips | Flip rate |
|------|------|--------|-------|-----------|
| 1 | `RPinky3` | finger_distal | 12,760 | 40.3% |
| 2 | `LIndex2` | finger_distal | 5,277 | 16.7% |
| 3 | `LIndex3` | finger_distal | 5,277 | 16.7% |
| 4 | `Ab` | root_anchor | 0 | 0.0% |
| 5 | `RRing3` | finger_distal | 0 | 0.0% |
| 6 | `RIndex1` | finger_distal | 0 | 0.0% |
| 7 | `RIndex2` | finger_distal | 0 | 0.0% |
| 8 | `RIndex3` | finger_distal | 0 | 0.0% |
| 9 | `RMiddle1` | finger_distal | 0 | 0.0% |
| 10 | `RMiddle2` | finger_distal | 0 | 0.0% |

### Flip concentration by body region

- **finger_distal:** 23,314 flips (100.0%)

### Near-alternating or high-rate bones (>45% flip rate or median gap 1–2)

- `RPinky3` (finger_distal): 12,760 flips, rate=40.3%, pattern=frequent_alternating

## `671_T3_P1_R2_Take_2026-02-03_08.05.01_PM_005` (T3 R2)

- **Total flips:** 0 / 31,392 frames
- **Bones with any flips:** 0 (0.0%)
- **First flip frame:** None
- **Last flip frame:** None
- **Combined flip pattern:** none
- **Top-3 bone share:** 0.0%
- **Top-10 bone share:** 0.0%
- **Diagnostic status:** `expected`

*No raw sign discontinuities; Stage 05 was a no-op.*

## Cross-file interpretation

### Is the R1-only pattern explainable?

Yes — **most plausibly as a Motive export / quaternion hemisphere or finger-track representation artifact on R1 captures**, not coordinated biomechanical sign reversals:

- Paired R1/R2 repetitions within the same take should not differ by all-or-nothing flip presence.
- R2 files show **zero** raw discontinuities across **all** bones (51 or 55 groups).
- R1 flips affect only **2–4 bones per file** (3.9–7.8% of groups); **100% of R1 flips are finger/distal**.
- First flip occurs **mid-capture** (frames 16334–18914, ~53–60% through), then continues with **near-alternating** sign changes (~40–47% of remaining frames) on affected phalanges only.
- Trunk/limb anchors (Ab, Chest, Thigh, Shin, Foot, Shoulder) show **zero** raw flips on all files.

### Concentration vs distribution

- `671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001`: **concentrated** (top-3 share 75.0%).
- `671_T2_P1_R1_Take_2026-01-15_04.35.25_PM_005`: **concentrated** (top-3 share 100.0%).
- `671_T3_P1_R1_Take_2026-02-03_08.05.01_PM_000`: **concentrated** (top-3 share 100.0%).

### High-flip bone anatomy

Max-flip bones on R1 files are predominantly **finger/distal phalanges** (Index/Middle/Ring/Thumb chains), which are already provisional distal exclusions for Layer 3.
Trunk anchors (Ab, Chest, Spine, Head) and major limb segments (Thigh, Shin) are **not** the dominant max-flip bones in this batch.

## Recommendations

| Question | Answer |
|----------|--------|
| Is Stage 05 still acceptable? | **Yes** — standard algorithm; post-correction validation passed. |
| Is Stage 06 allowed? | **Yes, with documentation** — proceed; monitor Stage 06/07 on R1 high-flip fingers. |
| Exclude bones from final analysis? | **No mandatory exclusion** from Stage 05 alone; fingers already heuristic exclusions. |
| Follow-up | Optional: compare raw q·q signs between R1 and R2 frame 0 for same take. |

## Limitations

- Diagnostic only; no Stage 05 re-run or algorithm change.
- Body-region labels are heuristic keyword matches on canonical bone names.
- Does not validate relative rotations or anatomical correctness.
