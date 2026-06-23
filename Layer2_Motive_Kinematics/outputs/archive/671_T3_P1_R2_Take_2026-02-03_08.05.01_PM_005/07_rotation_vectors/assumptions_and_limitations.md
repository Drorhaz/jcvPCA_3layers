# Stage 07 assumptions and limitations

## Purpose

Convert Stage 06 sign-continuous relative quaternions to rotation vectors via the log-map and diagnose branch-cut / frame-to-frame jump risks before filtering.

## Conversion

- Rotation vector conversion: scipy.spatial.transform.Rotation.from_quat([qx, qy, qz, qw]).as_rotvec()
- Output components: `rx`, `ry`, `rz`, `rotvec_norm`
- Compact QC flags propagated into `relative_rotation_vectors.parquet`; full diagnostics remain in stage reports and `rotvec_summary_by_link.csv`.

## Diagnostic thresholds (from config)

- Near-π count statistic: rotvec_norm ≥ 3.04159 rad
- Branch-cut warning: rotvec_norm > 2.98451 rad (0.95 × π)
- Branch-cut fail: rotvec_norm ≥ 3.14159 rad
- Jump warning: frame-to-frame rotvec jump > 0.5 rad
- Jump fail: frame-to-frame rotvec jump > 1.0 rad

## Link groups

- **core_candidate:** trusted diagnostic group; failures block Stage 07/08 authorization.
- **review_provisional:** trunk/spine/root/manual-review links; reported separately.
- **excluded:** distal finger/toe links; warnings documented but non-blocking.

## Explicit limitations

- Stage 07 uses the log-map / rotation-vector representation (SciPy Rotation.as_rotvec).
- Stage 07 performs branch-cut and frame-to-frame jump diagnostics only.
- Stage 07 does not filter.
- Stage 07 does not finalize analysis features.
- Stage 07 does not resolve skeleton-version mismatch.
- Stage 07 does not make Layer 3 ready.
- Core and excluded link diagnostics are interpreted separately.
- Branch-cut/jump diagnostics are required before Stage 08 filtering.
- Provisional joint selection from Stage 01 / pre–Stage 07 gate is preserved but not frozen.
