# Pre–Stage 07 kinematic gate report

Batch gate summary for 671 Part 1 after Kinematics Reviewer acceptance of Stages 04–06 (documentation/validation corrections only).

**This gate classifies links for Stage 07 authorization; it does not freeze final Layer 3 analysis features.**

## Confirmed Motive skeleton templates (671 Part 1)

- **T1/T2:** `Core + Passive Fingers (54)`
- **T3:** `Biomech (57)`
- Templates differ mainly in **trunk/spine/neck topology**; final cross-template feature selection remains **post–Layer 2 / pre–Layer 3**.

## Motive hip/top segment terminology (D005)

- Exported bones `671` and `T3_671` are **asset-name-labeled Motive hip/top skeleton segments** when Asset Hip Name naming is used.
- Motive documents the top skeleton/hip segment as the skeleton hip; export naming may use the asset name — reports do **not** rename these to `Pelvis` unless that label appears in the CSV.
- **`Root→671` / `Root→T3_671`:** CSV virtual parent `Root` has no quaternion; skipped in Stage 06.
- **`671→LThigh` / `671→RThigh` / `T3_671→LThigh` / `T3_671→RThigh`:** defensible hip/top-segment-to-thigh links; remain **core candidates**.
- **Trunk/spine links** (e.g. hip/top segment → abdomen/chest) remain **review/provisional** — not final analysis features.

## Stage 04 — numeric quaternion QC

- `671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv`: **pass** (groups pass/warn/fail: 51/0/0, max norm error: 1.0139809858422666e-06)
- `671_T1_P1_R2_Take 2026-01-06 03.57.12 PM_003.csv`: **pass** (groups pass/warn/fail: 51/0/0, max norm error: 1.005063494874392e-06)
- `671_T2_P1_R1_Take 2026-01-15 04.35.25 PM_005.csv`: **pass** (groups pass/warn/fail: 51/0/0, max norm error: 1.0078664920420977e-06)
- `671_T2_P1_R2_Take 2026-01-15 04.35.25 PM_009.csv`: **pass** (groups pass/warn/fail: 51/0/0, max norm error: 9.996110001964098e-07)
- `671_T3_P1_R1_Take 2026-02-03 08.05.01 PM_000.csv`: **pass** (groups pass/warn/fail: 55/0/0, max norm error: 9.674900320888469e-07)
- `671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv`: **pass** (groups pass/warn/fail: 55/0/0, max norm error: 9.857445142369414e-07)
- **Batch Stage 04 pass:** True

## Stage 05 — global sign-continuity

- `671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv` (R1): post_correction_valid=True, total_sign_flips=57080, stage06_may_proceed=True
- `671_T1_P1_R2_Take 2026-01-06 03.57.12 PM_003.csv` (R2): post_correction_valid=True, total_sign_flips=0, stage06_may_proceed=True
- `671_T2_P1_R1_Take 2026-01-15 04.35.25 PM_005.csv` (R1): post_correction_valid=True, total_sign_flips=26098, stage06_may_proceed=True
- `671_T2_P1_R2_Take 2026-01-15 04.35.25 PM_009.csv` (R2): post_correction_valid=True, total_sign_flips=0, stage06_may_proceed=True
- `671_T3_P1_R1_Take 2026-02-03 08.05.01 PM_000.csv` (R1): post_correction_valid=True, total_sign_flips=23314, stage06_may_proceed=True
- `671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv` (R2): post_correction_valid=True, total_sign_flips=0, stage06_may_proceed=True
- **Batch Stage 05 pass:** True

## Stage 05 R1/R2 asymmetry disposition

- High Stage 05 global sign-flip counts occurred **only in R1 files** (T1/T2/T3 Part 1 R1); all R2 files showed **zero** global sign flips.
- Affected bones were **distal finger phalanges only** (e.g. LIndex3, RIndex2, RPinky3 per diagnostic); no trunk, head, hand, shoulder, thigh, shin, or foot bones showed raw global sign flips.
- No **core candidate** body links showed unresolved global sign discontinuities after Stage 05 correction.
- Accepted as likely quaternion representation / export / finger-track instability, with residual risk documented.
- **Does not block Stage 07** when excluded/distal links remain excluded and core candidate links pass reconstruction and relative sign-continuity checks.

## Stage 06 — relative quaternion formula

- Relative quaternion: `q_relative = inverse(q_parent_global) * q_child_global`
- SciPy: `Rotation.from_quat(parent).inv() * Rotation.from_quat(child)`
- Reconstruction: `q_child_reconstructed = q_parent_global * q_relative`

## Stage 06 — reconstruction validation

- Pass threshold: max angular error ≤ 1e-05°
- Warning threshold: max angular error ≤ 0.001°
- Fail threshold: max angular error > 0.001°

- **Achieved global max error (batch):** 4.21212e-14°
- `671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv`: links pass/warn/fail 50/0/0, max error 4.10814e-14°
- `671_T1_P1_R2_Take 2026-01-06 03.57.12 PM_003.csv`: links pass/warn/fail 50/0/0, max error 3.42863e-14°
- `671_T2_P1_R1_Take 2026-01-15 04.35.25 PM_005.csv`: links pass/warn/fail 50/0/0, max error 4.21212e-14°
- `671_T2_P1_R2_Take 2026-01-15 04.35.25 PM_009.csv`: links pass/warn/fail 50/0/0, max error 3.94391e-14°
- `671_T3_P1_R1_Take 2026-02-03 08.05.01 PM_000.csv`: links pass/warn/fail 54/0/0, max error 3.41933e-14°
- `671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv`: links pass/warn/fail 54/0/0, max error 3.79358e-14°
- **Batch Stage 06 reconstruction pass:** True

## Stage 06 — relative sign-continuity

- Method: consecutive dot-product test on relative quaternions; if `dot(q[t], q[t-1]) < 0`, multiply `q[t]` by −1 (documented second pass, same rule as Stage 05).
- Raw relative sign flips in R1 files were limited to **excluded finger phalanges**; all links reached `post_correction_valid=True` after correction.

- **Core candidate raw relative sign flips (sum):** 0
- **Core candidate unresolved sign discontinuities:** 0

## Missing / skipped Stage 06 links

- `671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv` J001 Root→671: CSV virtual parent `Root` has no global quaternion; `Root→671` is non-computable and skipped in Stage 06 (affects_core=False, blocks Stage 07=False)
- `671_T1_P1_R2_Take 2026-01-06 03.57.12 PM_003.csv` J001 Root→671: CSV virtual parent `Root` has no global quaternion; `Root→671` is non-computable and skipped in Stage 06 (affects_core=False, blocks Stage 07=False)
- `671_T2_P1_R1_Take 2026-01-15 04.35.25 PM_005.csv` J001 Root→671: CSV virtual parent `Root` has no global quaternion; `Root→671` is non-computable and skipped in Stage 06 (affects_core=False, blocks Stage 07=False)
- `671_T2_P1_R2_Take 2026-01-15 04.35.25 PM_009.csv` J001 Root→671: CSV virtual parent `Root` has no global quaternion; `Root→671` is non-computable and skipped in Stage 06 (affects_core=False, blocks Stage 07=False)
- `671_T3_P1_R1_Take 2026-02-03 08.05.01 PM_000.csv` J055 Root→T3_671: CSV virtual parent `Root` has no global quaternion; `Root→T3_671` is non-computable and skipped in Stage 06 (affects_core=False, blocks Stage 07=False)
- `671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv` J055 Root→T3_671: CSV virtual parent `Root` has no global quaternion; `Root→T3_671` is non-computable and skipped in Stage 06 (affects_core=False, blocks Stage 07=False)

## Core candidate gate summary

- **Core candidate links:** 96 rows across batch
- **core_pass:** 96
- **core fail:** 0
- **Excluded/distal links with raw relative sign flips:** 7 (documented; do not block Stage 07)

## Pre–Stage 07 checklist

- [ x] Stage 04 pass?
- [ x] Stage 05 pass?
- [ x] Stage 06 reconstruction pass?
- [ x] Any core candidate reconstruction failures?
- [ x] Any core candidate unresolved sign discontinuities?
- [ x] Any missing/skipped core links?
- [x] Are distal/finger/toe exclusions carried forward?
- [x] Are trunk/spine/manual-review links still marked provisional?
- [x] Are hip/top-segment-to-thigh links retained as core candidates?
- [x] Is final analysis feature selection still deferred until post–Layer 2 / pre–Layer 3?

## Stage 07 authorization

**Stage 07 may proceed** for 671 Part 1, subject to human review of this gate report and per-file Stage 06 outputs.

## Explicit limitations

- This report does not convert to rotation vectors, filter, or implement Layer 3.
- `core_candidate` is a conservative pre–Stage 07 gate only; not final feature selection.
- Trunk/spine topology differences (`Core + Passive Fingers (54)` vs `Biomech (57)`) remain provisional per D007/D008.
