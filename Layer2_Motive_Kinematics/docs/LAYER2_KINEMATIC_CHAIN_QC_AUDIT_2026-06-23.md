# Layer 2 Kinematic Chain / QC / Filtering / Jump Detection Audit

Audit date: 2026-06-23  
Audited repository: `/Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project`  
Primary scope: `Layer2_Motive_Kinematics/`  
Context-only scope: `Layer1_motive_qc/`, `Layer2.5_Segmentation/`, `Layer3_JcvPCA/`

This report is an audit only. No Layer 2 source code, thresholds, schemas, or filters were changed. Current-code re-runs were produced under `Layer2_Motive_Kinematics/outputs/audit_rerun_*` to verify behavior on all available participant 671 files.

## 1. Executive verdict

**Overall verdict: Layer 2 kinematic derivation chain is _usable with caution_.**

The core scientific derivation is technically coherent:

```text
Motive global bone quaternions, XYZW
  -> structural parsing and component-order validation
  -> quaternion norm / missingness QC
  -> per-bone global sign-continuity correction
  -> native skeleton parent-child mapping
  -> q_relative = inverse(q_parent_global) * q_child_global
  -> relative-quaternion reconstruction validation
  -> relative sign-continuity correction
  -> SciPy log-map to rx/ry/rz rotation vectors, radians
  -> Stage 07 jump / branch-cut diagnostics
  -> Stage 08 Butterworth zero-phase filtering of relative rotvec components
  -> native filtered and analysis-clean filtered outputs
```

The final Stage 08 long-table columns `rx_filtered_analysis`, `ry_filtered_analysis`, and `rz_filtered_analysis` are filtered parent-child relative rotation-vector components, not marker positions, Euler angles, or global quaternion components.

The main cautions are:

1. **Jump thresholds are absolute, global, and not yet validated for Gaga movement.** Current defaults are 0.5 rad warning and 1.0 rad fail per frame-to-frame 3D rotvec jump.
2. **Jump detection is per-link and frame-local, but not axis-local.** A jump masks all three axes of that link within ±30 frames.
3. **Layer 2 is native-skeleton, not Layer 3-ready across template changes.** T1/T2 and T3 participant 671 files use different skeleton templates; T3 adds spine/neck segments and has different link names/order.
4. **Archived T3_R1 output was stale for `stage08_policy`.** Archived output incorrectly showed three `block_filter` core links. A current-code re-run corrected these to `allow_filter_with_warning`.
5. **Filter-failure detection is incomplete.** The code handles NaNs, short finite segments, jump-context masking, and branch-cut-context masking, but does not robustly test abnormal filter response, large pre/post differences, edge artifacts, or constant/near-constant output features.

Participant 671 outputs are **usable with caution for Layer 2.5** and **not directly ready for multi-timepoint Layer 3 JcvPCA until a post-Layer-2 feature-selection / harmonization manifest is frozen**.

## 2. Files and code inspected

Core Layer 2 source inspected:

- `src/layer2_motive/parsing.py`
- `src/layer2_motive/quaternions.py`
- `src/layer2_motive/quaternion_qc.py`
- `src/layer2_motive/quaternion_continuity.py`
- `src/layer2_motive/hierarchy.py`
- `src/layer2_motive/pre_stage07_gate.py`
- `src/layer2_motive/relative_rotation.py`
- `src/layer2_motive/rotvec.py`
- `src/layer2_motive/filtering.py`
- `src/layer2_motive/qc_propagation.py`
- `src/layer2_motive/export_layer2.py`
- `src/layer2_motive/stages/stage07.py`
- `src/layer2_motive/stages/stage08.py`

Key docs/config inspected:

- `docs/00_README_LAYER2_OVERVIEW.md`
- `docs/FEATURE_SELECTION_BOUNDARY.md`
- `docs/DECISION_LOG.md`
- `configs/default_layer2_config.yaml`

Tests inspected and executed:

- 19 test files under `Layer2_Motive_Kinematics/tests/`
- Test result from current environment: **110 passed, 1 skipped**

Context inspected:

- `Layer2.5_Segmentation/` notebooks and output manifests
- `Layer3_JcvPCA/` sample validation report and master-plan docs
- Participant 671 Layer 2 archived and current-code re-run outputs

## 3. Layer 2 architecture and run path

Plain-language architecture:

1. Layer 2 reads Motive mixed CSV files containing frame/time metadata and bone rotation quaternion columns.
2. It parses the Motive headers and discovers bone rotation groups.
3. It validates component order and constructability.
4. It checks numeric quaternion quality per bone.
5. It applies per-bone quaternion sign-continuity correction.
6. It discovers or reports a native parent-child skeleton map.
7. It computes relative parent-child quaternions.
8. It validates reconstruction: `q_parent * q_relative ≈ q_child`.
9. It converts relative quaternions to rotation vectors.
10. It detects near-pi branch-cut risk and large frame-to-frame rotvec jumps.
11. It filters rotvec components.
12. It exports native filtered values and analysis-clean values with per-row flags.

Text flow diagram:

```text
input Motive CSV
  -> Stage 00 CSV/header structure
  -> Stage 01 bone inventory + native parent-child candidate map
  -> Stage 02 quaternion component-order / SciPy constructability check
  -> Stage 03 frame/time validation
  -> Stage 04 quaternion QC: missingness, finite values, norm checks, invalid gaps
  -> Stage 05 global per-bone quaternion sign-continuity correction
  -> Stage 06 parent-child relative quaternion computation and reconstruction validation
  -> pre-Stage 07 core/review/excluded gate
  -> Stage 07 relative quaternion -> rotation vector, branch-cut and jump diagnostics
  -> Stage 08 Butterworth filtering of rx/ry/rz relative rotvec components
  -> Stage 08 native filtered + analysis-clean masked output
  -> Layer 2.5 window review / JcvPCA matrix export
  -> Layer 3 JcvPCA
```

Important output categories:

- Human QC: reports, manifests, jump reports, branch-cut reports, filtering summaries.
- Downstream computation: `filtered_relative_rotation_vectors.parquet` and later Layer 2.5 window matrices.

## 4. Input/output contract

Input:

- Motive mixed CSV with `Frame`, `Time (Seconds)`, and bone rotation quaternion columns.
- Participant 671 inputs were found in `Layer2_Motive_Kinematics/data/671/`.

Primary Stage 08 output:

- `08_filtered_rotvecs/filtered_relative_rotation_vectors.parquet`
- Long format: one row per frame × link, with identity columns, raw relative rotvecs, filtered native rotvecs, filtered analysis rotvecs, QC policies, and per-row masks.

Important Stage 08 columns observed in current re-runs:

- Identity: `session_id`, `run_label`, `frame`, `time_sec`, `link_id`, `parent_canonical`, `child_canonical`
- Raw relative rotvec: `rx_raw`, `ry_raw`, `rz_raw`
- Native filtered: `rx_filtered_native`, `ry_filtered_native`, `rz_filtered_native`
- Analysis-clean: `rx_filtered_analysis`, `ry_filtered_analysis`, `rz_filtered_analysis`
- Local QC: `stage07_jump_status`, `stage07_jump_magnitude_rad`, `stage08_policy`, `stage08_analysis_eligible`, `stage08_mask_reason`

Layer 2.5 expects the analysis-clean columns. Its output manifest explicitly lists `rx_filtered_analysis`, `ry_filtered_analysis`, `rz_filtered_analysis` as primary rotvec columns.

## 5. Quaternion parsing, convention, and validation

### Parsing and component order

Facts:

- Motive component order is treated as `X,Y,Z,W`.
- SciPy component order is scalar-last `x,y,z,w`.
- The code treats Motive XYZW as directly compatible with SciPy scalar-last ordering.

Relevant implementation:

- `src/layer2_motive/quaternions.py:12-14` imports `MOTIVE_COMPONENT_ORDER` and defines SciPy order.
- `src/layer2_motive/quaternions.py:40-42` checks that Motive labels lowercased equal SciPy order.
- `src/layer2_motive/quaternions.py:54-56` uses `Rotation.from_quat(row)`.
- `src/layer2_motive/parsing.py` identifies bone rotation quaternion roles and the XYZW component labels.

Interpretation:

- This is scientifically reasonable if the Motive export is indeed scalar-last XYZW. That matches the observed code assumption and common Motive/OptiTrack exports.
- A convention mismatch could silently produce plausible-looking but scientifically wrong rotations. The code has component-order constructability tests, but constructability alone cannot distinguish XYZW from WXYZ if both are finite nonzero arrays.
- The stronger protection is reconstruction validation after relative rotation. If all stages reconstruct child globals with machine-level error, the internal convention/order is likely self-consistent. It does not independently prove Motive's external convention without a known calibration pose.

### Quaternion validation

Facts:

- Stage 04 checks finite rows, missing components, zero/near-zero norms, norm errors, and invalid gaps.
- Thresholds are configured in `configs/default_layer2_config.yaml:16-28`.
- Defaults include:
  - expected norm: 1.0
  - pass max abs norm error: `1e-3`
  - warning/fail norm threshold: `1e-2`
  - near-zero threshold: `1e-8`
  - interpolation off by default

Relevant implementation:

- `src/layer2_motive/quaternion_qc.py:19-26` defines norm and completeness thresholds.
- `src/layer2_motive/quaternion_qc.py:278-288` checks finite rows and inf rows.
- `src/layer2_motive/quaternion_qc.py:287-301` computes norms and norm errors.
- `src/layer2_motive/quaternion_qc.py:312-327` creates invalid masks and invalid gaps.
- `src/layer2_motive/quaternion_qc.py:205-212` fails infinite, zero-norm, and near-zero-norm cases.
- `src/layer2_motive/quaternion_qc.py:229-241` distinguishes pass-level and warning/fail norm deviations.

Interpretation:

- The code does **not** silently interpolate or fill before normalization. Config explicitly says gap interpolation is off by default.
- Stage 04 reports norm statistics and invalid rows per bone. That is appropriate.
- The code relies on SciPy `Rotation.from_quat` downstream, which internally normalizes quaternions for rotation construction. There is no separate explicit normalized-quaternion audit column exported for every row. This is acceptable for small norm deviations but should be documented more directly.
- Severe invalid values are caught before the chain proceeds.

## 6. Quaternion sign-continuity correction

Facts:

- Sign-continuity correction is applied per bone before relative rotation.
- The rule is dot-product based: if `dot(q[t], q[t-1]) < 0`, multiply `q[t]` by -1.
- Flip evidence is preserved in per-bone summaries and flip-frame reports.

Relevant implementation:

- `src/layer2_motive/quaternion_continuity.py:50-62` implements `apply_sign_continuity`.
- `src/layer2_motive/quaternion_continuity.py:94-116` returns corrected quats, flip mask, and per-bone result.
- `src/layer2_motive/quaternion_continuity.py:146-152` exports flip frames.
- `configs/default_layer2_config.yaml:30-34` requires global-before-relative and relative-before-logmap sign continuity.

Interpretation:

- This is technically correct for quaternion double-cover ambiguity. It should not confuse true movement with sign flips because `q` and `-q` represent the same orientation; the dot sign is a representation discontinuity, not a physical discontinuity.
- Participant 671 R1 files had large sign-flip counts concentrated in distal finger phalanges. R2 files showed zero global sign flips. This pattern is likely representation/export/finger-tracking instability, not biological movement.
- The correction happens at the right stage: before relative rotation and before filtering/log-map analysis.

## 7. Skeleton / bone / parent-child mapping

Facts:

- Layer 2 uses native file skeleton structure and exports parent-child maps and manifests.
- `Root` is a virtual CSV parent with no quaternion.
- Motive hip/top segments named `671` and `T3_671` are treated as Motive hip/top skeleton segments, not silently renamed to pelvis.
- Finger/toe handling is intentional: fingers and toes are excluded from likely V0 analysis by heuristics, while hands remain included.
- T1/T2 and T3 participant 671 files have different skeleton templates.

Relevant docs:

- `docs/FEATURE_SELECTION_BOUNDARY.md:67-76` documents T1/T2 as Core + Passive Fingers and T3 as Biomech.
- `docs/FEATURE_SELECTION_BOUNDARY.md:92-114` states that skeleton-version mismatch is documented in Layer 2 but harmonization is deferred.
- `docs/DECISION_LOG.md:20-29` documents Motive hip/top and virtual Root policy.
- `docs/DECISION_LOG.md:54-68` documents skeleton-version mismatch policy.

Relevant implementation:

- `src/layer2_motive/pre_stage07_gate.py:14-35` defines core child bones and hip/top segment names.
- `src/layer2_motive/pre_stage07_gate.py:89-96` identifies finger and toe child bones.
- `src/layer2_motive/pre_stage07_gate.py:125-164` classifies root, finger, toe, and core links.
- `src/layer2_motive/pre_stage07_gate.py:201-205` classifies trunk/spine links as provisional.

Interpretation:

- The parent-child map is explicit and exportable.
- It is **not stable across all 671 files** because T3 uses a different skeleton topology. This is not hidden; it is documented. However, it is a major downstream caution.
- `joint_id` / `link_id` are positional identifiers and shift across templates. Cross-session joins must use parent/child canonical names and a frozen feature manifest, not only `J00x`.
- T3 introduces `Neck->Neck2->Head` and `Spine2->Spine3->Spine4->Chest`; T1/T2 have direct `Neck->Head` and `Ab->Chest`. These are not trivially equivalent.

## 8. Parent-child relative quaternion multiplication

Facts:

- The formula is exactly:

```text
q_relative = inverse(q_parent_global) * q_child_global
```

- SciPy `Rotation` composition is used.
- Reconstruction is validated as `q_parent * q_relative ≈ q_child`.

Relevant implementation:

- `src/layer2_motive/relative_rotation.py:21-23` documents multiplication order.
- `src/layer2_motive/relative_rotation.py:126-141` implements `r_parent.inv() * r_child`.
- `src/layer2_motive/relative_rotation.py:155-158` reconstructs child global from parent and relative.
- `src/layer2_motive/relative_rotation.py:30-31` defines reconstruction thresholds.
- `configs/default_layer2_config.yaml:36-40` configures reconstruction pass and warning thresholds.

Interpretation:

- This is the correct parent-to-child relative rotation formula under SciPy's composition convention.
- Reversing multiplication order could produce plausible but wrong axes/signs. The test suite includes a wrong-order negative test and known-rotation checks.
- Relative rotations are computed before filtering. Filtering happens only after log-map conversion to rotvec.
- A parent artifact affects only links using that parent or child; it does not automatically contaminate unrelated links.

## 9. Rotation-vector / log-map conversion

Facts:

- Relative quaternions are converted to rotation vectors with SciPy `Rotation.as_rotvec()`.
- Units are radians.
- Axes are stored as rx, ry, rz.
- Branch-cut risk near π is evaluated.
- Frame-to-frame jumps are evaluated on the 3D rotvec difference norm.

Relevant implementation:

- `src/layer2_motive/rotvec.py:54-60` converts quaternions to rotvecs with SciPy.
- `src/layer2_motive/rotvec.py:68-70` defines jumps as Euclidean norms of consecutive rotvec differences.
- `src/layer2_motive/rotvec.py:87-94` classifies jump status.
- `src/layer2_motive/rotvec.py:208-240` computes near-pi and jump diagnostics.
- `configs/default_layer2_config.yaml:42-49` sets near-pi and jump thresholds.

Interpretation:

- This is appropriate for PCA only if rotvec norms remain away from π and jumps are masked. Participant 671 core rotvec norms stayed below π, but some arm links had jump failures.
- These rx/ry/rz values are not anatomical Euler joint angles. They are relative rotation-vector coordinates in the chosen convention.
- The output is compatible with Layer 2.5 and Layer 3 in representation, but Layer 3 still requires stable feature names/order across compared matrices.

## 10. Filtering logic

Facts:

- Filtering is applied to relative rotation-vector components, not global quaternions, relative quaternions, positions, markers, velocities, or Euler angles.
- The code uses a Butterworth low-pass filter with SciPy `sosfiltfilt`.
- Default cutoff is 10 Hz, order 4, zero-phase via forward/backward filtering.
- Sampling rate is inferred/validated per file; participant 671 was ~120 Hz.
- NaNs are never passed to `sosfiltfilt`; filtering is applied on finite contiguous segments only.
- No interpolation or silent fill is applied.
- Native filtered outputs preserve values even inside jump context; analysis-clean outputs mask those contexts to NaN and mark them in QC columns.

Relevant implementation:

- `src/layer2_motive/filtering.py:12` imports `sosfiltfilt`.
- `src/layer2_motive/filtering.py:52-57` reads cutoff/order/type/context window from config.
- `src/layer2_motive/filtering.py:115-133` filters finite contiguous 1D segments without passing NaNs.
- `src/layer2_motive/filtering.py:136-159` filters the rx/ry/rz component matrix by finite row segments.
- `src/layer2_motive/filtering.py:434-452` writes native filtered, analysis filtered, and mask columns.
- `configs/default_layer2_config.yaml:50-58` defines filter settings.

Interpretation:

- For JcvPCA, the final intended inputs are filtered parent-child relative rotation-vector components.
- Filtering is done on continuous session data before Layer 2.5 segmentation/windowing.
- Local artifacts can be spread by filtering in the native signal, but the code explicitly creates ±30-frame context masks around Stage 07 jump/branch-cut events.
- Filter edge effects are not deeply audited; the code uses SciPy filtfilt padding rules but does not report per-edge distortion metrics.

## 11. Jump detection logic

Facts:

- Jump detection is on relative rotation vectors, before filtering.
- It uses the Euclidean norm of consecutive differences in rx/ry/rz.
- Thresholds are global and absolute:
  - warning: 0.5 rad
  - fail: 1.0 rad
- Detection is per link and per frame transition, not per axis.
- Reports include affected link and first large jump frame.

Relevant implementation:

- `src/layer2_motive/rotvec.py:68-70` computes 3D frame-to-frame rotvec jump magnitude.
- `src/layer2_motive/rotvec.py:87-94` applies warning/fail thresholds.
- `configs/default_layer2_config.yaml:47-48` defines the thresholds.

Interpretation:

- Representation choice is reasonable because it is applied after relative quaternion computation and sign-continuity correction.
- The logic does not distinguish true fast Gaga movement from measurement artifact; it flags unexpectedly large frame-to-frame changes. Human review is still needed.
- Risk of false positives exists for very fast expressive movement, especially wrist/hand/arm links.
- Risk of false negatives exists for subtle drift or lower-amplitude tracking artifacts.
- Because it is per-link and frame-local, it does not contaminate the whole session.

## 12. Filter-failure and artifact logic

Detected / handled:

- NaNs before filtering: finite contiguous segment filtering; no NaNs passed to filter.
- Short finite segments: skipped rather than filtered.
- Stage 07 jump context: ±30 frames masked in analysis-clean output.
- Branch-cut context: ±30 frames masked in analysis-clean output.
- Filter-applied status: `stage08_filter_applied`, `stage08_filter_status`.
- Human reports: filtering summaries, jump-context reports, branch-cut-context reports.

Not sufficiently detected:

- Abnormal filter response.
- Very large pre/post filtering differences.
- Edge artifacts with explicit metrics.
- Constant or near-constant filtered features.
- Cases where filtering smooths a real artifact not caught by Stage 07 jump logic.

Interpretation:

- Current artifact logic is useful and local, but not a complete filter-failure validation system.
- For PCA, the current outputs are safe against NaN/inf in eligible analysis rows, but not fully certified against filter-induced distortions.

## 13. Local vs global flagging analysis

| Artifact type | Session level | Frame level | Joint/link level | Axis level | Window/context level | Downstream usable? |
|---|---:|---:|---:|---:|---:|---|
| Missing values | Yes summary | Yes invalid gaps | Bone/link via propagation | No | Gap intervals | Yes, mostly |
| Invalid quaternion norm | Yes summary | Yes invalid rows/gaps | Bone, then affected links | No | Gap intervals | Yes |
| Zero-norm quaternion | Yes | Yes | Bone/link | No | Gap intervals | Yes |
| NaN quaternion | Yes | Yes | Bone/link | No | Gap intervals | Yes |
| Inf quaternion | Yes | Yes | Bone/link | No | Gap intervals | Yes |
| Quaternion sign discontinuity | Yes | Flip frame | Bone, then link | No | No broad window | Yes |
| Parent-child mapping issue | Yes | Not frame-specific | Link/skeleton | No | No | Yes if manifest used |
| Missing bone/joint | Yes | Not frame-specific | Link/skeleton | No | No | Yes |
| Impossible relative rotation jump | Yes summary | Yes first/event frames | Link | No | ±30 frames | Yes |
| Velocity spike | Layer 1 context, not Layer 2 core | Layer 1 | Marker/region | No | Layer 1 windows | Yes in Layer 2.5 context |
| Filter failure | Partial | Partial | Link | No | Partial | Needs improvement |
| Filter edge effect | Minimal | Not explicit | Link | No | No explicit edge report | Weak |
| Constant feature | Not robust | No | Feature/link possible but not reported | Could be axis if added | No | Weak |
| NaN after filtering | Yes via finite counts | Yes | Link | Component columns | Yes via eligibility | Yes |
| Inf after filtering | Integrity detectable | Yes if audited | Link | Component columns | No special context | Yes |
| Feature-order mismatch | Export/manifest context | No | Feature/link | Axis via names | No | Needs manifest freeze |
| Timebase irregularity | Yes | Yes gap reports | Session-level timing | No | Gap reports | Yes |

Answer to central concern:

- A jump in one link does **not** mask all joints.
- A jump masks that link's all three axes within ±30 frames in `rx/ry/rz_filtered_analysis`.
- Passing core links remained 100% eligible in current-code participant 671 runs even when another core link had a jump failure.

## 14. Existing tests and missing tests

Existing coverage is strong for:

- Quaternion component order.
- Quaternion normalization/QC.
- Zero-norm and NaN/inf handling.
- Sign-continuity correction.
- Relative multiplication order.
- Known simple rotations.
- Rotvec conversion and near-pi cases.
- Filtering with NaNs.
- Jump-context masking.
- QC propagation.
- Export schema basics.
- Frame/time validation.

Executed result:

```text
110 passed, 1 skipped
```

Missing or recommended tests before final production trust:

1. Known external Motive calibration pose proving XYZW convention against a measured physical orientation.
2. Synthetic smooth-but-fast Gaga-like movement to estimate false-positive jump threshold behavior.
3. Synthetic artifact with known local duration to verify ±30-frame context is sufficient but not excessive.
4. Filter pre/post distortion metrics on impulses and high-amplitude but smooth movement.
5. Explicit edge-effect tests near beginning/end of session.
6. Constant / near-constant feature detection.
7. Cross-template feature-manifest tests proving T1/T2/T3 harmonized matrices have identical names/order before Layer 3.
8. Tests that `joint_id` is not used as the only cross-session semantic key.

## 15. Participant 671 files discovered

All available participant 671 input CSVs:

| File | Inferred timepoint/repetition |
|---|---|
| `671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv` | T1 P1 R1 |
| `671_T1_P1_R2_Take 2026-01-06 03.57.12 PM_003.csv` | T1 P1 R2 |
| `671_T2_P1_R1_Take 2026-01-15 04.35.25 PM_005.csv` | T2 P1 R1 |
| `671_T2_P1_R2_Take 2026-01-15 04.35.25 PM_009.csv` | T2 P1 R2 |
| `671_T3_P1_R1_Take 2026-02-03 08.05.01 PM_000.csv` | T3 P1 R1 |
| `671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv` | T3 P1 R2 |

Current-code re-run output folders:

- `outputs/audit_rerun_T1_P1_R1`
- `outputs/audit_rerun_T1_P1_R2`
- `outputs/audit_rerun_T2_P1_R1`
- `outputs/audit_rerun_T2_P1_R2`
- `outputs/audit_rerun_T3_P1_R1`
- `outputs/audit_rerun_T3_P1_R2`

## 16. Participant 671 run results

All six files were run through current Layer 2 code to Stage 08.

| File | Frames | Duration s | FPS | Links | Core links | Core features | Eligible rows | Eligible % | NaN eligible | Inf eligible | All jump fails | Core jump fails | Core jump warnings | Problematic core links |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| T1_R1 | 30604 | 255.0 | 120.0 | 51 | 16 | 48 | 489481 | 32.0 | 0 | 0 | 9 | 1 | 2 | `LFArm->LHand` f16334 Δ=1.47 |
| T1_R2 | 30235 | 251.9 | 120.0 | 51 | 16 | 48 | 483760 | 32.0 | 0 | 0 | 0 | 0 | 0 | none |
| T2_R1 | 30356 | 253.0 | 120.0 | 51 | 16 | 48 | 485574 | 32.0 | 0 | 0 | 6 | 0 | 2 | none |
| T2_R2 | 30479 | 254.0 | 120.0 | 51 | 16 | 48 | 487664 | 32.0 | 0 | 0 | 0 | 0 | 0 | none |
| T3_R1 | 31674 | 263.9 | 120.0 | 55 | 16 | 48 | 506540 | 29.6 | 0 | 0 | 10 | 3 | 0 | `LUArm->LFArm` f18914 Δ=1.33; `LFArm->LHand` f18914 Δ=1.45; `RFArm->RHand` f18914 Δ=1.74 |
| T3_R2 | 31392 | 261.6 | 120.0 | 55 | 16 | 48 | 502211 | 29.6 | 0 | 0 | 0 | 0 | 1 | none |

Notes:

- `Eligible %` is low because the denominator includes all links, including excluded distal links and review/skipped links. Core pass links are fully eligible except local jump-context windows.
- Eligible analysis rows had **zero NaN and zero inf** in `rx_filtered_analysis`, `ry_filtered_analysis`, `rz_filtered_analysis`.
- No current-code run produced `block_filter` for participant 671.

## 17. Fine-grained comparison across 671 files

Feature/link stability:

| File | All links same as T1_R1? | Core links same as T1_R1? | Interpretation |
|---|---:|---:|---|
| T1_R1 | Yes | Yes | Baseline |
| T1_R2 | Yes | Yes | Stable with T1_R1 |
| T2_R1 | Yes | Yes | Stable with T1/T2 template |
| T2_R2 | Yes | Yes | Stable with T1/T2 template |
| T3_R1 | No | No | Biomech template differs |
| T3_R2 | No | No | Biomech template differs |

T3-only links relative to T1/T2:

- `Root->T3_671`
- `T3_671->Ab`
- `T3_671->LThigh`
- `T3_671->RThigh`
- `Ab->Spine2`
- `Spine2->Spine3`
- `Spine3->Spine4`
- `Spine4->Chest`
- `Neck->Neck2`
- `Neck2->Head`

T1/T2-only links absent in T3:

- `Root->671`
- `671->Ab`
- `671->LThigh`
- `671->RThigh`
- `Ab->Chest`
- `Neck->Head`

Important implication:

- T1/T2 vs T3 are not directly Layer 3-comparable until a canonical feature overlap / mapping decision is made and frozen.

## 18. Upper-body vs full-body trustworthiness

Upper-body core links include:

- `Chest->Neck` or T3 `Neck2->Head` / trunk-related replacements depending on template
- `Neck->Head` or `Neck2->Head`
- `Chest->LShoulder`, `LShoulder->LUArm`, `LUArm->LFArm`, `LFArm->LHand`
- `Chest->RShoulder`, `RShoulder->RUArm`, `RUArm->RFArm`, `RFArm->RHand`

Lower-body core links include:

- `671/T3_671->LThigh`, `LThigh->LShin`, `LShin->LFoot`
- `671/T3_671->RThigh`, `RThigh->RShin`, `RShin->RFoot`

Findings for participant 671:

- Upper-body arm/hand links are the main core jump concern.
- Lower-body core links were comparatively stable in jump diagnostics.
- R1 files show more issues than R2 files.
- T3_R1 is the worst current-code file, with three simultaneous core arm jump failures at frame 18914.
- Upper-body-only is not automatically safer if it includes distal arm/hand links; however, it avoids lower-body feature proliferation and may be a reasonable first pilot if jump-context masks are honored.

Recommendation:

- First Layer 3 pilot should use a scientist-approved canonical upper-body subset and should consider excluding or separately reviewing `LFArm->LHand`, `RFArm->RHand`, and possibly forearm links if they repeatedly trigger jumps.

## 19. Problematic joints/links and frame ranges

Core problems from current-code participant 671 runs:

| Run | Link | Artifact type | Frame | Severity rad | Downstream action |
|---|---|---|---:|---:|---|
| T1_R1 | `LFArm->LHand` | Core jump fail | 16334 | 1.474 | Mask ±30 frames for this link; review in notebook |
| T1_R1 | `LUArm->LFArm` | Core jump warning | 16611 | 0.674 | Review; not automatic fail |
| T1_R1 | `RUArm->RFArm` | Core jump warning | 16611 | 0.555 | Review; not automatic fail |
| T2_R1 | `RUArm->RFArm` | Core jump warning | 17307 | 0.719 | Review; not automatic fail |
| T2_R1 | `RFArm->RHand` | Core jump warning | 17307 | 0.702 | Review; not automatic fail |
| T3_R1 | `LUArm->LFArm` | Core jump fail | 18914 | 1.333 | Mask ±30 frames for this link; review in notebook |
| T3_R1 | `LFArm->LHand` | Core jump fail | 18914 | 1.450 | Mask ±30 frames for this link; review in notebook |
| T3_R1 | `RFArm->RHand` | Core jump fail | 18914 | 1.740 | Mask ±30 frames for this link; review in notebook |
| T3_R2 | `LFArm->LHand` | Core jump warning | 8072 | 0.818 | Review; not automatic fail |

Observed locality:

- A jump-fail link masks 61 frames for that link (frame ±30 including event frame).
- Other pass-core links remain 100% eligible.

## 20. Trustworthiness for Layer 2.5 and Layer 3 JcvPCA

Layer 2.5:

- Current outputs are usable with caution.
- Stage 08 provides row-level `stage08_analysis_eligible` and `stage08_mask_reason`.
- Layer 2.5 can preserve local link/frame evidence and create window-level flag logs.

Layer 3:

- Final matrices must have identical feature names/order.
- T1/T2 and T3 native feature sets differ.
- The existing Layer 3 sample report shows feature columns like `J004_Neck_to_Head_rx`, which are unsafe if `J004` shifts across templates or if `Neck->Head` becomes `Neck2->Head`.
- Layer 3 should not combine T1/T2/T3 native outputs without a frozen harmonization manifest.

Per-file conclusion:

| File | Layer 2.5 status | Layer 3 status |
|---|---|---|
| T1_R1 | Usable with caution | Usable only after local jump review and feature manifest freeze |
| T1_R2 | Ready for Layer 2.5 | Usable after feature manifest freeze |
| T2_R1 | Usable with caution | Usable after warning review and feature manifest freeze |
| T2_R2 | Ready for Layer 2.5 | Usable after feature manifest freeze |
| T3_R1 | Usable with caution | Requires investigation / harmonization before cross-timepoint PCA |
| T3_R2 | Usable with caution | Requires harmonization before cross-timepoint PCA |

## 21. Weak points and risks

1. Absolute jump thresholds are marked validation-required and may be too strict for fast Gaga movement.
2. The pipeline flags jumps but cannot classify movement vs measurement artifact.
3. No robust filter distortion / abnormal response audit.
4. No explicit constant/near-constant feature detection in final outputs.
5. No final cross-template feature freeze exists inside Layer 2.
6. `joint_id` instability can silently break downstream joins if users rely on IDs rather than parent/child names plus manifest.
7. Archived outputs can become stale relative to current source; T3_R1 proved this.
8. Rotvec coordinates are representation-dependent and not direct anatomical joint angles.

## 22. Recommended changes, if any

No source changes were made. Recommended changes before relying on Layer 2 for production JcvPCA:

| Issue | Why it matters | Recommended change | Risk of changing | Risk of not changing | Scientific interpretation affected? | User approval required? |
|---|---|---|---|---|---|---|
| Jump thresholds not validated for Gaga | False positives/negatives affect masks | Build calibration notebook using smooth fast Gaga and artifact examples | May relax/alter current QC | Current masks may be too strict/permissive | Yes | Yes |
| No filter distortion audit | PCA may use smoothed artifacts | Add pre/post max-difference, edge, impulse-response, constant-feature diagnostics | More warnings to interpret | Hidden filter artifacts | Yes | Yes |
| Cross-template feature mismatch | Layer 3 requires identical columns | Freeze canonical feature manifest before Layer 3 | May exclude some native features | Invalid comparisons | Yes | Yes |
| `joint_id` instability | Silent cross-session mismatch | Require parent/child + manifest ordering in Layer 2.5/3 exports | Downstream schema changes | Wrong joints compared | Yes | Yes |
| Archived stale outputs | Audit reproducibility risk | Add code version/hash and config hash to output manifests | Minimal | Old outputs mistaken as current | No, but affects trust | Yes |
| Rotvec convention documentation | Prevent misreading as anatomical angles | Add explicit report text: rotvecs are relative log-map coordinates, radians | Minimal | Misinterpretation | Yes | Yes |

## 23. What should be reviewed in Jupyter notebook

Recommended notebook review targets:

1. T1_R1 frame 16334, `LFArm->LHand`.
2. T1_R1 frame 16611, `LUArm->LFArm` and `RUArm->RFArm`.
3. T2_R1 frame 17307, right forearm/hand warnings.
4. T3_R1 frame 18914, simultaneous arm/hand jump failures.
5. T3_R2 frame 8072, `LFArm->LHand` warning.
6. R1 distal finger sign-flip bursts.
7. Compare raw vs native filtered vs analysis-clean filtered for affected links.
8. Confirm whether flagged events are true expressive movement or acquisition artifacts using video/Motive context if available.

## 24. Open questions for the user

1. Should Layer 3 pilot use upper-body only, and if so should wrist/hand links be included?
2. Are there video recordings or Motive visualizations for the jump frames?
3. Should T3 Biomech trunk/neck topology be mapped into T1/T2 topology, or should T3 be analyzed separately?
4. Should jump thresholds be adapted by joint family rather than global?
5. Should the first Layer 3 pilot exclude all jump-warning links or only jump-fail context windows?
6. Should hand links remain in the first pilot, given that failures concentrate in forearm/hand links?

## 25. Final chain-level verdict

| Stage | Verdict | Rationale |
|---|---|---|
| Quaternion parsing | Ready | XYZW -> SciPy scalar-last is explicit and tested; still needs external calibration proof for absolute convention. |
| Quaternion validation | Ready / usable with caution | Good norm/missing/finite QC; explicit normalization audit could be clearer. |
| Sign continuity | Ready | Correct dot-product double-cover correction, per bone/link, before relative/log-map. |
| Parent-child mapping | Usable with caution | Native maps are explicit, but not stable across T1/T2 vs T3. |
| Relative quaternion computation | Ready | Correct `inv(parent) * child`; reconstruction validation supports correctness. |
| Rotvec conversion | Ready / usable with caution | Correct SciPy log-map in radians; branch-cut and jump risks are tracked. |
| Filtering | Usable with caution | Correct target representation and NaN policy; incomplete filter-failure diagnostics. |
| Jump/artifact flagging | Usable with caution | Local per-link/frame masking works; thresholds need scientific validation and not axis-local. |
| Final export schema | Usable with caution | Layer 2.5-compatible long format; Layer 3 requires frozen feature manifest/order. |

Final verdict:

```text
Layer 2 kinematic derivation chain is: usable with caution
Participant 671 outputs are: usable with caution
```

The caution is not that the quaternion math is wrong. The caution is that artifact interpretation, jump thresholds, filtering diagnostics, and cross-template feature harmonization must be reviewed before using these outputs as final JcvPCA inputs.

## Independent auditor observations beyond the requested questions

1. **The strongest scientific evidence is reconstruction, not component constructability.** Component-order constructability alone is weak because wrong quaternion order can still be constructible. The reconstruction test provides much stronger self-consistency, but a known-pose external validation would close the loop.
2. **Layer 2 is doing two jobs that should remain separated:** native kinematic derivation and provisional analysis feature selection. The docs correctly defer final feature selection, but downstream users may still treat `core_candidate` as final. This should be guarded by explicit manifest requirements.
3. **The low eligible-row percentage is easy to misinterpret.** It mostly reflects excluded distal/review links in the denominator, not widespread corruption of core links.
4. **T3_R1 archived output exposed reproducibility risk.** Current code corrected `block_filter` to `allow_filter_with_warning`, but old outputs remained on disk. Future output manifests should include source commit hash, config hash, and package version.
5. **Layer 3 sample feature names include `J00x`, which is risky.** The human-readable parent-child part helps, but the ID prefix can still mislead. Feature identity should be manifest-driven.
6. **Simultaneous arm jump failures are scientifically ambiguous.** A simultaneous left/right or multi-link event can be true movement, tracking artifact, or skeleton/marker reassignment. It cannot be resolved from Layer 2 numeric outputs alone.
7. **Filtering native values inside jump context is useful but dangerous if misused.** Downstream should prefer `*_filtered_analysis` for PCA and only use `*_filtered_native` for inspection.
8. **No z-scoring occurs in Layer 2.** This preserves natural amplitude differences for JcvPCA, but Layer 3 must handle low-variance features deliberately rather than accidentally upweighting them later.
