# Decision Log

Record explicit project decisions here. Do not hide decisions in code comments only.

| Date | ID | Decision | Rationale | Status |
|------|-----|----------|-----------|--------|
| 2026-06-19 | D001 | Keep repo name `Layer2_Motive_Kinematics` | User Milestone 0 decision | active |
| 2026-06-19 | D002 | Relative quaternion sign-continuity required in Stage 06 before log-map | User + MASTER_PLAN alignment | active |
| 2026-06-19 | D003 | Gap interpolation off by default | v5.1 addendum | active |
| 2026-06-19 | D004 | Defer numeric thresholds to config; mark VALIDATION_REQUIRED | User Milestone 0 decision | active |
| 2026-06-19 | D005 | Motive hip/top segment and virtual Root parent (see below) | Kinematics Reviewer Stage 00–01 sign-off; amended 2026-06-19 | active |
| 2026-06-19 | D006 | Hands / fingers / toes policy (see below) | Kinematics Reviewer Stage 00–01 sign-off | active |
| 2026-06-19 | D007 | Trunk / spine handling (see below) | Kinematics Reviewer Stage 00–01 sign-off | active |
| 2026-06-19 | D008 | Skeleton-version mismatch policy (see below) | Kinematics Reviewer Stage 00–01 sign-off; amended 2026-06-19 | active |
| 2026-06-19 | D009 | Provisional `selected_joint_map_v0` (see below) | Kinematics Reviewer Stage 00–01 sign-off | active |
| 2026-06-19 | D010 | Pre–Stage 07 kinematic gate (see below) | Kinematics Reviewer Stages 04–06 sign-off; amended 2026-06-19 | active |

---

## Motive hip/top segment and virtual Root parent (D005)

Scientist decision after Kinematics Reviewer Stage 00–01 review; amended after confirmed Motive skeleton templates:

- Interpret exported bones named `671` and `T3_671` as **asset-name-labeled Motive hip/top skeleton segments** when Motive **Asset Hip Name** naming is used — not arbitrary roots and **not** simply renamed to `Pelvis` in reports.
- Motive documentation treats the top skeleton/hip segment as the skeleton hip; exported naming may use the asset name (e.g. `671`, `T3_671`) rather than a generic pelvis label.
- The CSV **`Root`** parent is a **virtual parent without quaternion data**. Links `Root→671` and `Root→T3_671` are **non-computable** in Stage 06 and remain explicitly skipped.
- Links **`671→LThigh`**, **`671→RThigh`**, **`T3_671→LThigh`**, and **`T3_671→RThigh`** are **defensible Motive hip/top-segment-to-thigh links** and may remain **core candidates** in the pre–Stage 07 gate.
- Trunk/spine links above the hip/top segment (e.g. `671→Ab`, `Ab→Chest`) remain **review/provisional** — not final analysis features.

---

## Hands / fingers / toes (D006)

Scientist decision after Kinematics Reviewer Stage 00–01 review:

- Keep **`LHand`** and **`RHand`** in the provisional body set.
- Exclude **finger chains** from V0 provisional selected features.
- Exclude **toes** from V0 provisional selected features.
- Toes should remain documented as excluded/uncertain candidates, not silently removed.

---

## Trunk / spine handling (D007)

Scientist decision after Kinematics Reviewer Stage 00–01 review:

- Do **not** freeze trunk/spine feature selection during Stage 00–01.
- Report **native trunk chains per file**.
- Trunk/spine inclusion for final analysis is deferred until **after Layer 2 validation and before Layer 3**.
- Extra biomechanical spine/neck segments (e.g. T3 `Spine2`–`Spine4`, `Neck2`) must **not** be treated as automatically equivalent to older skeleton trunk joints.

---

## Skeleton-version mismatch (D008)

Scientist decision after Kinematics Reviewer Stage 00–01 review:

- Skeleton-version mismatch is allowed to be **documented in Layer 2**.
- Layer 2 may process each file in its **native skeleton structure**.
- Cross-timepoint Layer 3 comparison requires an approved **post–Layer-2 / pre–Layer-3 feature selection scope**.
- For mismatch subjects, a possible later scope is **`canonical_overlap_only`**, but this is **not decided or implemented** in Stage 00–01.

Confirmed template mismatch for subject 671 Part 1:

- **T1/T2:** Motive template **`Core + Passive Fingers (54)`** (51 bone rotation groups in export).
- **T3:** Motive template **`Biomech (57)`** (55 bone rotation groups in export).

The mismatch is **mainly trunk/spine/neck topology** (extra biomechanical spine/neck segments in Biomech). Per-file reports document native structure; no canonical alignment is performed in Layer 2 Stages 00–06. Final cross-template feature scope remains **post–Layer 2 / pre–Layer 3**.

---

## Provisional `selected_joint_map_v0` (D009)

Scientist decision after Kinematics Reviewer Stage 00–01 review:

- `selected_joint_map_v0.csv` is a **provisional preview only**.
- It is **not final**, **not frozen** (`frozen = false`), and **not Layer 3-ready**.
- `selected_body_bones.csv` is a **provisional convenience export** derived from the same heuristic preview; it is **not** the final body joint set.
- Final analysis feature selection must be **documented after Layer 2 validation and before Layer 3**.

See also: `docs/FEATURE_SELECTION_BOUNDARY.md`.

---

## Pre–Stage 07 kinematic gate (D010)

Scientist decision after Kinematics Reviewer Stages 04–06 review (“Acceptable with corrections”):

- Stages 04–06 are accepted as a **kinematic derivation gate** before rotation-vector conversion.
- **Stage 07 may proceed** only if **core candidate** links pass reconstruction and relative sign-continuity checks.
- Distal finger global/relative sign instability (R1-only) is **documented** and **does not block Stage 07** because finger links are excluded from the likely V0 analysis set.
- Missing/skipped Stage 06 links must be **listed explicitly** and must **not** affect required core candidates.
- **Hip/top-segment-to-thigh links** (`671→LThigh` / `671→RThigh`, `T3_671→LThigh` / `T3_671→RThigh`) may remain **core candidates** in the gate.
- **Trunk/spine links** remain **`review`/provisional** because **`Core + Passive Fingers (54)`** and **`Biomech (57)`** differ in trunk/spine/neck topology.
- Final analysis feature selection remains **deferred** until after Layer 2 validation and before Layer 3.

Gate artifacts:

- `outputs/stage06_pre_stage07_gate_report.md`
- `outputs/stage06_pre_stage07_core_link_gate.csv`
- `outputs/stage06_missing_skipped_links_summary.csv`
- `outputs/parent_child_mapping_trust_report.md`

`core_candidate` in the gate CSV is a **conservative pre–Stage 07 classification** (head/neck, shoulders, arms, hands, thighs, shins, feet, including defensible hip/top-segment-to-thigh links). It is **not** final Layer 3 feature selection. Trunk/spine links are **not** included as final analysis features.

---

## Template for new entries

```text
| YYYY-MM-DD | DNNN | Short decision | Why | active/superseded |
```
