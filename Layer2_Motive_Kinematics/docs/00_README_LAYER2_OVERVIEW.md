# Layer 2 Motive CSV Quaternion Pipeline — Agent Implementation Overview

## Purpose

Implement **Layer 2 only** of the Motive / OptiTrack kinematic processing pipeline.

The purpose of this layer is to transform Motive-solved skeleton **global bone quaternions** from a mixed Motive CSV export into **filtered parent-child relative joint rotation-vector features**.

The primary final outputs are:

```text
relative_rotation_vectors_filtered.parquet
relative_rotation_vectors_filtered.csv
```

These outputs will later be used by Layer 3 for PCA / JcvPCA-style coordination analysis. Do **not** implement Layer 3 in this task.

---

## Layer 2 in one sentence

Layer 2 converts Motive global bone orientations into filtered tangent-space joint-relative rotation features, with full parser audit reports and diagnostic plots at every stage.

---

## What this script must do

The script must implement this pipeline:

```text
Motive mixed CSV
→ CSV structure audit
→ bone rotation column discovery
→ quaternion convention detection
→ frame/time validation
→ missing/invalid quaternion report
→ quaternion normalization
→ bone-level sign-continuity correction
→ parent-child joint mapping
→ global bone quaternion to relative joint quaternion
→ relative quaternion validation
→ relative quaternion sign-continuity correction (Stage 06, before log-map)
→ SO(3) log-map to rotation vectors
→ rotation-vector jump checks
→ Butterworth low-pass filtering in tangent space
→ filtered relative rotation-vector feature matrix
```

The central mathematical operation is:

```text
q_joint(t) = inverse(q_parent_global(t)) * q_child_global(t)
```

where `q_parent_global` and `q_child_global` are Motive global bone quaternions.

---

## What this script must not do

Do not implement:

```text
PCA
JcvPCA
JRW
A/B comparison
coordination analysis
statistical inference
machine-learning analysis
video rendering
interactive dashboard
```

Those belong to later layers or optional diagnostic branches.

---

## Required scientific framing

The output should be described as:

```text
filtered parent-child relative joint rotation-vector features derived from Motive-solved global bone quaternions
```

It should not be described as:

```text
validated anatomical joint angles
raw marker-derived joint angles
final JcvPCA results
```

Important limitation to preserve in reports:

> These features are Motive-derived skeleton kinematic features. They are not independently reconstructed anatomical joint angles.

---

## Required implementation philosophy

Keep the implementation:

```text
simple
modular
inspectable
stage-based
report-driven
fail-loudly when ambiguous
```

Avoid:

```text
over-engineering
large class hierarchies
hidden assumptions
silent guessing
hardcoded sample-specific row numbers
hardcoded subject IDs
spaghetti scripts
```

The agent must stop after every major stage and ask the user to validate the reports before continuing.

---

## Required file set

Use all files in this specification:

```text
00_README_LAYER2_OVERVIEW.md
01_MOTIVE_CSV_STRUCTURE_AND_PARSER_REQUIREMENTS.md
02_LAYER2_STAGE_BY_STAGE_IMPLEMENTATION_SPEC.md
03_OUTPUT_FOLDER_AND_REPORTING_CONTRACT.md
04_AGENT_STOP_AND_VALIDATE_PROTOCOL.md
05_CODEX_COMPOSER_PROMPT.md
06_IMPLEMENTATION_GUARDRAILS_AND_DEPENDENCIES.md
07_PARSER_ROBUSTNESS_REQUIREMENTS.md
```

Start by reading this overview, then read the guardrails and parser requirements before writing code.

## v5 safety additions

This version adds several implementation-critical safeguards:

- Missing, NaN, infinite, or zero-norm quaternions must not pass silently into `sosfiltfilt`.
- Small gaps may be repaired only with an explicitly reported mitigation strategy; large gaps must stop the pipeline before filtering.
- Quaternion multiplication must use `scipy.spatial.transform.Rotation`, not raw NumPy element-wise multiplication.
- Sign-continuity correction should be implemented efficiently with NumPy-based operations, not slow deeply nested Python loops.
- Parent-child hierarchy computation should use flat dictionaries or tables, not an object-oriented skeleton tree.
- Finger/distal-bone exclusion should use transparent keyword rules and must be validated by the user.
- Stage 06 must include a reconstruction test: `parent_global * joint_relative ≈ child_global`.
- Stage 08 filter diagnostics must include a zoomed 2-second high-movement window, not only full-duration plots.
