# Stage 03 assumptions and limitations

## Purpose

Structural timing validation of Frame and Time columns before any time-dependent quaternion processing.

## Thresholds (provisional, conservative)

- Fail if Frame or Time column is missing or has unparseable rows.
- Fail if Frame is not strictly monotonic increasing.
- Fail if Time has non-positive dt intervals.
- Warning if inferred sampling rate differs from metadata by more than 0.5%.
- Warning if frame index gaps exist (missing indices between first and last frame).
- Warning if max dt > 1.5 × median dt.
- Warning if min positive dt < 0.5 × median dt.
- Warning if duplicate frame indices are present.

## Explicit limitations

- This stage validates Frame and Time column structure only.
- No quaternion norm QC, gap repair, sign continuity, relative rotations, rotation vectors, filtering, or Layer 3 processing is performed.
- Missing frame indices are reported but not interpolated or repaired.
- Sampling rate is inferred from median positive dt; irregular intervals are flagged only.
- Joint sets are not frozen; this stage does not validate bone or joint selection.
