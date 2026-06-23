# Layer 2 Stage-by-Stage Implementation Specification

## Final goal

Produce:

```text
outputs/08_filtering/relative_rotation_vectors_filtered.parquet
outputs/08_filtering/relative_rotation_vectors_filtered.csv
```

These files must contain filtered parent-child relative joint rotation-vector features.

---

## Stage 00 — CSV structure audit

### Goal

Understand the Motive CSV structure before loading data for computation.

### Required actions

- Read first 20 lines manually using Python `open()` or `csv` module.
- Preserve blank lines and absolute line numbers.
- Detect metadata.
- Detect row roles: Type, Name, ID, Parent, Property, Component.
- Detect data start row.
- Detect frame/time candidate columns.
- Detect high-level column categories: Bone / Bone Marker / Marker.

### Required reports

```text
outputs/00_csv_structure/report.md
outputs/00_csv_structure/header_row_detection.csv
outputs/00_csv_structure/detected_columns.csv
outputs/00_csv_structure/unmatched_columns.csv
outputs/00_csv_structure/columns_used_for_layer2.csv
outputs/00_csv_structure/columns_ignored_for_layer2.csv
```

### Stop condition

Stop after this stage and ask the user to validate that the detected structure is correct.

---

## Stage 01 — Bone rotation column discovery and joint mapping foundation

### Goal

Identify all Bone Rotation X/Y/Z/W column groups and create the initial hierarchy map.

### Required actions

- Use only columns where Type = Bone and Property = Rotation.
- Group X/Y/Z/W components per bone.
- Strip subject prefixes from both Name and Parent rows.
- Preserve source names.
- Handle Parent == Root explicitly.
- Build all-bones inventory.
- Build raw hierarchy table from Parent row.
- Build selected body-bones table.
- Build excluded-finger-bones table.
- Build missing expected joints table.

### Required reports

```text
outputs/01_joint_mapping/report.md
outputs/01_joint_mapping/joint_channel_map.csv
outputs/01_joint_mapping/hierarchy_mapping.csv
outputs/01_joint_mapping/parent_child_joint_map.csv
outputs/01_joint_mapping/all_bones_inventory.csv
outputs/01_joint_mapping/selected_body_bones.csv
outputs/01_joint_mapping/excluded_finger_bones.csv
outputs/01_joint_mapping/missing_expected_joints.csv
```

### Stop condition

Stop and ask the user to validate canonical bone names and parent-child mapping before continuing.

---

## Stage 02 — Quaternion convention detection

### Goal

Confirm quaternion component order and SciPy conversion convention.

### Required actions

- Verify that each selected bone has exactly X, Y, Z, W rotation columns.
- Detect source order.
- Verify whether reordering is needed for SciPy.
- Write convention report.

### Required reports

```text
outputs/02_quaternion_detection/report.md
outputs/02_quaternion_detection/quaternion_column_groups.csv
outputs/02_quaternion_detection/convention_report.csv
```

### Stop condition

Stop if component order is ambiguous or incomplete.

---

## Stage 03 — Frame/time validation

### Goal

Verify time base and frame ordering.

### Required actions

- Detect frame and time columns robustly.
- Load numeric data with flat column names.
- Validate monotonic frame index.
- Validate monotonic time.
- Detect duplicate frames.
- Detect missing frame IDs.
- Estimate sampling rate from median time difference.
- Compare estimated sampling rate with metadata if available.

### Required reports and plots

```text
outputs/03_frame_timing/report.md
outputs/03_frame_timing/frame_time_column_detection.csv
outputs/03_frame_timing/frame_timing_summary.csv
outputs/03_frame_timing/frame_timing_plot.png
```

### Stop condition

Stop if frame/time structure is ambiguous or invalid.

---

## Stage 04 — Missing/invalid quaternion report and quaternion normalization

### Goal

Validate numerical quaternion data and normalize quaternions.

### Required actions

- Check NaN values.
- Check infinite values.
- Check empty values.
- Check zero-norm quaternions.
- Compute quaternion norms before normalization.
- Normalize every quaternion: `q_normalized = q / ||q||`.
- Save norm report.

### Required reports and plots

```text
outputs/04_quaternion_qc/report.md
outputs/04_quaternion_qc/missing_invalid_quaternion_report.csv
outputs/04_quaternion_qc/quaternion_norms.csv
outputs/04_quaternion_qc/quaternion_norm_plot.png
```

### Stop condition

Stop if many quaternions are invalid, if zero-norm quaternions exist in selected bones, or if norms are far from 1 beyond threshold.

---

## Stage 05 — Bone-level sign-continuity correction

### Goal

Remove quaternion sign flips at the bone level before relative rotations.

### Required action

For each bone independently:

```python
if dot(q[t], q[t-1]) < 0:
    q[t] = -q[t]
```

### Required reports and plots

```text
outputs/05_sign_continuity/report.md
outputs/05_sign_continuity/sign_flip_report.csv
outputs/05_sign_continuity/before_after_plot.png
```

### Stop condition

Stop if sign flips are unexpectedly large or concentrated in key body bones.

---

## Stage 06 — Parent-child relative quaternion computation and validation

### Goal

Convert global bone quaternions into parent-child relative joint quaternions.

### Required mathematical operation

```text
q_joint(t) = inverse(q_parent_global(t)) * q_child_global(t)
```

### Required actions

- Use the curated `parent_child_joint_map.csv`.
- Exclude joints with missing parent or child bones.
- Do not treat Parent == Root as a normal physical parent.
- Compute relative quaternions for selected joints.
- Validate relative quaternion norms.
- Apply **relative quaternion sign-continuity correction** per joint (same rule as Stage 05: flip sign when `dot(q[t], q[t-1]) < 0`). Must run after relative quaternion computation and **before** Stage 07 log-map conversion.
- Run reconstruction validation (see v5 Stage 06 requirements).
- Save relative quaternion dataset (post sign-continuity).

### Required reports

```text
outputs/06_local_relative_validation/report.md
outputs/06_local_relative_validation/hierarchy_mapping.csv
outputs/06_local_relative_validation/relative_joint_quaternions.parquet
outputs/06_local_relative_validation/relative_rotation_summary.csv
outputs/06_local_relative_validation/relative_sign_flip_report.csv
outputs/06_local_relative_validation/relative_sign_continuity_before_after_plot.png
```

### Stop condition

Stop if any selected joint cannot be computed or relative quaternion norms are invalid.

---

## Stage 07 — Log-map to rotation vectors and jump checks

### Goal

Map relative quaternions to tangent-space rotation-vector features.

### Required actions

- Use `scipy.spatial.transform.Rotation.from_quat(...).as_rotvec()`.
- Remember SciPy expects `[x, y, z, w]`.
- For each joint, generate three features: `joint_rx`, `joint_ry`, `joint_rz`.
- Save unfiltered rotation-vector features.
- Generate a feature map.
- Compute jump magnitudes:

```text
jump[t] = norm(r[t] - r[t-1])
```

- Write jump report and jump flags.

### Required reports and plots

```text
outputs/07_rotvec_conversion/report.md
outputs/07_rotvec_conversion/rotvec_feature_map.csv
outputs/07_rotvec_conversion/relative_rotation_vectors_unfiltered.parquet
outputs/07_rotvec_conversion/relative_rotation_vectors_unfiltered.csv
outputs/07_rotvec_conversion/rotvec_heatmap.png
outputs/07_rotvec_conversion/rotation_vector_jump_report.csv
outputs/07_rotvec_conversion/rotation_vector_jump_flags.csv
```

### Stop condition

Stop if rotation-vector jumps indicate major discontinuities or log-map artifacts.

---

## Stage 08 — Butterworth low-pass filtering in tangent space

### Goal

Apply low-pass filtering to rotation-vector components, not raw quaternion components.

### Required filtering rule

Do not filter quaternion components directly.

Filter each rotation-vector component independently using zero-phase Butterworth filtering.

Recommended initial parameters:

```text
sampling_rate = inferred from file, expected around 120 Hz
cutoff_hz = 10
filter_order = 4
method = scipy.signal.sosfiltfilt
```

### Required actions

- Validate cutoff against Nyquist frequency.
- Apply filtering to each `*_rx`, `*_ry`, `*_rz` feature.
- Save filtered feature matrix.
- Save filter report.
- Generate before/after plot for selected features.

### Required reports and plots

```text
outputs/08_filtering/report.md
outputs/08_filtering/filter_report.csv
outputs/08_filtering/relative_rotation_vectors_filtered.parquet
outputs/08_filtering/relative_rotation_vectors_filtered.csv
outputs/08_filtering/before_after_filter_plot.png
```

### Stop condition

Stop after generating final outputs and ask user to validate reports and plots before any Layer 3 work.

---

## Optional Stage 08b — Filter sensitivity

For V0 this may be skipped unless requested.

If implemented, run:

```text
6 Hz
10 Hz
15 Hz
```

and save:

```text
outputs/08_filtering/filter_sensitivity_summary.csv
```

Do not use this as an excuse to implement PCA/JcvPCA.

## v5 Stage-specific safety requirements

### Stage 04 — Missing/invalid quaternion mitigation rule

Stage 04 must not only report missing or invalid quaternions. It must decide whether the file can safely continue.

Invalid values include:

```text
NaN
infinite values
empty numeric cells
zero-norm quaternions
near-zero-norm quaternions
```

Critical rule:

```text
Do not pass NaNs or zero-norm quaternions into relative-rotation computation, log-map conversion, or sosfiltfilt.
sosfiltfilt will propagate NaNs and can make an entire filtered trajectory unusable.
```

Required mitigation policy:

1. If there are no missing/invalid quaternion values, continue.
2. If a joint has short isolated gaps up to 5 consecutive frames, the script may propose interpolation.
3. Any interpolation must be explicitly logged, even if the gap is only one frame.
4. If gaps exceed 5 consecutive frames for any required selected joint, stop before filtering.
5. If zero-norm quaternions occur, treat them as invalid/missing first; do not normalize them.
6. If interpolation is used for quaternion data, prefer spherical interpolation (`Slerp`) when feasible. For V0, linear interpolation followed by normalization may be allowed only if clearly documented as a pragmatic repair for very short gaps.
7. Save both pre-mitigation and post-mitigation QC reports.

Required outputs:

```text
outputs/04_quaternion_qc/missing_invalid_quaternion_report.csv
outputs/04_quaternion_qc/quaternion_gap_report.csv
outputs/04_quaternion_qc/quaternion_mitigation_log.csv
outputs/04_quaternion_qc/report.md
```

The report must clearly state:

```text
n_missing_values
n_zero_norm_quaternions
max_gap_length_by_bone
interpolation_applied_true_false
interpolation_method
frames_interpolated
stop_required_true_false
```

### Stage 05 — Efficient sign-continuity correction

The sign-continuity correction rule remains:

```text
if dot(q[t], q[t-1]) < 0:
    q[t] = -q[t]
```

However, the implementation should avoid deeply nested Python loops over every frame and every quaternion component.

Use NumPy-based operations wherever practical. A reasonable implementation may still loop over bones, but should vectorize over frames as much as possible.

Reference approach:

```python
# q has shape (n_frames, 4), in [x, y, z, w]
dots = np.sum(q[1:] * q[:-1], axis=1)
# use these dot products to detect sign flips and apply a cumulative sign correction
```

The implementation must preserve correctness over cleverness. If a vectorized implementation becomes unclear, use a simple per-bone function with clear comments, but avoid unnecessary complexity.

### Stage 06 — Quaternion multiplication must use SciPy Rotation objects

Do not compute relative quaternions using raw NumPy multiplication.

Wrong:

```python
q_relative = q_parent_inv * q_child  # if these are raw arrays, this is element-wise and wrong
```

Correct:

```python
from scipy.spatial.transform import Rotation as R

r_parent = R.from_quat(q_parent_xyzw)
r_child = R.from_quat(q_child_xyzw)
r_joint = r_parent.inv() * r_child
q_joint_xyzw = r_joint.as_quat()
```

The required mathematical operation is:

```text
q_joint(t) = inverse(q_parent_global(t)) * q_child_global(t)
```

The required implementation mechanism is SciPy `Rotation` multiplication.

### Stage 06 — Relative quaternion sign-continuity correction

After computing relative joint quaternions and before log-map conversion, apply sign-continuity correction **per selected joint** independently:

```text
if dot(q_relative[t], q_relative[t-1]) < 0:
    q_relative[t] = -q_relative[t]
```

Use NumPy-vectorized operations over frames where practical (same guidance as Stage 05).

Required outputs:

```text
outputs/06_local_relative_validation/relative_sign_flip_report.csv
outputs/06_local_relative_validation/relative_sign_continuity_before_after_plot.png
```

Run the reconstruction acid test on relative quaternions **after** sign-continuity correction.

### Stage 06 — Reconstruction acid test

After relative sign-continuity correction, run a reconstruction test.

For at least one random frame and one random selected joint, verify:

```text
q_parent_global(t) * q_joint_relative(t) ≈ q_child_global(t)
```

Using SciPy:

```python
r_reconstructed_child = r_parent * r_joint
```

Report the angular reconstruction error in radians/degrees.

Required output:

```text
outputs/06_local_relative_validation/reconstruction_test_report.csv
```

Minimum fields:

```text
joint_name
frame_index
parent_bone
child_bone
angular_error_rad
angular_error_deg
pass_true_false
```

If the reconstruction error is large, stop. This usually means quaternion order, parent-child direction, or multiplication order is wrong.

### Stage 07 — Finger/distal-bone split should use transparent heuristics

The agent must not assume a fixed universal list of finger bones. Motive naming may vary.

Use transparent heuristics such as keywords:

```text
Thumb
Index
Middle
Ring
Pinky
Finger
HandThumb
HandIndex
Toe
```

Important distinction:

- `Hand` may be a useful body endpoint and should not automatically be excluded.
- Finger bones distal to the hand should usually be excluded from V0.
- Toe handling should be configurable: toes may be excluded for a strict 19-joint body set or included as foot endpoints.

The proposed split must be written to:

```text
outputs/01_joint_mapping/selected_body_bones.csv
outputs/01_joint_mapping/excluded_distal_bones.csv
```

The user must validate this split before continuing.

### Stage 08 — Filtering diagnostics must include a 2-second zoom window

Full-duration plots over 30,000+ frames are not sufficient for validating filtering.

The filter report must include:

1. A full-duration before/after overview plot.
2. A zoomed 2-second high-movement window.

The zoom window should be selected automatically by finding a period with high rotation-vector magnitude or high frame-to-frame change, using selected representative joints.

Required plot:

```text
outputs/08_filtering/before_after_filter_plot_zoom_2sec.png
```

The report must state:

```text
zoom_window_start_time
zoom_window_end_time
selection_rule
selected_features_plotted
```

Purpose:

- Visually check that `sosfiltfilt` did not create obvious phase shift.
- Check that important movement peaks were not over-smoothed.
- Make the filter behavior inspectable rather than hidden.
