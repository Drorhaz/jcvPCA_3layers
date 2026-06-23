# Prompt for Composer 2.5 / Codex

You are implementing **Layer 2 only** of a Motive / OptiTrack kinematic processing pipeline.

Read all specification files before writing code:

```text
00_README_LAYER2_OVERVIEW.md
01_MOTIVE_CSV_STRUCTURE_AND_PARSER_REQUIREMENTS.md
02_LAYER2_STAGE_BY_STAGE_IMPLEMENTATION_SPEC.md
03_OUTPUT_FOLDER_AND_REPORTING_CONTRACT.md
04_AGENT_STOP_AND_VALIDATE_PROTOCOL.md
06_IMPLEMENTATION_GUARDRAILS_AND_DEPENDENCIES.md
07_PARSER_ROBUSTNESS_REQUIREMENTS.md
```

## Main task

Build a simple, robust, stage-based Python script that parses Motive solved-skeleton CSV files containing global bone quaternions and produces filtered parent-child relative joint rotation-vector features.

The final required outputs are:

```text
outputs/08_filtering/relative_rotation_vectors_filtered.parquet
outputs/08_filtering/relative_rotation_vectors_filtered.csv
```

Do not implement PCA, JcvPCA, JRW, A/B comparison, or coordination analysis.

---

## Required pipeline

Implement the pipeline in this order:

```text
00 CSV structure audit
01 bone rotation column discovery / joint mapping
02 quaternion convention detection
03 frame/time validation
04 missing/invalid quaternion report + quaternion normalization
05 bone-level sign-continuity correction
06 parent-child relative quaternion computation and validation
07 SO(3) log-map to rotation vectors + jump checks
08 Butterworth low-pass filtering in tangent space
```

The key mathematical operation is:

```text
q_joint(t) = inverse(q_parent_global(t)) * q_child_global(t)
```

Then:

```text
relative joint quaternion
→ scipy Rotation.as_rotvec()
→ Butterworth filtering on rotvec components
```

---

## Parser requirements

Do not use Pandas MultiIndex headers.

Do not use:

```python
pd.read_csv(..., header=[...])
```

Instead:

1. Read the first 20 lines manually using `open()` or `csv`.
2. Preserve blank lines and absolute line numbers.
3. Dynamically detect Type, Name, ID, Parent, Property, Component rows.
4. Detect metadata such as Rotation Type, Coordinate Space, Capture Frame Rate, Export Frame Rate, Total Frames, and Length Units.
5. Build a flat column map.
6. Load numeric data separately using `pd.read_csv(skiprows=data_start_row, names=flat_column_names)`.

Use only:

```text
Type = Bone
Property = Rotation
Components = X, Y, Z, W
```

Ignore Bone Marker and Marker columns for Layer 2 features, but report them in the inventory.

---

## Robustness requirements

Do not hardcode sample-specific assumptions.

Do not hardcode:

```text
row numbers
subject IDs such as 671
number of bones
Frame/Time always being columns 0 and 1
specific bone prefix strings
```

Do dynamically detect:

```text
header rows
metadata values
frame/time columns
quaternion component groups
subject prefixes
canonical names
parent-child hierarchy
```

Strip subject prefixes from both Name and Parent rows, while preserving original source names.

Handle `Parent == Root` as a special non-bone parent. Do not search for a physical bone named Root.

---

## Stop-and-validate protocol

Do not run the entire pipeline in one pass.

After each stage:

1. Write reports and plots.
2. Summarize what was found.
3. List assumptions and warnings.
4. Stop and ask the user to validate before proceeding.

If a critical ambiguity occurs, stop immediately and write an error report.

---

## Dependencies

Use required dependencies:

```text
pandas
numpy
scipy
matplotlib
pyarrow
```

Use:

```text
scipy.spatial.transform.Rotation
scipy.signal.sosfiltfilt
```

Optional dependencies may be used only if they serve a specific Layer 2 diagnostic output and do not expand the scope:

```text
plotly: optional HTML diagnostics only
seaborn: optional heatmaps only
scikit-learn: not needed for Layer 2 V0
opencv: not needed unless future video/image diagnostics are explicitly requested
pyyaml: optional simple config only
```

Keep the implementation simple. Avoid over-engineering, GUI tools, dashboards, large class hierarchies, and hidden assumptions.

---

## Expected code style

Prefer:

```text
one main CLI script
small helper functions
clear stage functions
explicit output paths
plain reports
simple plots
```

Avoid:

```text
complex class systems
plugin frameworks
machine-learning abstractions
silent fallbacks
magic guessing
```

Suggested CLI:

```bash
python layer2_motive_quaternion_pipeline.py \
  --input path/to/motive.csv \
  --output-dir outputs/layer2_run \
  --cutoff-hz 10 \
  --filter-order 4 \
  --stage 00
```

Optionally support running a single stage at a time:

```bash
--stage 00
--stage 01
--stage 02
...
--stage 08
```

The implementation should save intermediate artifacts so later stages can resume after user validation.

## v5 additional mandatory requirements

In addition to the files above, obey these safety rules:

1. Do not use Pandas MultiIndex headers for parsing Motive CSV files.
2. Do not pass NaNs, infinite values, or zero-norm quaternions into filtering.
3. If gaps are found, report them. Small gaps up to 5 frames may be repaired only with explicit logging; larger gaps must stop the pipeline before filtering.
4. Use SciPy `Rotation` objects for quaternion multiplication:

```python
r_joint = r_parent.inv() * r_child
```

5. Do not multiply raw quaternion arrays element-wise.
6. Implement sign-continuity efficiently, preferably with NumPy-based operations over frames.
7. Do not build object-oriented skeleton trees; use flat dictionaries/tables for parent-child mappings.
8. Use simple prefix stripping such as `source_name.split(':')[-1]`, while preserving source names in reports.
9. `Rotation.from_quat()` must receive arrays shaped `(n_frames, 4)` in `[x, y, z, w]` order.
10. For relative quaternion validation, run the reconstruction test:

```text
q_parent_global * q_joint_relative ≈ q_child_global
```

11. For filtering validation, generate both a full-duration plot and a mandatory zoomed 2-second high-movement before/after plot.
12. For finger/distal-bone exclusion, use transparent keyword heuristics and ask the user to validate the proposed split before continuing.
