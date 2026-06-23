# Feature Selection Boundary (Layer 2 vs Layer 3)

## Purpose

Layer 2 produces **native per-file kinematic features** and **transparent audit reports**.
It documents skeleton structure and candidate joints; it does **not** decide the final
analysis feature set used in Layer 3 JcvPCA.

## What Layer 2 does (Stages 00–08)

For each Motive mixed CSV, Layer 2:

1. Parses and documents native bone names, hierarchy, and quaternion columns.
2. Builds a full **candidate joint map** (all detectable parent-child pairs).
3. Applies **provisional** distal/finger/toe heuristics for reporting only.
4. Writes `selected_joint_map_v0.csv` with `frozen = false` and
   `selection_status = provisional_v0`.
5. After validation through Stage 08, emits filtered relative rotation-vector features
   for the joints processed in that file's pipeline run.

Layer 2 features are **valid in native file coordinates** — they reflect what Motive exported
for that capture, not a cross-subject canonical skeleton decision.

## What Layer 2 does not do (Stage 00–01)

Stage 00–01 must **not**:

- Freeze the final analysis joint set.
- Align skeletons across subjects or sessions.
- Resolve skeleton-version mismatch automatically.
- Choose a `canonical_overlap_only` feature scope.

Those decisions belong **after Layer 2 feature generation and validation, before Layer 3**.

## Provisional joint maps

`outputs/01_joint_mapping/selected_joint_map_v0.csv` is a **heuristic preview** only:

| Field | Meaning |
|-------|---------|
| `included_in_v0` | Provisional auto-include from config heuristics |
| `frozen` | Always `false` until an explicit human/config freeze step |
| `selection_status` | `provisional_v0` |

Default V0 heuristics (configurable, not final):

- **Hands:** included (`include_hand: true`)
- **Fingers:** excluded via keyword heuristics
- **Toes:** excluded by default (`include_toes: false`); flagged for review
- **Root/asset anchor:** reported as detected in CSV (not renamed to "Pelvis" unless present)
- **Motive hip/top segment:** exported asset-name-labeled hip/top bones (e.g. `671`, `T3_671`) documented per D005; not renamed to `Pelvis` unless that label appears in the export
- **Trunk candidates:** reported explicitly, not silently discarded

## Final analysis feature selection (pre–Layer 3)

After Layer 2 outputs are validated for each file/session, a separate documented step
(before Layer 3) selects which features enter comparison analysis. This step may:

- Accept the native per-file joint set for single-subject workflows.
- Restrict to a **canonical overlap feature set** when skeleton versions differ across
  compared datasets (`canonical_overlap_only` scope).
- Apply scientist-approved inclusion/exclusion overrides.

That step must be **documented** (decision log, manifest, or config freeze file). It is
**not** implemented inside Stage 00–01.

## Native Motive skeleton templates (671 Part 1)

Confirmed Motive skeleton templates for subject 671 Part 1:

| Sessions | Motive template | Observed rotation groups |
|----------|-------------------|--------------------------|
| T1, T2 | **Core + Passive Fingers (54)** | 51 |
| T3 | **Biomech (57)** | 55 |

Layer 2 **documents template identity per file** but does **not** harmonize skeletons or freeze the final analysis feature set. **`Core + Passive Fingers (54)`** and **`Biomech (57)`** differ mainly in **trunk/spine/neck topology** for this dataset (extra biomechanical spine/neck segments in Biomech).

Terminology for exported hip/top bones (D005):

- `671` and `T3_671` are reported as **asset-name-labeled Motive hip/top skeleton segments** when Asset Hip Name naming is used.
- Motive treats the top skeleton/hip segment as the skeleton hip; the export may use the asset name rather than a generic `Pelvis` label.
- Do **not** call these segments simply `Pelvis` in reports unless explaining that Motive documentation equates the hip/top segment with the skeleton hip and naming follows the asset.

**Pre–Stage 07 gate implications (provisional, not final features):**

- **Core candidates** may include defensible hip/top-segment-to-thigh links (`671→LThigh`, `671→RThigh`, `T3_671→LThigh`, `T3_671→RThigh`).
- **Trunk/spine links** (e.g. hip/top segment → abdomen/spine/chest) remain **review/provisional** and are **not** final analysis features until post–Layer 2 / pre–Layer 3 selection.
- Virtual CSV parent **`Root→671` / `Root→T3_671`** links remain skipped (no parent quaternion).

Final analysis feature selection across templates remains **deferred** until after Layer 2 validation and before Layer 3.

## Skeleton-version mismatch

When compared captures use different skeleton definitions (e.g. **Core + Passive Fingers (54)** vs **Biomech (57)**), Layer 2 still emits complete per-file reports. Document:

- Detected Motive hip/top segment per file (`671`, `T3_671`, etc.).
- Motive skeleton template name where known.
- Trunk chain or hierarchy summary per file.
- Candidate and uncertain joints per file.

Cross-file overlap analysis is deferred. A later pre–Layer 3 step may define
`canonical_overlap_only` features — identical `{joint}_rx`, `{joint}_ry`, `{joint}_rz`
names and column order across all files entering JcvPCA.

## Why Layer 3 requires identical feature names/order

Layer 3 JcvPCA compares feature matrices across conditions/sessions. Compared datasets
must share:

- Identical feature column names.
- Identical column order (manifest-driven).

Layer 2 per-file native outputs may differ in bone inventory until the pre–Layer 3
selection step harmonizes them.

## Structural XYZW population check (Stage 01)

Stage 01 may report a per-bone **structural population check** in
`rotation_population_report.csv`. This check is intentionally narrow.

**What it checks**

- Whether each Bone Rotation X/Y/Z/W column group has numeric values present row-by-row
  (complete raw XYZW frame count and percent).

**What it does not check**

- Quaternion norm QC (Stage 04).
- Component-order validation or SciPy compatibility (Stage 02).
- Sign-continuity (Stages 05 / 06).
- Gap detection or interpolation policy (Stage 04).

**Important**

- **Population pass does not imply quaternion validity.**
- A bone may show 100% structural population while still failing later norm, order, gap,
  or reconstruction checks.

## Related artifacts

| Stage / step | Artifact | Final? |
|--------------|----------|--------|
| Stage 01 | `candidate_joint_map.csv` | No — full inventory of pairs |
| Stage 01 | `selected_joint_map_v0.csv` | No — `frozen = false` |
| Stage 01 | `selected_body_bones.csv` | No — provisional preview subset only; not final body joint set |
| Stage 01 | `rotation_population_report.csv` | Report only — structural population; not quaternion QC |
| Stage 01 | `excluded_distal_bones.csv` | Report only |
| Post–Layer 2 validation | TBD manifest / config freeze | Yes — for Layer 3 |
| Layer 3 input | `layer3_feature_manifest.csv` | Yes — stable order |

See also: `docs/PROJECT_SCOPE.md`, `docs/VALIDATION_PROTOCOL.md`, `.cursor/plans/layer_2_project_plan_61f0fbde.plan.md`.
