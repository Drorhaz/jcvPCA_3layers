# Stage 06 assumptions and limitations

## Purpose

Compute parent→child relative joint quaternions from Stage 05 sign-continuous global Bone Rotation quaternions and validate reconstruction.

## Multiplication order (SciPy Rotation)

- Relative quaternion: q_rel = inv(q_parent) * q_child via SciPy Rotation.from_quat(parent).inv() * Rotation.from_quat(child). Reconstruction: q_child ≈ q_parent * q_rel via parent * relative.

## Reconstruction validation thresholds

- **Pass:** max angular error ≤ 1e-05 degrees
- **Warning:** max angular error > 1e-05 and ≤ 0.001 degrees
- **Fail:** max angular error > 0.001 degrees

## Relative quaternion sign continuity

- When raw relative quaternion sequences contain sign discontinuities, Stage 06 applies the same consecutive dot-product correction as Stage 05 (flip q[t] when dot(q[t], q[t-1]) < 0) with explicit logging. This is a documented second-pass sign continuity on relative quaternions, required before Stage 07 log-map.

## Output format

Primary deliverable: long-format `relative_quaternions.parquet` with columns `frame`, `time`, joint identifiers, provisional selection metadata, `qx`, `qy`, `qz`, `qw` (SciPy `[x,y,z,w]` order), and `relative_flip_applied`.
CSV mirror written for inspection; parquet is primary for downstream stages.

## Explicit limitations

- Stage 06 computes native relative quaternions from sign-continuous global quaternions.
- Stage 06 does not finalize analysis features.
- Stage 06 does not resolve skeleton-version mismatch.
- Stage 06 does not convert to rotation vectors.
- Stage 06 does not filter.
- Stage 06 does not make Layer 3 ready.
- Provisional joint selection from Stage 01 is preserved but not frozen.
- Root-anchor links are labeled and excluded from final-analysis status by default.
