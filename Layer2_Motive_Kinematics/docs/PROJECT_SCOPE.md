# Layer 2 Project Scope

## Active scope

Layer 2 converts Motive mixed CSV **global bone quaternions** into continuous filtered **parent-child relative rotation-vector features** for later Layer 3 analysis.

Pipeline stages **00–08** (see `02_LAYER2_STAGE_BY_STAGE_IMPLEMENTATION_SPEC.md`):

- CSV structure audit and joint mapping
- Quaternion component-order detection
- Frame/time validation
- Quaternion QC and global sign-continuity
- Relative quaternion computation, **relative sign-continuity**, reconstruction tests
- Log-map to rotation vectors
- Butterworth filtering in tangent space

## Out of scope

- Layer 1 raw marker QC code or outputs
- Layer 3 segmentation, PCA, JcvPCA, JRW, T1/T2/T3 comparison
- Claims of validated anatomical joint angles

## Independence

Layer 2 must not import Layer 1 code or require Layer 1 artifact flags.

## Outputs

Primary deliverables:

```text
outputs/08_filtering/relative_rotation_vectors_filtered.parquet
outputs/08_filtering/relative_rotation_vectors_filtered.csv
```

Full output contract: `03_OUTPUT_FOLDER_AND_REPORTING_CONTRACT.md`.

## Feature selection boundary

Layer 2 documents native skeleton structure and provisional joint maps in Stage 00–01.
The final analysis feature set is **not** decided in Stage 00–01. See
[`docs/FEATURE_SELECTION_BOUNDARY.md`](FEATURE_SELECTION_BOUNDARY.md).

## Implementation plan

See `.cursor/plans/layer_2_project_plan_61f0fbde.plan.md`.
