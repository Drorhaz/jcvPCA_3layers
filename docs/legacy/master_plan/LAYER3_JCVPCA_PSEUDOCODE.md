# Layer 3 JcvPCA Pseudocode — Clean Cursor-Safe Version

## Status and purpose

This document defines the intended Layer 3 implementation logic for the Gaga / OptiTrack / Motive JcvPCA pipeline.

Layer 3 compares changes in **parent-child relative rotation-vector contribution structure** across T1, T2, and T3, using T1 as the reference condition.

This document is intended for Cursor as implementation context. It must be read together with:

- the paper implementation script `S1_File.py`;
- the Layer 3 scope document;
- the master plan;
- the Cursor scope addendum;
- the Layer 2.5 exported JcvPCA-ready matrix and manifest.

The core JcvPCA implementation should remain close to the paper code in structure and logic, with only the minimum adaptations needed for full-body Motive-derived rotation-vector data.

---

## Non-negotiable V1 scope

Layer 3 V1 implements only:

```text
Group 4 cross-repetition JcvPCA
```

Primary analysis:

```text
A_T1  = T1_P1_R1_Group4 + T1_P1_R2_Group4
B_T2  = T2_P1_R1_Group4 + T2_P1_R2_Group4
B_T3  = T3_P1_R1_Group4 + T3_P1_R2_Group4
NV_T1 = T1_P1_R1_Group4 vs T1_P1_R2_Group4
```

Do not implement in V1:

- Group 5;
- task-level analysis;
- single-repetition analysis as a primary output;
- cross-subject analysis;
- JsvCRP;
- CRP;
- bootstrapping;
- statistical significance testing;
- automatic segmentation;
- automatic clean-window selection;
- Euler features;
- omega features;
- marker-position features;
- velocity features.

The broader analysis levels below are documented as future roadmap only.

---

## Scientific framing

Use this language:

```text
JcvPCA-style comparison of Motive-derived parent-child relative rotation-vector contribution structure.
```

Preferred terms:

- parent-child relative rotation contribution;
- joint-link contribution;
- rotation-vector feature contribution;
- increased contribution in B relative to A;
- decreased contribution in B relative to A;
- beyond available T1 repetition-level variability;
- within available T1 repetition-level variability / inconclusive.

Avoid:

- direct anatomical joint loading;
- muscle use;
- direct encoder measurement;
- synchronization change;
- statistically significant;
- proved change;
- no change.

Important caveat:

```text
JcvPCA measures differences in feature contribution structure. It does not measure temporal synchronization. JsvCRP/CRP is out of scope for V1.
```

---

## Session structure

Timepoints:

```text
T1, T2, T3
```

At each timepoint, Part 1 is repeated twice:

```text
P1_R1
P1_R2
```

Movement groups in Part 1:

```text
Group 1 = trunk sagittal movement
Group 2 = upper-limb elevation and arm wave
Group 3 = axial rotation and reciprocal arm rotation
Group 4 = curvilinear exploration
Group 5 = single-leg balance with whole-body curves
Group 6 = whole-body shaking / dance
```

V1 primary focus:

```text
Group 4 — curvilinear exploration
```

Reason:

```text
Group 4 is long, coherent, whole-body, and Gaga-relevant. It is the safest first-pass analysis unit.
```

Group 5 is a later extension, not part of V1.

---

## Layer 3 input contract

Layer 3 consumes Layer 2.5 exported JcvPCA-ready window matrices.

Required metadata columns:

```text
session_id
run_label
frame
time_sec
```

Required feature columns:

```text
numeric columns ending in _rx, _ry, _rz
```

Only `_rx`, `_ry`, and `_rz` feature columns enter PCA.

Metadata columns must never enter PCA.

Example feature triplet:

```text
J004_Neck_to_Head_rx
J004_Neck_to_Head_ry
J004_Neck_to_Head_rz
```

Layer 3 must validate:

- all required metadata columns exist;
- feature columns exist;
- all feature columns are numeric;
- no NaNs;
- no infinite values;
- no constant feature columns;
- feature names are identical across A and B;
- feature order is identical across A and B;
- every joint-link unit has a complete rx/ry/rz triplet;
- there are enough rows for PCA;
- selected number of PCs is valid.

If validation fails:

```text
STOP.
Write a validation report.
Do not fill, interpolate, drop frames, replace with zero, or silently repair data.
```

---

## Feature names and joint-link map

`feature_names`:

```text
Ordered list of _rx/_ry/_rz feature columns used in PCA.
```

The order must come from the validated input schema or manifest.

`joint_link_map`:

```text
Mapping from each parent-child link stem to its three axis features.
```

Example:

```text
J004_Neck_to_Head:
  - J004_Neck_to_Head_rx
  - J004_Neck_to_Head_ry
  - J004_Neck_to_Head_rz
```

Use the term `joint-link` or `link`, not pure anatomical joint, because the features are parent-child relative rotations.

---

## Analysis manifest

Layer 3 should use an analysis manifest CSV to identify which matrix belongs to which role.

Required columns:

```text
subject_id
timepoint
part_id
repetition_id
group_id
matrix_path
include_in_analysis
analysis_role
```

For V1, valid roles are:

```text
A_T1_R1
A_T1_R2
B_T2_R1
B_T2_R2
B_T3_R1
B_T3_R2
```

The runner builds:

```text
A_T1  = A_T1_R1 + A_T1_R2
B_T2  = B_T2_R1 + B_T2_R2
B_T3  = B_T3_R1 + B_T3_R2
NV_T1 = A_T1_R1 vs A_T1_R2
```

Concatenation means row-wise concatenation of matrices after schema validation.

---

## Future analysis levels — roadmap only, not V1

Layer 3 may later support four analysis levels:

1. single-task, single-repetition;
2. group-level, single-repetition;
3. single-task, cross-repetition;
4. group-level, cross-repetition.

For V1, implement only:

```text
group-level, cross-repetition, Group 4
```

Do not implement these future levels unless explicitly instructed later.

---

## Natural variability design

Natural variability is estimated from T1 only.

For V1 Group 4:

```text
A_var = T1_P1_R1_Group4
B_var = T1_P1_R2_Group4
NV_T1 = Compute_JcvPCA(A_var, B_var)
```

This is a repetition-level baseline difference.

It is useful for interpretation, but it is not a statistical distribution.

Report:

```text
observed change exceeds the available T1 repetition-level variability
```

Do not report:

```text
statistically significant
```

If more repetitions/windows are later available, bootstrapping may be added in a future version. Do not implement bootstrapping in V1.

---

## Core JcvPCA function

Function signature recommendation:

```python
def compute_jcvpca(
    A_data: pd.DataFrame,
    B_data: pd.DataFrame,
    feature_names: list[str],
    variance_threshold: float = 0.90,
    selected_m: int | None = None,
) -> dict:
    ...
```

The implementation should preserve the paper-code structure as closely as possible.

Use:

```python
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
```

Do not copy:

- simulated sine-wave data generation;
- plotting code;
- `%matplotlib tk`;
- CRP/JsvCRP code;
- shapely Polygon logic;
- hardcoded two-joint examples;
- hardcoded `n_components=2`.

---

## Step 1: validate inputs

Before PCA, check:

```text
A_data and B_data contain the same feature_names.
feature_names are in the same order.
feature columns are numeric.
feature columns contain no NaNs.
feature columns contain no infinite values.
feature columns are not constant.
features are filtered parent-child relative rotation-vector components.
no raw marker columns enter PCA.
no raw quaternion columns enter PCA.
no metadata columns enter PCA.
```

If invalid, stop and write validation report.

---

## Step 2: center each dataset independently

Correct:

```python
A_mean = A_data[feature_names].mean(axis=0)
B_mean = B_data[feature_names].mean(axis=0)

A_centered = A_data[feature_names] - A_mean
B_centered = B_data[feature_names] - B_mean
```

Each feature column is centered independently.

Do not center rx/ry/rz as a group.

Do not compute one mean per joint-link.

Do not use A's mean to center B.

Incorrect:

```python
B_centered = B_data[feature_names] - A_mean
```

Do not use:

```python
PCA_A.transform(B_raw)
```

because it applies A's fitted mean to B.

---

## Step 3: fit PCA on reference A

If `selected_m` is not provided, select it from A only.

First fit PCA on all valid components to compute cumulative explained variance.

Then:

```text
selected_m = smallest number of PCs where cumulative explained variance >= variance_threshold
```

Recommended V1 threshold:

```text
0.90
```

Then fit:

```python
pca_A = PCA(n_components=selected_m)
pca_A.fit(A_centered)

pca_A_frame = pca_A.components_
pca_A_variance_ratio = pca_A.explained_variance_ratio_
```

PC selection must be based on A only.

Do not choose selected_m from B, T2, or T3.

---

## Step 4: project B into A PCA space

Use manual matrix multiplication:

```python
B_scores_in_A_space = np.matmul(
    B_centered.to_numpy(),
    pca_A_frame.transpose()
)
```

Meaning:

```text
B is represented in A's PCA coordinate frame.
```

---

## Step 5: recompute PCA on projected B

```python
pca_B = PCA(n_components=selected_m)
pca_B.fit(B_scores_in_A_space)

pca_B_frame = pca_B.components_
pca_B_variance_ratio = pca_B.explained_variance_ratio_
```

This matches the paper implementation logic.

---

## Step 6: express B loadings back in original feature space

```python
B_reprojected_loadings = np.matmul(pca_B_frame, pca_A_frame)
```

Then:

```python
B_abs_loadings = np.abs(B_reprojected_loadings)
A_abs_loadings = np.abs(pca_A_frame)
```

`B_abs_loadings` are the B feature contribution weights expressed back in the original feature space.

---

## Step 7: compute axis-level JcvPCA

```python
JcvPCA_axis = B_abs_loadings - A_abs_loadings
```

Sign convention:

```text
positive = feature contributes more in B than A
negative = feature contributes less in B than A
```

This follows the paper implementation and the paper's verbal interpretation.

---

## Step 8: compute joint-link RSS aggregation

This is the corrected rule.

Do not use simple sum of absolute rx/ry/rz.

For each joint-link and each PC:

```python
JRW_A_link = sqrt(A_rx_abs^2 + A_ry_abs^2 + A_rz_abs^2)
JRW_B_link = sqrt(B_rx_abs^2 + B_ry_abs^2 + B_rz_abs^2)

JcvPCA_link = JRW_B_link - JRW_A_link
```

Equivalent implementation:

```python
JRW_A_link = np.sqrt(np.sum(A_abs_loadings[pc, axis_indices] ** 2))
JRW_B_link = np.sqrt(np.sum(B_abs_loadings[pc, axis_indices] ** 2))
JcvPCA_link = JRW_B_link - JRW_A_link
```

Reason:

```text
The paper uses scalar joint variables. This project uses 3D rotation-vector triplets for each parent-child link. RSS is the conservative adaptation for grouping rx/ry/rz into one joint-link magnitude.
```

---

## Step 9: optional variance weighting

Variance-weighted outputs may be exported, but they are secondary.

For each selected PC:

```python
Weighted_JcvPCA_axis = JcvPCA_axis * pca_A_variance_ratio[pc]
Weighted_JcvPCA_link = JcvPCA_link * pca_A_variance_ratio[pc]
```

Do not use B variance to weight the main outputs.

---

## PCA stability check — diagnostic only

A future diagnostic may compare PCA from:

```text
T1_R1
T1_R2
T1_R1 + T1_R2
```

Check:

- explained variance similarity;
- loading similarity;
- dominant PC consistency.

Output status:

```text
stable
warning_unstable
insufficient_data_for_stability_test
```

For V1, this is diagnostic/reporting only. It should not stop the analysis unless basic input validation fails.

Do not implement bootstrapping in V1 unless explicitly requested.

---

## V1 run plan

For Group 4 only:

```text
A_T1 = concatenate(A_T1_R1, A_T1_R2)
B_T2 = concatenate(B_T2_R1, B_T2_R2)
B_T3 = concatenate(B_T3_R1, B_T3_R2)
NV_T1 = A_T1_R1 vs A_T1_R2
```

Run:

```text
compute_jcvpca(A_T1, B_T2)
compute_jcvpca(A_T1, B_T3)
compute_jcvpca(A_T1_R1, A_T1_R2)
```

The third comparison is the natural variability comparison.

---

## Output tables

Export to:

```text
outputs/layer3_jcvpca/
```

Required outputs:

```text
validation_report.json
analysis_metadata.json
explained_variance.csv
jrw_axis.csv
jcvpca_axis.csv
jrw_link.csv
jcvpca_link.csv
natural_variability_t1.csv
interpretation_summary.md
```

Axis-level output columns:

```text
comparison
pc
feature
loading_A_abs
loading_B_reprojected_abs
jcvpca_axis
explained_variance_A
explained_variance_B_projected
```

Link-level output columns:

```text
comparison
pc
link_id
JRW_A_link
JRW_B_link
JcvPCA_link
explained_variance_A
```

Metadata should include:

```text
subject_id
reference_timepoint = T1
comparison_timepoints = T2, T3
part_id = P1
group_id = Group4
analysis_level = group_cross_repetition
repetitions_used
feature_scope = whole_body
feature_names
joint_link_map
selected_m
variance_threshold
centering_rule = center each dataset independently
normalization_rule = no z-score, no range-normalization
sign_convention = JcvPCA = abs(B_reprojected) - abs(A)
joint_link_aggregation = RSS over rx/ry/rz
natural_variability_rule = T1 repetition-level variability: R1 vs R2
timing_caveat = JcvPCA does not measure synchronization
```

---

## Interpretation language

Use:

```text
increased beyond available T1 repetition-level variability
decreased beyond available T1 repetition-level variability
within available T1 repetition-level variability / inconclusive
consistent across T2 and T3
```

Avoid:

```text
statistically significant
proved change
no change
synchronization change
```

Recommended first claim structure:

```text
For Group 4, T1 was used as the reference condition. T2 and T3 were compared against T1 using whole-body parent-child relative rotation-vector features. The observed JcvPCA changes were interpreted against available T1 repetition-level variability estimated from T1_P1_R1_Group4 versus T1_P1_R2_Group4.
```

---

## Cursor implementation instruction

When Cursor reads this document:

1. treat this as the cleaned Layer 3 pseudocode;
2. use the paper script as the computational reference;
3. use the HTML implementation plan for detailed movement-group context;
4. ignore any older version that uses simple sum across rx/ry/rz;
5. implement only V1 Group 4 cross-repetition unless explicitly instructed otherwise.
