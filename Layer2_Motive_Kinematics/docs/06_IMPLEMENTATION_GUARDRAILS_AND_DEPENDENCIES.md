# Implementation Guardrails and Dependencies

## Purpose

Prevent over-engineering and prevent silent technical assumptions.

The goal is a transparent Layer 2 feature-extraction pipeline, not a general motion-capture platform.

---

## Required dependencies

Use these core dependencies:

```text
pandas
numpy
scipy
matplotlib
pyarrow
```

Required SciPy modules:

```text
scipy.spatial.transform.Rotation
scipy.signal.butter
scipy.signal.sosfiltfilt
```

`pyarrow` is recommended for parquet output.

---

## Optional dependencies

Optional dependencies are allowed only if they serve a clearly defined Layer 2 diagnostic output and do not expand the scope.

```text
plotly
```
Allowed only for optional interactive HTML diagnostics. PNG plots must still be produced with matplotlib.

```text
seaborn
```
Allowed only for simple diagnostic heatmaps if it simplifies code. Matplotlib is preferred.

```text
scikit-learn
```
Not needed for Layer 2 V0. Reserve mainly for Layer 3 PCA/JcvPCA. Do not introduce it in Layer 2 unless there is a specific non-PCA validation reason.

```text
opencv
```
Not needed for Layer 2. Use only if a later branch explicitly adds video/image diagnostics.

```text
pyyaml
```
Allowed only for simple configuration files if needed.

---

## Do not introduce without explicit need

Avoid heavy frameworks and unrelated tools:

```text
tensorflow
pytorch
mocap-specific black-box frameworks
GUI frameworks
dashboards
web servers
database systems
custom plugin systems
```

---

## Code organization

Keep the code simple:

```text
one main CLI script
small helper modules if needed
simple stage functions
plain dictionaries or dataclasses for config
explicit paths
explicit reports
```

Suggested structure:

```text
layer2_motive_quaternion_pipeline.py
utils_parsing.py       optional
utils_quaternion.py    optional
utils_reporting.py     optional
```

Avoid:

```text
large class hierarchy
abstract base classes
complex inheritance
plugin systems
hidden global state
notebook-only implementation
```

---

## Assumptions policy

Never silently assume:

```text
Coordinate Space
Rotation Type
quaternion order
subject prefix
Frame/Time columns
parent-child hierarchy
root handling
selected joint map
sampling rate
filter cutoff validity
```

Every assumption must be written to:

```text
outputs/assumptions_log.md
```

---

## Robustness without over-engineering

The parser should be robust, but the implementation should remain simple.

Robust means:

```text
detect row roles dynamically
preserve blank lines
avoid Pandas MultiIndex traps
report detected structure
stop when ambiguous
```

Robust does not mean:

```text
support every possible file format
invent missing metadata
infer anatomy from arbitrary names
build a full schema framework
silently fix broken files
```

---

## Plotting policy

Required plots must be static PNG files.

Use matplotlib by default.

Plotly HTML diagnostics are optional and must not replace required PNG files.

Avoid complex styling. Diagnostic clarity is more important than visual polish.

---

## Layer boundary

Do not cross into Layer 3.

Layer 2 ends at:

```text
relative_rotation_vectors_filtered.parquet
relative_rotation_vectors_filtered.csv
```

Do not add PCA or JcvPCA logic to this script.

## v5 anti-overengineering and numerical safety rules

### Do not build an object-oriented skeleton tree

Do not build classes such as:

```python
class BoneNode:
    ...
```

Do not build recursive graph traversal code unless absolutely necessary.

For Layer 2 V0, compute parent-child relative rotations using flat structures:

```text
bone_name -> quaternion array
child_bone -> parent_bone
joint_name -> (parent_bone, child_bone)
```

Recommended implementation style:

```python
bone_quats = {bone_name: quat_array_xyzw}
parent_map = {child_bone: parent_bone}
joint_map = {joint_name: (parent_bone, child_bone)}
```

This is easier to audit, debug, and validate than a complex skeleton tree.

### Do not multiply raw quaternion arrays

Quaternion composition must use SciPy `Rotation` objects. Raw NumPy multiplication of quaternion arrays is element-wise multiplication and is mathematically wrong for rotations.

Required reference:

```python
r_joint = r_parent.inv() * r_child
```

### Keep vectorization practical

Use NumPy vectorization for large frame-wise operations where it improves clarity and speed.

Do not create obscure or fragile vectorized code. Clear, tested per-bone helper functions are acceptable. Avoid deeply nested loops over frames, bones, and components when a simple array operation is available.

### Missing data must be resolved before filtering

`scipy.signal.sosfiltfilt` must not receive NaNs or infinite values. Missing or invalid data must be repaired, excluded, or stopped before filtering.
