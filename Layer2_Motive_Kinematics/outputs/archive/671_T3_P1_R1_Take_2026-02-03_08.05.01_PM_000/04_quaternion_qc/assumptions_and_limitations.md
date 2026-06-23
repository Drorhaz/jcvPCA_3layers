# Stage 04 assumptions and limitations

## Purpose

Numeric quaternion QC on global Bone Rotation XYZW groups before any sign-continuity correction or relative-rotation computation.

## Thresholds (provisional, conservative)

- Expected unit norm: 1.0
- Pass if max abs norm error <= 0.001 and no missing/non-finite/zero-norm rows.
- Warning if max abs norm error > 0.001 and <= 0.01, or isolated invalid gaps of 1–5 frames.
- Fail if any zero-norm or near-zero-norm quaternion (near-zero threshold 1e-08).
- Fail if any infinite quaternion component exists.
- Fail if any contiguous invalid gap exceeds 5 frames.
- Fail if complete XYZW percent < 99.0%.

## Spec note

The v5 Stage 04 spec also lists normalization, mitigation logs, and optional interpolation. This implementation follows the approved Stage 04 QC-only scope: detect/report only; no repair.

## Explicit limitations

- Stage 04 validates numeric quaternion quality only.
- Stage 04 does not validate anatomical correctness.
- Stage 04 does not perform sign-continuity.
- Stage 04 does not compute relative rotations.
- Stage 04 does not filter.
- Stage 04 does not make Layer 3 features ready.
- No quaternion normalization, interpolation, or silent repair is performed in Stage 04.
- v5 spec Stage 04 also describes normalization/mitigation outputs; this milestone implements QC/reporting only per approved plan.
