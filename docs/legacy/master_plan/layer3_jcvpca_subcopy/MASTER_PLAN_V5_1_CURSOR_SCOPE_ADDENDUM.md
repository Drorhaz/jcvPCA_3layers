# MASTER_PLAN_V5_1_CURSOR_SCOPE_ADDENDUM

## Purpose of This Addendum

This addendum clarifies how Cursor / Composer should interpret the broader three-layer master plan when preparing and implementing the Layer 2 project.

The master plan should be treated as a **scope, boundary, and architecture document**. It is not the final implementation authority for every algorithmic detail.

For the current development phase, the active implementation target is:

```text
Layer 2 — Solved Skeleton Kinematics
```

Layer 2 should be prepared and implemented as an independent project for now.

---

## 1. How Cursor Should Read the Master Plan

Cursor should use `MASTER_PLAN.md` mainly to understand:

```text
1. The overall three-layer architecture.
2. The separation between Layer 1, Layer 2, and Layer 3.
3. The input/output contract between layers.
4. The conservative scientific framing of the method.
5. The implementation order and STOP-checkpoint philosophy.
```

Cursor should **not** use the master plan as permission to implement all layers at once.

During the current phase, Cursor must not begin Layer 3 implementation unless explicitly instructed.

---

## 2. Current Active Scope

The current active scope is:

```text
Prepare and implement Layer 2 as an independent Motive solved-skeleton kinematics project.
```

Layer 2 should convert Motive-solved global bone quaternions into continuous filtered parent-child relative rotation-vector features.

The core Layer 2 transformation is:

```text
Motive global bone quaternions
  -> validated bone quaternion table
  -> normalized and sign-continuous global quaternions
  -> parent-child relative quaternions
  -> sign-continuous relative quaternions
  -> log-map rotation vectors
  -> continuous filtered joint_rx / joint_ry / joint_rz features
```

The first successful Layer 2 result should be a valid continuous feature table from one representative Motive mixed CSV, before scaling to all sessions.

---

## 3. Layer 2 Independence From Layer 1

Layer 1 is complete for now and may be used as conceptual background only.

Layer 2 must not:

```text
import Layer 1 code
depend on Layer 1 outputs
require raw-marker QC reports to produce its own features
use raw marker XYZ data to compute final Layer 2 kinematic variables
assume that Layer 1 masks or artifact flags are available
```

Layer 2 may mention Layer 1 only as part of the broader architecture:

```text
Layer 1 = measurement-level QC evidence
Layer 2 = solved-skeleton kinematic feature extraction
Layer 3 = segmentation and JcvPCA-style analysis
```

For now, Layer 2 should stand on its own.

---

## 4. Layer 2 Must Not Implement Layer 3

During Layer 2 work, Cursor must not implement:

```text
segmentation into Group 4 or Group 5
JcvPCA
PCA
JRW
natural variability comparison
T1 vs T2 or T1 vs T3 comparison
interpretation tables
statistical analysis
movement-complexity interpretation
```

Layer 2 may only prepare the feature outputs that Layer 3 will later consume.

Layer 3 details in the master plan are context only during Layer 2 development.

---

## 5. Layer 2 Output Contract

The main Layer 2 output should be a continuous time-series feature table.

Required feature form:

```text
filtered parent-child relative rotation-vector components:
joint_rx
joint_ry
joint_rz
```

Recommended outputs:

```text
relative_joint_quaternions.parquet
relative_rotation_vectors_unfiltered.parquet
relative_rotation_vectors_filtered.parquet
relative_rotation_vectors_filtered.csv
layer2_feature_table_continuous.parquet
layer3_feature_manifest.csv
layer2_final_validation_report.csv
layer2_metadata.json
```

Layer 2 should also export diagnostic reports:

```text
bone_inventory.csv
parent_child_joint_map_used.csv
frame_time_validation_report.csv
bone_quaternion_missingness_report.csv
quaternion_norm_report.csv
quaternion_sign_flip_report_global.csv
quaternion_sign_flip_report_relative.csv
rotation_vector_jump_report.csv
filter_settings_report.csv
```

---

## 6. Master Plan vs Layer 2 Spec Priority

If there is any conflict between the master plan and the detailed Layer 2 specification, use the following priority order:

```text
1. Latest Layer 2 correction addendum
2. Layer 2 v5 specification files
3. This master-plan scope addendum
4. MASTER_PLAN.md
5. Older pseudocode or informal notes
```

For Layer 2 implementation, the detailed Layer 2 spec overrides the broad master plan.

---

## 7. Required Correction to Layer 3 Context: Joint Grouping Rule

The broad materials contain a possible inconsistency in Layer 3 joint-level aggregation.

The preferred default rule should be:

```text
For each joint and PC:

JRW_A_joint = sqrt(A_rx^2 + A_ry^2 + A_rz^2)
JRW_B_joint = sqrt(B_rx^2 + B_ry^2 + B_rz^2)

JcvPCA_joint = JRW_B_joint - JRW_A_joint
```

This root-sum-square rule treats the three rotation-vector axes as a 3D joint-level magnitude.

Cursor must not replace this with a simple sum of absolute rx/ry/rz components unless explicitly approved after scientific review.

This issue matters for Layer 3 only. It should not affect Layer 2 implementation except that Layer 2 must preserve clean rx/ry/rz feature naming per joint.

---

## 8. Recommended Layer 2 Project Skeleton

Cursor should create a maintainable project skeleton before implementing algorithms.

Recommended structure:

```text
layer2_motive_kinematics/
  README.md
  pyproject.toml

  src/
    layer2_motive/
      __init__.py
      cli.py
      parsing.py
      schema.py
      quaternions.py
      hierarchy.py
      rotvec.py
      filtering.py
      validation.py
      reporting.py
      io.py

  tests/
    test_frame_time_detection.py
    test_motive_header_parsing.py
    test_quaternion_component_order.py
    test_quaternion_normalization.py
    test_quaternion_sign_continuity.py
    test_relative_quaternion_reconstruction.py
    test_gap_detection.py
    test_rotvec_conversion.py
    test_filter_preconditions.py

  configs/
    default_layer2_config.yaml
    parent_child_joint_map_template.csv
    selected_body_joints_template.csv

  docs/
    PROJECT_SCOPE.md
    LAYER2_IMPLEMENTATION_PLAN.md
    ASSUMPTIONS_LOG.md
    DECISION_LOG.md
    VALIDATION_PROTOCOL.md
    KNOWN_LIMITATIONS.md

  examples/
    README.md

  outputs/
    .gitkeep
```

The project should be built as a research-code package, not as a single loose script.

---

## 9. Required Development Tooling

Before implementation, Cursor should evaluate and recommend tooling, but should not install unnecessary tools blindly.

Recommended minimum Python/dev tools:

```text
python >= 3.10
numpy
pandas
scipy
pyarrow
pyyaml
pytest
ruff
pyright or pylance
```

Optional tools only if justified:

```text
matplotlib
plotly
rich
typer
dvc
mlflow
```

Cursor/VS Code extensions that may help:

```text
Python
Pylance
Ruff
Jupyter
GitLens
Error Lens
Rainbow CSV
Markdown All in One
YAML
Code Spell Checker
Parquet viewer, only if needed
```

Do not install random AI coding plugins or large skill libraries unless the benefit is explicitly justified for this Layer 2 project.

---

## 10. Cursor Behavior Rules

Cursor must follow these rules:

```text
1. Inspect files before making claims about repository structure.
2. Do not invent Motive CSV structure.
3. Do not hardcode bone names unless they come from a config file or inspected data.
4. Do not silently choose scientific parameters.
5. Do not silently interpolate missing quaternion data.
6. Do not filter data containing NaNs.
7. Do not use Euler angles in the main pipeline.
8. Do not use raw global quaternion components as PCA-ready features.
9. Do not implement Layer 3 while working on Layer 2.
10. Write tests for every fragile transformation.
```

Cursor should clearly separate:

```text
known from inspected files
specified by project documentation
assumed for implementation
requires user/scientist validation
```

---

## 11. First Implementation Milestones

Cursor should not implement the full Layer 2 pipeline in one pass.

Recommended milestones:

### Milestone 0 — Project Skeleton

Create:

```text
folder structure
pyproject.toml
README.md
docs
config templates
empty modules
test skeletons
```

No algorithmic implementation yet.

### Milestone 1 — Motive CSV Parsing

Implement:

```text
manual header inspection
frame/time detection
bone quaternion column discovery
bone inventory export
parser validation report
```

Stop after one representative file.

### Milestone 2 — Quaternion Validation

Implement:

```text
component order detection from labels
quaternion norm validation
zero-norm detection
missingness detection
global sign-continuity correction
reports
```

Stop before relative rotations.

### Milestone 3 — Relative Joint Rotations

Implement:

```text
parent-child joint map loading
relative quaternion computation
relative sign-continuity correction
reconstruction tests
relative quaternion export
```

Stop and inspect reconstruction error.

### Milestone 4 — Rotation Vectors and Filtering

Implement:

```text
log-map rotation-vector conversion
rotation-vector jump checks
filter precondition checks
Butterworth low-pass filtering in tangent space
filtered feature export
feature manifest export
```

Stop and inspect trajectories.

### Milestone 5 — Scale to Six Part 1 Repetitions

Only after one file is validated, run Layer 2 for:

```text
T1_P1_r1
T1_P1_r2
T2_P1_r1
T2_P1_r2
T3_P1_r1
T3_P1_r2
```

Required validation:

```text
same feature names
same feature order
same parent-child map
same sampling-rate assumptions
no missing required JcvPCA features
```

---

## 12. Scientific Framing to Preserve

Layer 2 should be described as:

```text
Motive-solved global bone quaternions were transformed into parent-child relative joint rotations and mapped to tangent-space rotation-vector features. These continuous filtered relative rotation-vector features serve as the kinematic input for later JcvPCA-style analysis.
```

Layer 2 should not be described as:

```text
direct anatomical joint-angle reconstruction
direct encoder-equivalent joint measurement
validated biomechanical joint loading
movement-complexity analysis
JcvPCA analysis
statistical testing
```

---

## 13. Final Instruction to Cursor

Before implementing Layer 2, Cursor should produce:

```text
1. A short understanding summary.
2. A proposed project skeleton.
3. A list of required inputs.
4. A list of required outputs.
5. A list of assumptions that need validation.
6. A proposed dependency/tooling set.
7. A staged implementation plan.
```

Cursor should wait for review after this planning step.

Implementation should begin only after the Layer 2 project skeleton and assumptions are approved.
