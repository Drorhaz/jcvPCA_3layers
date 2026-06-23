# Stage 05 assumptions and limitations

## Purpose

Enforce temporal sign continuity on global Bone Rotation quaternions before relative-rotation computation.

## Algorithm

- Read quaternions in SciPy order `[x, y, z, w]`.
- For each frame `t > 0`, if `dot(q[t], q_corrected[t-1]) < 0`, multiply `q[t]` by -1.
- Continue using corrected quaternions as the reference for subsequent frames.

## Output format

Primary deliverable: long-format table in `global_quaternions_sign_continuous.parquet` with columns:
`frame`, `time`, `source_bone_name`, `canonical_bone_name`, `qx`, `qy`, `qz`, `qw`, `flip_applied`.
A CSV mirror is also written for inspection; parquet is the primary artifact for downstream stages due to file size.

## Validation

- Post-correction consecutive dot products must be >= -1e-12.

## Explicit limitations

- Stage 05 corrects global quaternion signs only; it does not change represented rotations.
- Stage 05 does not interpolate missing data or repair failed Stage 04 QC data.
- Stage 05 does not perform anatomical validation.
- Stage 05 does not compute relative rotations.
- Stage 05 does not convert to rotation vectors or filter.
- Stage 05 does not make Layer 3 features ready.
- No quaternion normalization is applied; Stage 04-passed norms are preserved.
