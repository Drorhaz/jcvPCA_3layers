You are working in a repository for a three-layer Gaga/OptiTrack/Motive movement analysis pipeline. Your task is to build a detailed implementation plan for Layer 3 JcvPCA, but do not implement code yet.

Important: Layer 3 must be a conservative adaptation of the JcvPCA computational framework from the paper. The core implementation should remain very similar in structure and logic to the paper's Python script.

## Files and directories to inspect

Read these first:

* `Layer3_JcvPCA/references/S1_File.py`
* `Layer3_JcvPCA/references/JcvPCA_and_JsvCRP.pdf`
* `3_layers_Matser_plan_Full/MASTER_PLAN.md`
* `3_layers_Matser_plan_Full/MASTER_PLAN_V5_1_CURSOR_SCOPE_ADDENDUM.md`
* `3_layers_Matser_plan_Full/layer3 psuedocode.txt`
* `3_layers_Matser_plan_Full/jvcPCA_elborated_implmentationPlan_w_movementTaskGroups.html`
* `Layer3_JcvPCA/docs/LAYER3_SCOPE.md`

Also inspect these directories as read-only context:

* `Layer1_motive_qc/`
* `Layer2_Motive_Kinematics/`
* `Layer2.5_Segmentation/`

You may inspect Layer 1, Layer 2, and Layer 2.5 to understand outputs, schemas, manifests, and constraints. Do not modify them unless explicitly asked later.

Also inspect the sample Layer 2.5 output matrix:

* `outputs/pre_jvcpca_review/session_window/window_jvcpca_matrix.parquet`
* `outputs/pre_jvcpca_review/session_window/window_jvcpca_matrix_summary.md`
* `outputs/pre_jvcpca_review/session_window/window_export_manifest.json`

If these paths differ, search for the equivalent `window_jvcpca_matrix.parquet`, summary, and manifest.

## Scientific and computational requirements

The core JcvPCA function must intentionally preserve the structure and logic of the paper's S1 Python implementation.

Use:

```python
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
```

The central algorithm must follow this structure:

1. build or concatenate dataset A;
2. center A independently;
3. fit PCA on A;
4. build or concatenate dataset B;
5. center B independently;
6. manually project B into A PCA space using matrix multiplication;
7. fit PCA on projected B;
8. re-express B loadings in original feature space using `pca_B_frame @ pca_A_frame`;
9. compute JcvPCA as `abs(B_reprojected_loadings) - abs(A_loadings)`.

Do not replace this with a different PCA comparison method.

Do not use `PCA_A.transform(B_raw)` because it would apply A's mean to B. B must be centered independently and projected manually.

Do not z-score, variance-scale, or range-normalize features.

Do not implement CRP/JsvCRP in V1.

Do not copy the simulation, plotting, `%matplotlib tk`, random data generation, or shapely Polygon logic from the paper script.

## V1 scope

Layer 3 V1 should implement only Group 4 cross-repetition analysis:

```text
A_T1  = T1_P1_R1_Group4 + T1_P1_R2_Group4
B_T2  = T2_P1_R1_Group4 + T2_P1_R2_Group4
B_T3  = T3_P1_R1_Group4 + T3_P1_R2_Group4
NV_T1 = T1_P1_R1_Group4 vs T1_P1_R2_Group4
```

Do not implement Group 5, task-level analysis, cross-subject analysis, bootstrapping, statistics, JsvCRP, or automatic segmentation in V1.

## Input contract

Layer 3 consumes Layer 2.5 exported JcvPCA matrices.

Required metadata columns:

```text
session_id
run_label
frame
time_sec
```

Feature columns are numeric columns ending in:

```text
_rx
_ry
_rz
```

Only `_rx/_ry/_rz` columns enter PCA.

Layer 3 must validate:

* no NaNs;
* no infinite values;
* no constant feature columns;
* feature names identical across A and B;
* feature order identical across A and B;
* each joint-link unit has complete rx/ry/rz triplet;
* sufficient rows for selected PCA;
* selected number of PCs is valid.

If validation fails, Layer 3 must stop and write a clear validation report. It must not fill, interpolate, drop, or repair data.

## PC selection

For V1, choose:

```text
selected_m = smallest number of PCs from A reaching 90% cumulative explained variance
```

PC selection must be based on A only.

## Joint-link aggregation

Axis-level JcvPCA:

```python
JcvPCA_axis = abs(B_reprojected_loading) - abs(A_loading)
```

Joint-link aggregation must use RSS across rx/ry/rz:

```python
JRW_A_link = sqrt(A_rx^2 + A_ry^2 + A_rz^2)
JRW_B_link = sqrt(B_rx^2 + B_ry^2 + B_rz^2)
JcvPCA_link = JRW_B_link - JRW_A_link
```

Do not use simple sum of absolute rx/ry/rz.

## Required output from you now

Return a detailed implementation plan only. Do not write code yet.

Your plan should include:

1. A proposed Layer 3 directory structure.
2. The exact files you will create.
3. The exact files you will read but not modify.
4. The core functions and their signatures.
5. The validation rules.
6. The analysis manifest format.
7. The output files and schemas.
8. The tests you will write.
9. Any contradictions you found in the existing docs.
10. Any questions or decisions needed before implementation.

Keep the plan lean and direct. Do not over-engineer.

Implement Layer 3 JcvPCA according to the approved plan.

## Non-negotiable implementation principles

1. Keep Layer 3 separate from Layer 1, Layer 2, and Layer 2.5.
2. Do not modify Layer 1, Layer 2, or Layer 2.5 unless explicitly approved.
3. The core JcvPCA implementation must remain close to the paper's Python logic.
4. Use `numpy`, `pandas`, and `sklearn.decomposition.PCA`.
5. Do not use `PCA_A.transform(B_raw)`.
6. Do not z-score or variance-normalize.
7. Do not implement JsvCRP or CRP.
8. Do not implement automatic segmentation.
9. Do not silently repair NaNs, infs, or invalid matrices.
10. Keep code readable, simple, and auditable.

## Required package structure

Create:

```text
Layer3_JcvPCA/
├── README.md
├── pyproject.toml
├── config/
│   ├── layer3_analysis_manifest_template.csv
│   └── layer3_config.yaml
├── src/
│   └── layer3_jcvpca/
│       ├── __init__.py
│       ├── core.py
│       ├── io.py
│       ├── validation.py
│       ├── aggregation.py
│       ├── runner.py
│       └── reporting.py
├── scripts/
│   └── run_layer3_jcvpca.py
├── tests/
│   ├── test_core_matches_paper_logic.py
│   ├── test_input_validation.py
│   ├── test_feature_order.py
│   └── test_rss_aggregation.py
└── docs/
    ├── LAYER3_SCOPE.md
    └── METHOD_ADAPTATION_NOTES.md
```

## Core function

In `core.py`, implement a function similar to:

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

The function must follow the paper structure:

```python
dataset_A_centered = A_data[feature_names] - A_data[feature_names].mean()

pca_A = PCA(n_components=selected_m)
pca_A.fit(dataset_A_centered)

pca_A_frame = pca_A.components_
pca_A_variance_ratio = pca_A.explained_variance_ratio_

dataset_B_centered = B_data[feature_names] - B_data[feature_names].mean()

dataset_B_projected = np.matmul(
    dataset_B_centered.to_numpy(),
    pca_A_frame.transpose()
)

pca_B = PCA(n_components=selected_m)
pca_B.fit(dataset_B_projected)

pca_B_frame = pca_B.components_
pca_B_variance_ratio = pca_B.explained_variance_ratio_

result_B = np.abs(np.matmul(pca_B_frame, pca_A_frame))

sub = result_B - np.abs(pca_A_frame)
```

Adapt this only as needed for variable feature count and selected PCs.

## Input validation

Layer 3 must load matrices and validate:

* metadata columns exist;
* feature columns ending in `_rx`, `_ry`, `_rz` exist;
* only feature columns enter PCA;
* all feature columns are numeric;
* no NaNs;
* no infinite values;
* no constant feature columns;
* identical feature names and order across A/B matrices;
* complete rx/ry/rz triplets;
* enough frames for PCA;
* selected_m is valid.

If validation fails, raise a clear error and write a validation report.

Do not repair or alter invalid data.

## Analysis manifest

Implement support for a CSV manifest with columns:

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

For V1, support:

```text
analysis_role = A_T1_R1
analysis_role = A_T1_R2
analysis_role = B_T2_R1
analysis_role = B_T2_R2
analysis_role = B_T3_R1
analysis_role = B_T3_R2
```

The runner should build:

```text
A_T1  = A_T1_R1 + A_T1_R2
B_T2  = B_T2_R1 + B_T2_R2
B_T3  = B_T3_R1 + B_T3_R2
NV_T1 = A_T1_R1 vs A_T1_R2
```

## Outputs

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

## Axis-level outputs

For each comparison, selected PC, and feature:

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

## Link-level RSS outputs

Group features by removing the final `_rx`, `_ry`, `_rz` suffix.

For each comparison, selected PC, and link:

```text
comparison
pc
link_id
JRW_A_link
JRW_B_link
JcvPCA_link
```

Use:

```python
JRW_A_link = sqrt(rx_A^2 + ry_A^2 + rz_A^2)
JRW_B_link = sqrt(rx_B^2 + ry_B^2 + rz_B^2)
JcvPCA_link = JRW_B_link - JRW_A_link
```

## Natural variability

Compute T1 repetition-level natural variability:

```text
A = T1_R1
B = T1_R2
```

using the same `compute_jcvpca` function.

Do not call it statistical significance.

## Tests

Write tests for:

1. the core function follows paper logic on a small synthetic dataset;
2. B is centered independently, not with A mean;
3. feature order mismatch fails;
4. NaN/infinite values fail;
5. metadata columns are excluded from PCA;
6. incomplete rx/ry/rz triplets fail;
7. RSS aggregation works correctly;
8. selected_m is chosen from A explained variance only.

## Final behavior

After implementation, run tests and provide:

1. files created;
2. tests passed/failed;
3. any assumptions made;
4. any changes to scope;
5. exact command to run Layer 3.

Do not start implementation only after i review and approve the plan you'll build