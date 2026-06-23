# Agent Stop-and-Validate Protocol

## Core rule

The agent must not implement or run the full pipeline in one uninterrupted pass.

The agent must proceed stage by stage, and after each stage it must stop and present validation materials to the user.

---

## Required stop message after each stage

After each stage, report:

```text
Stage completed
What was detected
What assumptions were made
Files written
Warnings/errors
Plots generated
What the next stage will do
Specific items the user should validate
```

Then wait for user approval before continuing.

---

## Mandatory validation checkpoints

### After Stage 00

User must validate:

```text
metadata detection
header row detection
data start row
Frame/Time column detection
Bone/Bone Marker/Marker classification
```

### After Stage 01

User must validate:

```text
canonical bone names
subject-prefix stripping
Root handling
parent-child hierarchy
selected body bones
excluded fingers
missing expected joints
```

### After Stage 02

User must validate:

```text
quaternion component grouping
source order X/Y/Z/W or other
SciPy order mapping
```

### After Stage 03

User must validate:

```text
frame count
duration
sampling rate
frame/time monotonicity
large timing gaps
```

### After Stage 04

User must validate:

```text
missing/invalid quaternion counts
norm ranges
zero-norm checks
selected bones status
```

### After Stage 05

User must validate:

```text
sign flip counts
before/after component plots
whether flips are concentrated in key joints
```

### After Stage 06

User must validate:

```text
relative joint map
computed relative quaternion set
relative quaternion sign-continuity report (before log-map)
relative quaternion norm report
```

### After Stage 07

User must validate:

```text
rotvec feature map
unfiltered rotation-vector heatmap
rotation-vector jump report
jump flags
```

### After Stage 08

User must validate:

```text
filter report
before/after filter plot
final feature matrix shape
final CSV/parquet output files
```

---

## Fail-loudly rules

Stop immediately if:

```text
Rotation Type is not Quaternion or cannot be verified
Coordinate Space is not Global or cannot be verified
quaternion order cannot be determined
required Bone Rotation X/Y/Z/W groups are missing
Frame/Time columns cannot be identified
Parent hierarchy cannot be built
selected parent-child map is incomplete
zero-norm quaternions exist in selected bones
relative quaternion computation fails
rotation-vector jumps indicate severe discontinuities
filter cutoff is invalid relative to Nyquist frequency
```

When stopping, write a clear error report and do not proceed silently.

## v5 additional validation checkpoints

### After Stage 04 — Missing/invalid data decision

The stop message must explicitly answer:

```text
Were any NaNs, infinite values, empty cells, zero-norm, or near-zero-norm quaternions found?
Were any gaps interpolated?
What interpolation method was used?
What was the maximum gap length?
Are there any gaps larger than 5 frames?
Is it safe to continue to relative rotations and filtering?
```

If any required selected joint has a gap larger than 5 consecutive frames, stop and ask the user whether to exclude the joint/window/file. Do not continue to filtering.

### After Stage 06 — Reconstruction acid test

The stop message must include the reconstruction test result:

```text
q_parent_global * q_joint_relative ≈ q_child_global
```

Report angular error for at least one random frame and selected joint. Prefer reporting several random tests plus the worst-case test over a small sample.

If reconstruction fails, do not continue to log-map conversion.

### After Stage 08 — Filter visual validation

The stop message must include links/paths to:

```text
before_after_filter_plot.png
before_after_filter_plot_zoom_2sec.png
```

The zoomed 2-second plot is mandatory. The user must be able to inspect whether the filter caused visible phase shift or excessive smoothing.
