# Motive CSV Structure and Parser Requirements

## Purpose

Build a robust parser for Motive mixed CSV files containing solved skeleton bone quaternion data.

The parser is the most critical part of Layer 2. If the parser misunderstands the CSV structure, every downstream feature will be invalid.

The parser must prove, through reports, that it correctly identified:

```text
metadata
header row roles
frame/time columns
Bone vs Bone Marker vs Marker columns
bone rotation quaternion columns
quaternion component order
bone names
parent names
raw skeleton hierarchy
canonical bone names
selected body joints
ignored columns
```

---

## Motive CSV may use a multi-row header

Motive CSV files may contain a multi-row header, including metadata rows, blank rows, hierarchy rows, and data labels.

The parser must read the first 20 lines and dynamically identify relevant row roles. Do not assume a single-line header.

Expected row roles may include:

```text
metadata row
blank row(s)
Type row
Name row
ID row
Parent row
Property row
Component row
data start row
```

The exact line numbers may vary across exports. The parser must dynamically detect them by content and report the detected line numbers.

---

## Do not use Pandas MultiIndex headers

Do not parse the Motive CSV using:

```python
pd.read_csv(..., header=[...])
```

Motive CSV headers often contain blank cells, blank lines, uneven hierarchy rows, and partially populated columns. Pandas MultiIndex parsing can create `Unnamed` columns and make structure validation fragile.

Instead:

1. Read the header block manually using `open().readlines()` or the Python `csv` module.
2. Preserve blank lines and absolute line numbers.
3. Dynamically identify the row roles.
4. Extract row-level lists for Type, Name, ID, Parent, Property, and Component.
5. Build an explicit flat column map.
6. Load numeric data separately with `pd.read_csv(skiprows=data_start_row, names=flat_column_names)`.

Required output:

```text
outputs/00_csv_structure/header_row_detection.csv
outputs/00_csv_structure/report.md
```

---

## Metadata to detect and report

The parser must try to detect and report:

```text
Rotation Type
Coordinate Space
Capture Frame Rate
Export Frame Rate
Total Frames
Length Units
```

Important requirements:

- `Rotation Type` must be verified for each file.
- `Coordinate Space` must be verified for each file.
- If `Coordinate Space = Global`, the script must compute parent-child relative joint quaternions.
- If `Coordinate Space` is not found or is not Global, stop and ask for user validation.
- If `Rotation Type` is not Quaternion or cannot be verified, stop.

---

## Column categories

Motive mixed CSVs may contain columns of type:

```text
Bone
Bone Marker
Marker
```

Layer 2 must use only:

```text
Type = Bone
Property = Rotation
Components = X, Y, Z, W
```

Layer 2 must not use:

```text
Bone Marker columns
Marker columns
Bone Position columns
Marker Position columns
```

However, ignored columns must still be reported in the inventory.

Required outputs:

```text
outputs/00_csv_structure/detected_columns.csv
outputs/00_csv_structure/unmatched_columns.csv
outputs/00_csv_structure/columns_used_for_layer2.csv
outputs/00_csv_structure/columns_ignored_for_layer2.csv
```

---

## Quaternion column detection

For each bone, the parser must group four rotation columns:

```text
X
Y
Z
W
```

The expected source quaternion order in Motive exports may be:

```text
X, Y, Z, W
```

SciPy expects:

```text
x, y, z, w
```

Therefore, if source columns are detected as X/Y/Z/W, no reordering is needed for SciPy.

Do not assume this silently. Detect and report it.

Required outputs:

```text
outputs/02_quaternion_detection/quaternion_column_groups.csv
outputs/02_quaternion_detection/convention_report.csv
```

The convention report must include:

```text
source_component_order
scipy_component_order
reordering_required
status
notes
```

---

## Frame and Time column detection

Frame and Time columns may not have values in the upper hierarchy rows such as Type, Name, ID, or Parent. They may appear only in a lower header row such as the Component/header-label row.

The parser must detect frame/time columns by scanning the full header block for labels such as:

```text
Frame
Time
Time (Seconds)
Seconds
```

The parser must not require Frame and Time columns to have valid Type/Name/Parent labels.

If Frame and Time are detected at indices 0 and 1, report that. If they are detected elsewhere, report their actual indices.

Required output:

```text
outputs/03_frame_timing/frame_time_column_detection.csv
```

---

## Subject prefixes and canonical names

Motive bone names may contain subject-specific prefixes such as:

```text
671:Chest
671:LThigh
671:RShin
```

The parser must strip subject prefixes from both:

```text
Name row
Parent row
```

Canonical examples:

```text
671:Chest  -> Chest
671:LThigh -> LThigh
671:RShin  -> RShin
```

Preserve original source names in all reports.

Required mapping fields:

```text
source_bone_name
canonical_bone_name
source_parent_name
canonical_parent_name
subject_prefix
```

Do not hardcode a specific subject ID such as `671`.

---

## Special handling of Parent == Root

The Parent row may contain the label:

```text
Root
```

This indicates that the bone has no physical parent bone in the CSV hierarchy. The parser must not search for a bone named `Root` and must not crash.

Root handling must be explicit:

- Do not include the root as a relative joint unless explicitly configured.
- If root orientation is saved, save it separately as root/global orientation metadata.
- Parent == Root must be recorded in the hierarchy report.

Do not silently choose whether the root relative quaternion is identity or equal to the global root quaternion. If root inclusion is needed, make it a documented configuration choice.

---

## Parent-child hierarchy

The Parent header row provides the raw skeleton hierarchy. The parser must use it to construct a source hierarchy table.

Then create a curated selected-joint map for Layer 2 body features.

Required outputs:

```text
outputs/01_joint_mapping/hierarchy_mapping.csv
outputs/01_joint_mapping/parent_child_joint_map.csv
outputs/01_joint_mapping/all_bones_inventory.csv
outputs/01_joint_mapping/selected_body_bones.csv
outputs/01_joint_mapping/excluded_finger_bones.csv
outputs/01_joint_mapping/missing_expected_joints.csv
```

---

## Robustness principle

Use the provided sample CSV as an example of Motive structure, not as a fixed template.

Do not hardcode:

```text
specific row numbers
specific subject IDs
specific bone-name prefixes
specific number of bones
specific assumption that Frame/Time are always columns 0 and 1
```

Instead:

```text
detect dynamically
report explicitly
stop when ambiguous
```

## v5 parser safety clarifications

The parser must not only detect columns; it must prevent unsafe downstream processing.

### Missing/invalid quaternion policy

If required bone quaternion columns contain NaNs, infinite values, empty cells, zero-norm quaternions, or near-zero-norm quaternions, the parser/QC stage must flag them before any relative quaternion computation.

Small gaps up to 5 consecutive frames may be repaired only if the method is explicit and logged. Larger gaps must stop the pipeline before filtering.

### No hardcoded anatomical split

Bone names vary across Motive exports. The body-vs-distal/finger split should use transparent heuristics and then require user validation.

### Flat hierarchy representation

The Parent row should be parsed into a flat table and dictionary mapping. Do not require an object-oriented skeleton tree for Layer 2 V0.
