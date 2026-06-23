# Parent–child mapping trust report

Documentation-only trust summary for 671 Part 1 parent→child relative links. This report does **not** freeze final Layer 3 features.

## Confirmed Motive skeleton templates

| Session | Template | Hip/top segment bone |
|---------|----------|----------------------|
| T1, T2 | Core + Passive Fingers (54) | `671` |
| T3 | Biomech (57) | `T3_671` |

Templates differ mainly in trunk/spine/neck topology. Cross-template final feature selection remains deferred until post–Layer 2 / pre–Layer 3.

## Terminology for `671` / `T3_671`

- **`671`:** asset-name-labeled Motive hip/top skeleton segment (`671`); Motive documents this as the skeleton hip; export naming may follow Asset Hip Name.
- **`T3_671`:** asset-name-labeled Motive hip/top skeleton segment (`T3_671`); Motive documents this as the skeleton hip; export naming may follow Asset Hip Name.
- Reports do **not** call these segments simply `Pelvis` unless noting that Motive equates the hip/top segment with the skeleton hip and naming may follow the asset.

## Trusted mapping categories

### Skipped (non-computable)

- `671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv` J001 `Root→671`: CSV virtual parent `Root` has no global quaternion; `Root→671` is non-computable and skipped in Stage 06
- `671_T1_P1_R2_Take 2026-01-06 03.57.12 PM_003.csv` J001 `Root→671`: CSV virtual parent `Root` has no global quaternion; `Root→671` is non-computable and skipped in Stage 06
- `671_T2_P1_R1_Take 2026-01-15 04.35.25 PM_005.csv` J001 `Root→671`: CSV virtual parent `Root` has no global quaternion; `Root→671` is non-computable and skipped in Stage 06
- `671_T2_P1_R2_Take 2026-01-15 04.35.25 PM_009.csv` J001 `Root→671`: CSV virtual parent `Root` has no global quaternion; `Root→671` is non-computable and skipped in Stage 06
- `671_T3_P1_R1_Take 2026-02-03 08.05.01 PM_000.csv` J055 `Root→T3_671`: CSV virtual parent `Root` has no global quaternion; `Root→T3_671` is non-computable and skipped in Stage 06
- `671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv` J055 `Root→T3_671`: CSV virtual parent `Root` has no global quaternion; `Root→T3_671` is non-computable and skipped in Stage 06

### Core candidates (pre–Stage 07 gate)

- Total core candidate link rows: **96**
- Hip/top-segment-to-thigh rows: **12** (`671→LThigh`, `671→RThigh`, `T3_671→LThigh`, `T3_671→RThigh`)
- All core candidates passed reconstruction and relative sign-continuity in Stage 06.

### Review / provisional (not final analysis features)

- Trunk/spine link rows: **20** (e.g. hip/top segment → abdomen/chest)
- These links are documented but **not** promoted to final analysis features.

### Excluded (distal finger / toe)

- Finger and toe chains remain excluded from the likely V0 analysis set per D006.

## Final feature selection

Final analysis feature selection remains **deferred** until after Layer 2 validation and before Layer 3. See `docs/FEATURE_SELECTION_BOUNDARY.md` and D010 in `docs/DECISION_LOG.md`.
