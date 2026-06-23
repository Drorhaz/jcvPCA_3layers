# Output Folder and Reporting Contract

## Required output structure

The script must write outputs exactly under a user-specified output directory, defaulting to:

```text
outputs/
```

Required folder structure:

```text
outputs/
  00_csv_structure/
    report.md
    header_row_detection.csv
    detected_columns.csv
    unmatched_columns.csv
    columns_used_for_layer2.csv
    columns_ignored_for_layer2.csv

  01_joint_mapping/
    report.md
    joint_channel_map.csv
    hierarchy_mapping.csv
    parent_child_joint_map.csv
    all_bones_inventory.csv
    selected_body_bones.csv
    excluded_finger_bones.csv
    missing_expected_joints.csv

  02_quaternion_detection/
    report.md
    quaternion_column_groups.csv
    convention_report.csv

  03_frame_timing/
    report.md
    frame_time_column_detection.csv
    frame_timing_summary.csv
    frame_timing_plot.png

  04_quaternion_qc/
    report.md
    missing_invalid_quaternion_report.csv
    quaternion_norms.csv
    quaternion_norm_plot.png

  05_sign_continuity/
    report.md
    sign_flip_report.csv
    before_after_plot.png

  06_local_relative_validation/
    report.md
    hierarchy_mapping.csv
    relative_joint_quaternions.parquet
    relative_rotation_summary.csv
    relative_sign_flip_report.csv
    relative_sign_continuity_before_after_plot.png

  07_rotvec_conversion/
    report.md
    rotvec_feature_map.csv
    relative_rotation_vectors_unfiltered.parquet
    relative_rotation_vectors_unfiltered.csv
    rotvec_heatmap.png
    rotation_vector_jump_report.csv
    rotation_vector_jump_flags.csv

  08_filtering/
    report.md
    filter_report.csv
    relative_rotation_vectors_filtered.parquet
    relative_rotation_vectors_filtered.csv
    before_after_filter_plot.png

  assumptions_log.md
  run_summary.md
```

---

## Report requirements

Every stage must write a human-readable `report.md` that includes:

```text
stage name
input files used
what was detected
what assumptions were made
what outputs were written
warnings
errors
validation status
next recommended action
```

Every stage must also write machine-readable CSV or JSON reports.

---

## Assumptions log

The script must maintain:

```text
outputs/assumptions_log.md
```

Every assumption must be explicit.

Example assumptions:

```text
Assumption 001: Coordinate Space was detected as Global from the metadata row.
Assumption 002: Rotation Type was detected as Quaternion.
Assumption 003: Quaternion source order was detected as X/Y/Z/W and passed directly to SciPy.
Assumption 004: Subject prefixes were stripped by removing the substring before the first colon.
Assumption 005: Finger bones were excluded from the V0 selected body-joint feature set.
Assumption 006: Root orientation was not included as a relative joint feature.
Assumption 007: Butterworth filtering was applied to rotation-vector features, not quaternion components.
```

Do not hide assumptions in code comments only.

---

## Plot requirements

All required plots must be saved as PNG files.

Optional interactive HTML plots may be generated with Plotly, but PNG outputs remain required.

Use simple, readable plots. Do not prioritize aesthetics over diagnostic clarity.

Required diagnostic plot types:

```text
frame timing plot
quaternion norm plot
sign-continuity before/after plot
rotation-vector heatmap
filter before/after plot
```

---

## Final output contract

The final filtered feature files must contain:

```text
frame
time
joint_rx / joint_ry / joint_rz columns for each selected relative joint
```

Feature names must be stable and documented in:

```text
outputs/07_rotvec_conversion/rotvec_feature_map.csv
```

The final outputs must be:

```text
outputs/08_filtering/relative_rotation_vectors_filtered.parquet
outputs/08_filtering/relative_rotation_vectors_filtered.csv
```

## v5 additional required outputs

Add these files to the output contract.

### Stage 04

```text
outputs/04_quaternion_qc/quaternion_gap_report.csv
outputs/04_quaternion_qc/quaternion_mitigation_log.csv
```

### Stage 06

```text
outputs/06_local_relative_validation/reconstruction_test_report.csv
outputs/06_local_relative_validation/relative_sign_flip_report.csv
outputs/06_local_relative_validation/relative_sign_continuity_before_after_plot.png
```

### Stage 08

```text
outputs/08_filtering/before_after_filter_plot_zoom_2sec.png
```

Every interpolation, repair, skipped joint, excluded distal bone, and failed validation must also be recorded in:

```text
outputs/assumptions_log.md
```
