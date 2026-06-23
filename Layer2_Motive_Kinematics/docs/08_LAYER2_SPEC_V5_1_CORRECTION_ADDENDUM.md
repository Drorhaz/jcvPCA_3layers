# Layer 2 Motive CSV Agent Spec — v5.1 Correction Addendum

## Purpose

This addendum should be added to the Layer 2 Motive CSV agent specification package before implementation begins. It does not replace the existing v5 specification. Instead, it clarifies several implementation-critical ambiguities and strengthens the project structure, validation logic, output naming, and scientific guardrails.

The goal is to make Layer 2 implementation safer, more maintainable, and more defensible for research/thesis-level use.

## Scope of this Addendum

This addendum applies to the current Layer 2 project only.

Layer 2 should remain independent from Layer 1 for now. Layer 1 may be referenced only as broader architectural context, but Layer 2 must not import Layer 1 code, assume Layer 1 output files, or require Layer 1 masks to run.

Layer 2 is responsible for producing a reliable kinematic representation from Motive solved-skeleton CSV exports. It should not perform PCA, JcvPCA, JRW computation, T1/T2 comparison, movement interpretation, statistical testing, or thesis-level claims about coordination or complexity.

---

# 1. Standardize Output Naming for Excluded Bones

## Current issue

The v5 specification uses both:

- `excluded_finger_bones.csv`
- `excluded_distal_bones.csv`

This creates unnecessary ambiguity for implementation and downstream reporting.

## Required correction

Use the unified filename:

```text
excluded_distal_bones.csv
```

This is preferred because exclusions may include fingers, toes, distal hand segments, distal foot segments, or other distal/non-core bones depending on the Motive skeleton and project configuration.

## Required columns

The file should include, at minimum:

```text
bone_name
parent_bone
exclusion_reason
exclusion_category
matched_rule
```

Suggested values for `exclusion_category`:

```text
finger
toe
distal_hand
distal_foot
non_body_core
unknown_or_manual_review
```

The original term “finger bones” may still appear in explanatory documentation, but the output contract should use `excluded_distal_bones.csv` consistently.

---

# 2. Define Default Gap and Missing-Value Behavior

## Current issue

The v5 specification says that small gaps may be repaired, preferably with Slerp, but it does not define the default behavior. This leaves too much discretion to the implementation agent.

## Required correction

Default V0 behavior should be conservative:

```text
Detect and report all missing values, zero-norm quaternions, invalid quaternion rows, and frame gaps.
Do not automatically interpolate by default.
```

Interpolation should occur only when explicitly enabled by configuration or CLI flag, for example:

```text
--allow-short-gap-interpolation
```

## Required rules

1. All missing/invalid data must be reported before any mitigation.
2. By default, the pipeline should stop before filtering if required selected bones contain missing/invalid values.
3. If interpolation is explicitly enabled:
   - interpolate only gaps of length <= 5 frames;
   - use Slerp where feasible;
   - if linear interpolation + normalization is used as a fallback, document this clearly;
   - save both pre-mitigation and post-mitigation reports;
   - log every interpolated gap, even if very small.
4. If any required selected bone has a gap > 5 frames, stop before filtering.
5. Never pass NaNs, infinite values, or zero-norm quaternions into `scipy.signal.sosfiltfilt`.

## Suggested reports

```text
missingness_pre_mitigation.csv
missingness_post_mitigation.csv
interpolation_log.csv
stage04_missingness_summary.md
```

---

# 3. Clarify Quaternion “Convention Detection”

## Current issue

The v5 specification refers to “quaternion convention detection.” This may overstate what can be inferred from a Motive CSV alone.

From the CSV, the parser can usually detect component labels/order such as X/Y/Z/W or W/X/Y/Z. However, it cannot always prove deeper rotation-convention questions such as:

- active vs passive interpretation;
- coordinate-system handedness;
- anatomical axis meaning;
- whether the exported global orientation corresponds perfectly to SciPy’s interpretation;
- whether the skeleton’s local anatomical axes match the intended biomechanical interpretation.

## Required correction

Rename this concept as:

```text
quaternion component-order detection and SciPy compatibility validation
```

Do not claim that the pipeline fully validates all quaternion conventions or anatomical meanings.

## Required language

Use conservative wording such as:

```text
The parser detects quaternion component labels and arranges components into SciPy-compatible order. Reconstruction tests validate internal consistency of the chosen parent-child relative rotation computation, but they do not independently validate anatomical joint-angle interpretation.
```

---

# 4. Strengthen Relative Rotation Reconstruction Testing

## Current issue

The v5 specification mentions a reconstruction test but allows a minimal test on one random frame and one joint. That is not strong enough for a research-grade pipeline.

## Required correction

The reconstruction test should be mandatory and broad.

For each selected parent-child joint, compute:

```text
q_relative = inv(q_parent_global) * q_child_global
q_child_reconstructed = q_parent_global * q_relative
```

Then compare `q_child_reconstructed` to `q_child_global`.

## Required test coverage

Run reconstruction tests for:

- all selected joints;
- at least 100 valid frames sampled across the recording, or all valid frames if fewer than 100;
- root-adjacent joints and distal excluded examples when useful for debugging;
- the worst-case frame/joint identified after initial testing.

## Required output metrics

Report angular reconstruction error in degrees, including:

```text
joint_name
n_tested_frames
mean_error_deg
median_error_deg
max_error_deg
p95_error_deg
pass_fail
```

## Suggested pass threshold

Use a strict numerical tolerance by default, for example:

```text
max_error_deg <= 1e-5
```

If floating-point behavior or library implementation requires a relaxed threshold, the threshold must be explicitly documented in the decision log.

## Required report

```text
relative_rotation_reconstruction_report.csv
relative_rotation_reconstruction_summary.md
```

The pipeline must stop if reconstruction fails.

---

# 5. Add Explicit Filtering Safety Requirements

## Current issue

The v5 specification correctly warns that filtering must not run on NaNs, but filtering safety should be defined more explicitly.

## Required correction

Before applying `sosfiltfilt`, the pipeline must verify:

1. sampling rate is known and valid;
2. cutoff frequency is valid relative to Nyquist;
3. the number of frames is sufficient for the filter/pad length;
4. no NaNs, infinities, or invalid values exist in the selected feature matrix;
5. filtering is applied only after quaternion normalization, sign-continuity correction, relative rotation computation, and log-map conversion.

## Required sampling-rate handling

Sampling rate should be derived from the Time column when possible and cross-checked against metadata or expected export frame rate.

Report:

```text
sampling_rate_hz
sampling_rate_source
median_dt
min_dt
max_dt
dt_jitter_summary
```

## Required cutoff validation

Use a conservative validation rule such as:

```text
cutoff_hz < 0.45 * sampling_rate_hz
```

Also report:

```text
cutoff_hz
nyquist_hz
normalized_cutoff
filter_order
filter_type
```

## Required short-signal validation

Before filtering, verify that the recording is long enough for the selected filter and `sosfiltfilt` padding requirements.

If too short:

```text
Stop and report the reason.
Do not silently switch to another filter.
Do not use a fallback unless explicitly approved and documented.
```

## Required report

```text
filtering_validation_report.md
```

---

# 6. Add Rotation-Vector Branch-Cut and Continuity Checks

## Current issue

Rotation vectors can become unstable or discontinuous when rotations approach pi radians. The v5 specification includes jump checks, but the branch-cut risk should be explicit.

## Required correction

After log-map conversion and before filtering, report the distribution of rotation-vector norms.

Required metrics:

```text
joint_name
max_rotvec_norm_rad
p95_rotvec_norm_rad
n_frames_near_pi
max_frame_to_frame_jump
p95_frame_to_frame_jump
flag_near_pi
flag_large_jump
```

Suggested warning threshold:

```text
near_pi_threshold_rad = pi - 0.10
```

The exact threshold may be configurable but must be documented.

## Required behavior

If many values are near pi, or if large jumps remain after quaternion sign-continuity correction, the pipeline should stop before filtering and require review.

The report should make clear that tangent-space filtering is only defensible when the rotation-vector representation is reasonably continuous.

## Required report

```text
rotvec_continuity_report.csv
rotvec_continuity_summary.md
```

---

# 7. Clarify Stage-Stopping Behavior: Agent Workflow vs Script Behavior

## Current issue

The v5 specification says the agent should stop after each stage. That is useful for interactive development, but the script should not require interactive user input during execution.

## Required correction

Separate the two concepts:

## Agent workflow

During Cursor/Codex implementation, the agent should stop after major stages, summarize what was implemented, list created files, report tests, and wait for user approval before moving to the next implementation phase.

## Script behavior

The Python package/CLI should support non-interactive stage execution, such as:

```bash
layer2-motive run-stage --stage 03 --input path/to/file.csv --output outputs/session_x
layer2-motive run-until --stage 06 --input path/to/file.csv --output outputs/session_x
layer2-motive run-all --input path/to/file.csv --output outputs/session_x
```

The script should write validation reports and exit cleanly on failure. It should not pause for manual input inside Python.

---

# 8. Add Recommended Project Skeleton

## Required correction

Before algorithm implementation, create a clean Layer 2 project structure. The project should support maintainable code, tests, documentation, configuration, and reproducible outputs.

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
      metadata.py
      hierarchy.py
      quaternions.py
      relative_rotation.py
      rotvec.py
      filtering.py
      validation.py
      reporting.py
      config.py
  tests/
    test_prefix_stripping.py
    test_header_detection.py
    test_frame_time_detection.py
    test_quaternion_component_order.py
    test_quaternion_normalization.py
    test_sign_continuity.py
    test_relative_reconstruction.py
    test_gap_detection.py
    test_filtering_validation.py
  docs/
    PROJECT_SCOPE.md
    LAYER2_IMPLEMENTATION_PLAN.md
    ASSUMPTIONS_LOG_TEMPLATE.md
    DECISION_LOG.md
    VALIDATION_PROTOCOL.md
  configs/
    default_layer2_config.yaml
    selected_body_joints_template.yaml
  examples/
    README.md
  outputs/
    .gitkeep
```

## Notes

- Use `src/layer2_motive/` rather than a flat script-only structure.
- Keep CLI orchestration separate from core logic.
- Keep scientific assumptions in docs/configs, not hidden in code.
- Keep generated outputs out of git unless they are small examples or test fixtures.

---

# 9. Define Initial Selected-Joint Strategy

## Current issue

The v5 specification correctly avoids hardcoding an anatomical list too early, but the first implementation still needs an explicit V0 strategy.

## Required correction

Use a heuristic-first V0 strategy followed by explicit validation.

## V0 selected-joint rule

```text
Select all non-root parent-child bone pairs that are not excluded by distal/finger/toe exclusion rules.
Generate a full candidate joint table.
Require user validation before freezing the selected joint set for downstream Layer 3 use.
```

## Required outputs

```text
candidate_joint_map.csv
selected_joint_map_v0.csv
excluded_distal_bones.csv
joint_selection_summary.md
```

## Required columns for candidate/selected joint maps

```text
joint_id
parent_bone
child_bone
included
exclusion_reason
selection_rule
requires_manual_review
```

## Future direction

After inspecting real Motive exports, the project may move to a config-driven selected-joint map, for example:

```text
configs/selected_body_joints_v1.yaml
```

This should be treated as a later stabilization step, not an assumption in the first parser implementation.

---

# 10. Add Development Tooling Expectations

## Required correction

The project should be created with explicit research-code tooling from the start.

## Required Python/development tools

At minimum, configure:

```text
pytest
ruff
pyright or basedpyright
```

Suggested package dependencies:

```text
numpy
pandas
scipy
pyarrow
pyyaml
```

Optional later dependencies:

```text
polars
matplotlib
rich
typer
```

Do not add optional dependencies unless they solve a specific implementation problem.

## pyproject expectations

`pyproject.toml` should include:

- package metadata;
- Python version requirement;
- dependencies;
- dev dependencies;
- ruff configuration;
- pytest configuration;
- type-checking configuration if applicable.

## Testing expectations

Every stage should have minimal unit tests before moving to the next stage.

High-priority tests:

1. Motive header role detection.
2. Frame/Time column detection.
3. subject/prefix stripping.
4. quaternion component-order mapping.
5. zero-norm quaternion detection.
6. sign-continuity correction.
7. relative rotation reconstruction.
8. missingness/gap detection.
9. filtering validation failure on NaNs.
10. output report contract creation.

---

# 11. Recommended Implementation Phases

Do not implement all stages in one pass.

## Phase 0 — Project setup only

Create:

- repo/project structure;
- `pyproject.toml`;
- README;
- docs;
- configs;
- empty modules;
- test skeleton.

No algorithmic implementation yet.

## Phase 1 — Parser and structure validation

Implement:

- Stage 00: environment/input registration;
- Stage 01: raw CSV structure inspection;
- Stage 02: metadata and header role detection;
- Stage 03: bone/channel discovery.

Goal:

```text
Prove the Motive CSV structure is understood before any quaternion math is attempted.
```

## Phase 2 — Quaternion and relative-rotation safety

Implement:

- Stage 04: missingness and invalid quaternion validation;
- Stage 05: quaternion normalization and sign-continuity correction;
- Stage 06: parent-child relative rotations and reconstruction tests.

Goal:

```text
Prove quaternion processing is internally consistent before log-map conversion or filtering.
```

## Phase 3 — Feature generation and filtering

Implement:

- Stage 07: log-map rotation vectors and continuity checks;
- Stage 08: tangent-space filtering and final feature export.

Goal:

```text
Produce defensible filtered relative rotation-vector features for later Layer 3 analysis.
```

---

# 12. Required Conservative Scientific Language

Layer 2 outputs should be described as:

```text
filtered parent-child relative rotation-vector features derived from Motive-solved global bone quaternions
```

Avoid claiming:

```text
validated anatomical joint angles
clinical joint kinematics
independently verified biomechanical joint rotations
```

Unless separate validation is performed later.

Recommended limitation statement:

```text
Layer 2 derives internally consistent parent-child relative rotation features from Motive-solved skeleton exports. These features are suitable for downstream movement-representation analyses, but they should not be described as independently validated anatomical joint angles unless additional biomechanical validation is performed.
```

---

# 13. Cursor/Codex Instruction Summary

When giving this project to Cursor/Codex, include the following instruction:

```text
Before implementation, apply the v5.1 correction addendum to the Layer 2 specification.
Do not implement all stages at once.
Start with project setup and planning documents only.
Do not import Layer 1 code or require Layer 1 outputs.
Do not make undocumented scientific assumptions.
When uncertain, write the uncertainty into the assumptions log or decision log.
All implementation must be testable, modular, and research-grade.
```

---

# 14. Final Recommendation

The v5 specification is strong and should remain the foundation. This addendum should be treated as a correction and hardening layer before implementation.

The most important decisions added here are:

1. use `excluded_distal_bones.csv` consistently;
2. do not interpolate gaps by default;
3. avoid overstating quaternion convention validation;
4. require broad reconstruction testing;
5. validate filtering safety before `sosfiltfilt`;
6. check rotation-vector continuity and near-pi behavior;
7. separate agent-stage stopping from script execution behavior;
8. create a clean `src/` project skeleton;
9. use heuristic-first joint selection with manual validation;
10. configure testing/linting/type-checking from project start.
