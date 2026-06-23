# Parser Robustness Requirements for Motive CSV

## Purpose

These requirements prevent early parser failures caused by Motive CSV multi-row headers, blank lines, partially empty hierarchy rows, subject prefixes, and special root labels.

They are mandatory for Stage 00 and Stage 01.

---

## 1. Avoid the Pandas MultiIndex trap

Motive CSV files can contain multiple header rows with blank cells and blank lines. Using Pandas MultiIndex headers can create unstable column names such as `Unnamed: X_level_Y` and make filtering unreliable.

Do not use:

```python
pd.read_csv(path, header=[0, 1, 2, 3, 4, 5, 6])
```

Instead:

1. Read the first 20 lines manually.
2. Use the `csv` module or `open().readlines()`.
3. Preserve blank lines.
4. Identify row roles dynamically by content.
5. Build a flat column map.
6. Load numeric data separately using explicit names.

Recommended pattern:

```python
# Pseudocode only
header_lines = read_first_n_lines(path, n=20, preserve_blank=True)
row_roles = detect_header_row_roles(header_lines)
column_map = build_flat_column_map(row_roles)
data = pd.read_csv(path, skiprows=data_start_row, names=flat_column_names)
```

Required report:

```text
outputs/00_csv_structure/header_row_detection.csv
```

---

## 2. Preserve blank lines and absolute line numbers

Motive CSV files may contain completely blank lines inside the header section.

Do not remove blank lines before detecting header row positions.

The parser must preserve:

```text
zero-based line index
one-based line number
raw line content
row role
```

Required report fields:

```text
row_role
zero_based_line_index
one_based_line_number
detected_label
confidence
notes
```

Do not hardcode that a specific row number is blank or that a specific line number always contains Component.

---

## 3. Detect Frame and Time columns robustly

Frame and Time labels may appear only in a lower header row, while upper hierarchy rows may be empty for those columns.

The parser must scan the full header block for:

```text
Frame
Time
Time (Seconds)
Seconds
```

The parser must not require Frame/Time columns to have Type, Name, ID, Parent, or Property labels.

Do not assume Frame and Time are always columns 0 and 1. If they are, report it. If not, report their detected indices.

Required report:

```text
outputs/03_frame_timing/frame_time_column_detection.csv
```

---

## 4. Strip subject prefixes from Name and Parent rows

Motive names may include a subject prefix, for example:

```text
671:Chest
671:LThigh
671:RShin
```

The parser must strip prefixes from both:

```text
Name row
Parent row
```

Canonical mapping examples:

```text
671:Chest  -> Chest
671:LThigh -> LThigh
671:RShin  -> RShin
```

Preserve source values in every report.

Required fields:

```text
source_bone_name
canonical_bone_name
source_parent_name
canonical_parent_name
subject_prefix
```

Do not hardcode `671` or any specific subject ID.

---

## 5. Handle Parent == Root explicitly

The Parent row may contain:

```text
Root
```

This is not a physical bone name. It means the bone has no parent bone in the CSV hierarchy.

The script must not search for a parent bone named `Root`.

Root handling must be explicit:

```text
Parent == Root -> root-level bone / no parent bone
```

For V0:

```text
Do not include root as a relative joint feature unless explicitly configured.
Save root orientation separately only if useful for reports.
```

Do not silently decide that root relative quaternion is identity or global orientation. If root orientation is used, document the choice.

---

## 6. Do not treat the sample CSV as a fixed template

The sample file is an example of Motive structure, not a fixed schema.

Do not hardcode:

```text
row numbers
column numbers
subject ID
number of bones
exact set of bone names
Frame/Time positions
```

Do dynamically detect and report:

```text
metadata
row roles
column categories
frame/time columns
bone names
parent names
quaternion groups
component order
```

---

## 7. Stop early when ambiguity is detected

If the parser cannot safely determine the structure, stop before numerical processing.

Critical ambiguity examples:

```text
Cannot find Type row
Cannot find Name row
Cannot find Parent row
Cannot find Property or Component rows
Cannot detect Frame/Time columns
Cannot verify Rotation Type = Quaternion
Cannot verify Coordinate Space = Global
Cannot group Bone Rotation X/Y/Z/W columns
Cannot build parent-child hierarchy
```

When stopping, write:

```text
outputs/00_csv_structure/report.md
outputs/00_csv_structure/parser_error_report.csv
```

Do not proceed by guessing.

## 8. v5 code references and robust naming heuristics

### Prefix stripping reference

Use a simple method unless the file proves more complex:

```python
canonical_name = source_name.split(':')[-1]
```

Apply this consistently to both the `Name` row and the `Parent` row.

Preserve the original source name in every report.

### SciPy quaternion shape reference

When creating SciPy rotations, ensure that the quaternion array has shape:

```text
(n_frames, 4)
```

and is ordered as:

```text
[x, y, z, w]
```

Reference:

```python
from scipy.spatial.transform import Rotation as R
rot = R.from_quat(quat_array_xyzw)
```

### Finger/distal-bone heuristic reference

Do not hardcode a single fixed finger list. Use transparent keyword-based classification, then stop for user validation.

Possible distal keywords:

```text
Thumb
Index
Middle
Ring
Pinky
Finger
```

Possible endpoint keywords that require caution:

```text
Hand
Toe
```

`Hand` should usually remain in the body set. Finger segments distal to the hand should usually be excluded in V0.

`Toe` may be included or excluded depending on the chosen body feature set; report the choice explicitly.
