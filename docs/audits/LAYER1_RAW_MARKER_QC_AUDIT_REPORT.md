# Layer 1 Raw Marker QC / Gap / Artifact / Swap Audit

**Audit type:** Read-only technical + scientific audit. No code, config, threshold, test, report, output, or data file was modified.
**Auditor scope:** `Layer1_motive_qc/` (primary). `Layer2_Motive_Kinematics/`, `Layer2.5_Segmentation/`, `Layer3_JcvPCA/` read for downstream contract only.
**Subject under deep test:** participant **671** (all 6 raw files).
**Date of audit run:** 2026-06-23. Audit used the **already-present** Layer 1 outputs in `outputs/runs/671_*_20260623_*` plus read-only inspection of the raw CSV headers. No pipeline re-run was performed that overwrote results.
**Code version inspected:** `motive_qc` v0.6.0.

> Convention in this report: *Fact* = verified directly from source/output. *Interpretation* = auditor judgment. They are kept separate.

---

## 1. Executive verdict

Layer 1 (`motive_qc`) is a **well-engineered, genuinely "report-only, do-not-repair" raw marker QC layer** with strong gap detection, gap-safe kinematics, an explicit duplicate-skeleton quarantine mechanism, and a frame-aligned advisory `qc_mask` that joins cleanly to Layer 2/2.5 on `frame`. The core *per-session* logic is careful and largely correct.

**However, for the specific question this audit was commissioned to answer — is Layer 1 trustworthy and sufficient for Layer 2.5 segmentation and Layer 3 JcvPCA, including the known 671 T3 marker-set difference — the verdict is `usable with caution`, with two blocking gaps and several important ones:**

1. **BLOCKING — Marker-set identity is never detected, reported, or exported across sessions.** *Fact:* The 671 T3 files use asset prefix `T3_671:` while T1/T2 use `671:`; the 54 anatomical marker short-names are otherwise **identical** (verified by parsing raw headers). Layer 1 only detects *within-file* competing skeletons (and does so correctly — T2_P1_R2 has a duplicate and 48 markers were quarantined). It performs **no cross-session marker-name comparison**, exports **no marker-set manifest / marker-set id**, and the `layer1_segmentation_notebook_manifest.json` handed to Layer 2.5 contains **no marker list at all**. The T3 difference is currently absorbed only by a **hard-coded regex** in Layer 2.5 (`marker_family.py`: `^(?:T3_)?671[_:]?`). Layer 1 makes the issue invisible to a downstream consumer.

2. **BLOCKING/IMPORTANT — The session-level readiness verdict and the frame/window-level verdict can disagree catastrophically, and the human report shows the optimistic one as the headline.** *Fact:* `671_T3_P1_R2` reports **"Overall QC status: `caution`"** while **28,967 / 31,392 frames (≈92%) are `exclude_or_review`** and **478/524 (≈91%) of 0.5 s windows are `exclude`**, driven by a **103.3 s** continuous gap on a single marker (`T3_671:LThighFront`) plus others. A PI reading the headline would badly under-estimate the problem.

3. **IMPORTANT — `qc_mask` exclusion is a marker *union*: one labeled marker's ≥0.5 s gap marks the entire gap span `exclude` for all markers.** This is the "one bad marker contaminates the window" behavior the audit was asked to check. It is partially mitigated (per-criterion flag columns + `qc_mask_intervals.affected_markers` give downstream the option to be more lenient), but the headline `status` column is global-union and very aggressive.

4. **IMPORTANT — Layer 1 has no automated tests whatsoever** (no `tests/`, no `pytest.ini`/`pyproject`/`conftest`). Layer 2.5 and Layer 3 both have test suites; Layer 1 does not. "Tests pass" cannot be invoked as evidence of correctness because there are none.

5. **IMPORTANT — Marker-level outputs carry the asset prefix (`671:` / `T3_671:`) inconsistently**, so any cross-session "which markers are repeatedly problematic" analysis on Layer 1 outputs will silently fail to match T3 markers to T1/T2 markers.

**Bottom line:** Per-file gap/artifact evidence for 671 is trustworthy enough to *use with caution*. The dataset is **not** safe for *cross-timepoint* (T1 vs T2 vs T3) JcvPCA interpretation on the strength of Layer 1 outputs alone, because Layer 1 neither detects nor advertises that T3 is a re-labelled asset, and `671_T3_P1_R2` is effectively unusable (≈92% excluded) — a fact the headline status hides.

---

## 2. Files and code inspected

### 2.1 Layer 1 source (all read in full)

| File | Role (verified) |
|---|---|
| `motive_qc/parse.py` | L1 parse: header detection, lean column read, marker inventory, validation, session metadata |
| `motive_qc/marker_meta.py` | header-row finding, marker-name parsing, labeled/unlabeled detection, body-region assignment, prefix/canonical parsing |
| `motive_qc/analysis_scope.py` | **single source of truth** for labeled-in-analysis / unlabeled / quarantined partition; within-file competing-skeleton resolution |
| `motive_qc/gaps.py` | L2 gaps: per-marker gap events, severity, marker-quality, coverage readiness verdict, `frame_qc_mask`, unlabeled burden |
| `motive_qc/segments.py` | gap-safe valid-segment iteration, speeds/accel, robust MAD threshold, near-gap test |
| `motive_qc/artifacts.py` | L4: velocity-MAD, single-frame-spike, constant-hold, rigid-body segment-length (swap) screening; event clustering |
| `motive_qc/windows.py` | L3: fixed 0.5 s / 1.0 s window safety scoring from L2 gaps + L4 events |
| `motive_qc/report.py` | L5: analysis frame mask, qc_intervals, markdown report |
| `motive_qc/deliverables.py` | `qc_mask` + `qc_mask_intervals` (criterion-tagged), gaps-over-threshold, artifacts-by-segment, `load_qc_mask` |
| `motive_qc/io.py` | output writing, tier gating, `qc_mask` validation, segmentation manifest, RUN_MANIFEST |
| `motive_qc/output_tiers.py` | essential vs full tier table/plot gating |
| `motive_qc/pipeline.py` | orchestration L1→L2→L4→L3→L5 |
| `motive_qc/batch_metrics.py`, `batch_report.py` (partial), `batch.py`, `batch_plots.py`, `batch_workbook.py` | L6 cross-session aggregation + PI EDA |
| `config.yaml`, `README.md`, `docs/PROJECT_SPEC_MOTIVE_QC.md` (scanned) | thresholds + spec |

### 2.2 Downstream (read for contract only)
- `Layer2.5_Segmentation/src/pre_jvcpca_review/load_layer1.py` — how L2.5 ingests L1.
- `Layer2.5_Segmentation/src/layer2_motive/segmentation/marker_family.py` — marker-name normalization incl. the hard-coded `T3_671` regex.
- `Layer2.5_Segmentation/input/Layer1_QC/QC_671_T1_P1_R1/...` — the exact L1 files L2.5 consumes.

### 2.3 Data + outputs inspected
- Raw headers of all 6 `data/671/671_*.csv` (Name/Type rows only; full files are multi-hundred-MB).
- All 6 fresh runs `outputs/runs/671_{T1..T3}_P1_{R1,R2}_20260623_*` (session summaries, qc_mask, intervals, gaps, artifacts, segment_length_qc, quarantined_markers, manifests, qc_report.md).
- *Fact:* there is **no** `outputs/batch_runs/` directory — the cross-session (Layer 6) package has not been produced/retained, so no cross-session artifact exists to inspect.

---

## 3. Layer 1 architecture and run path

### 3.1 Plain language
Layer 1 reads one raw Motive marker-XYZ CSV (pre-gap-fill, pre-smoothing, pre-skeleton-solve), figures out which columns are real labeled markers vs unlabeled vs solved/rigid-body columns, measures where each marker is missing and for how long, screens for kinematic artifact *candidates* (spikes, implausible velocities, rigid-pair length violations that suggest swaps), scores fixed time windows for PCA/jPCA safety, and writes an advisory **frame-level mask** plus human and machine reports. It does **not** alter the CSV, fill gaps, smooth, or delete frames.

### 3.2 Inputs / outputs (high level)
- **Input:** one Motive CSV under `data/{subject}/` (+ `config.yaml`).
- **Outputs:** per-run folder `outputs/runs/{subject}_{session}_{timestamp}/` with `tables/*.csv`, `plots/*.png`, `qc_report.md`, `qc_report.html`, `qc_reason_codes.md`, `config_used.yaml`, `RUN_MANIFEST.json`, and `layer1_segmentation_notebook_manifest.json` (the Layer 2/2.5 handoff).

### 3.3 Stage → module map (verified, `pipeline.py`)
Execution order is **L1 → L2 → L4 → L3 → L5** (L4 runs before L3 because window safety consumes artifact events).

| Stage | Module / function | Produces |
|---|---|---|
| L1 parse | `parse.run_layer1_parse` | `MotiveSession`, `marker_inventory`, `session_summary` (counts only) |
| L2 gaps | `gaps.run_layer2_gaps` | `gap_events`, `marker_quality_summary`, `gap_summary_by_*`, `unlabeled_marker_summary`, `frame_qc_mask`, `quarantined_markers`, readiness verdict |
| L4 artifacts | `artifacts.run_layer4_artifacts` | `artifact_candidates`, `artifact_events`, `artifact_session_summary`, `segment_length_qc` |
| L3 windows | `windows.run_layer3_windows` | `window_quality_0p5s`, `window_quality_1p0s`, `frame_quality_summary`, `window_quality_summary` |
| L5 report | `report.run_layer5_report` + `deliverables.build_qc_mask` | `qc_mask`, `qc_mask_intervals`, `qc_intervals`, `gaps_over_0p2s/0p5s`, `artifacts_by_segment`, markdown report |
| L6 batch | `batch.py` + `batch_metrics.py` + `batch_report.py` | cross-session `dataset_eda_report.*`, HTML, per-session pointers |

### 3.4 Flow diagram (corrected to match code)
```
raw Motive marker CSV  (data/{subject}/...csv)
  -> read_csv_header / find_header_rows / build_marker_columns      [marker_meta.py]
  -> classify Marker vs rigid/skeleton/quaternion (excluded)        [parse.py]
  -> labeled vs unlabeled (name regex)                              [marker_meta.is_unlabeled_marker]
  -> within-file competing-skeleton + never-solved quarantine       [analysis_scope.compute_marker_analysis_flags]
  -> coord_array, valid_marker_frame (all-XYZ-finite per frame)     [parse.py]
  -> per-marker contiguous gap runs -> gap_events + severities      [gaps.detect_gaps_for_marker]
  -> coverage-based readiness verdict + frame_qc_mask               [gaps.py]
  -> unlabeled burden + bursts                                      [gaps.build_unlabeled_summary]
  -> gap-safe velocity-MAD / single-frame-spike / rigid-pair swap   [artifacts.py + segments.py]
  -> cluster candidates into events                                 [artifacts.cluster_artifact_events]
  -> 0.5s/1.0s window safety (L2 gaps + L4 events)                  [windows.py]
  -> criterion-tagged advisory qc_mask + intervals                 [deliverables.build_qc_mask]
  -> markdown/HTML report + segmentation manifest                   [report.py, io.py]
  -> (Layer 6) cross-session metric aggregation                     [batch*.py]   <-- NO marker-set comparison
```
*Gap vs the prompt's template diagram:* there is **no "summarize marker-set identity" stage** and **no cross-session marker-set summary** — that box does not exist in the code.

### 3.5 Which outputs serve whom (verified)
- **Human QC review:** `qc_report.md`, `qc_report.html`, plots, `qc_reason_codes.md`.
- **Downstream computation / Layer 2.5:** `qc_mask.csv` (PRIMARY, frame join), `qc_mask_intervals.csv`, `layer1_segmentation_notebook_manifest.json`. Confirmed consumed by `Layer2.5_Segmentation/src/pre_jvcpca_review/load_layer1.py` (joins on `frame`).
- **Relevant for Layer 3 interpretation:** indirectly via the windows L2.5 exports; Layer 1 does not feed Layer 3 directly.

### 3.6 Documented assumptions (and the main unstated ones)
*Documented (README/spec/config):* report-only (no repair); fixed 0.5/1.0 s windows; thresholds in config; expressive-movement artifact tuning; finger group excluded; capture/export rate must match.
*Main scientific/technical assumptions (auditor-identified, mostly **unstated**):*
- A marker-frame is "valid" only if **all three** axes are finite (any single missing axis ⇒ marker missing that frame).
- Velocity/MAD thresholds are pooled per session (adaptive), so "normal" is defined by the session's own distribution.
- Rigid-body pairs are auto-bootstrapped by proximity + low coefficient-of-variation; assumes same-side in-group markers form near-rigid pairs.
- **Implicit, and the dangerous one: each file is self-contained; nothing assumes or checks that T1/T2/T3 share a marker set.** There is no explicit "same marker set across sessions" assumption *in code*, but there is also no guard — and the human report's identity block presents only counts, which *look* identical across T1/T3, inviting the reader to assume comparability.

---

## 4. Input/output contract

1. **Raw format expected:** OptiTrack Motive marker-XYZ CSV with the standard multi-row header (metadata row, then `Type`/`Name`/`ID`/`Parent`/`Frame` rows). *Fact:* `read_csv_header` locates the axis row by the literal `Frame` label.
2. **Motive CSV only?** Effectively yes. No other format readers exist. BVH/parquet explicitly out of scope.
3. **Marker names parsed:** `Name` header row; prefix split on `:` (`671:ChestTop`) and a secondary `_`-based split for asset-style names (`T3_671_...`, `FKA-671_...`); `canonical_short_name` derived (`parse_marker_identity`).
4. **X/Y/Z identified:** by the `Frame`/axis header row cells equal to `X`/`Y`/`Z` per marker column; duplicate axes ⇒ `duplicate_axis` (can fail the run).
5. **Unlabeled markers:** regex `^unlabeled(\s|_)*\d*$` on the short name (plus optional config patterns).
6. **Metadata columns:** first metadata row parsed as key/value pairs (`Capture Frame Rate`, `Export Frame Rate`, `Length Units`, etc.).
7. **Output files created:** see §2.3 / §3.2 / "Latest output files" table (§ near end).
8. **Per-file contents:** documented in README and verified against the 671 runs.
9. **Stable across sessions?** *Fact:* schemas are stable and identical across all 6 runs (same columns). Row counts differ as expected.
10. **Documented?** README + spec describe the essential tables and `qc_mask` columns well.
11. **Machine-readable schemas?** Yes (CSV/JSON). But there is **no formal schema file** (no JSON-schema / dataclass contract) — column presence is enforced only inside `io._validate_qc_mask` for `qc_mask`.
12. **Human-readable?** Yes (`qc_report.md/html`).
13. **Identity in report?** Session, input file, Motive version, frame rate, range, duration, units, counts — **yes**. *But:* subject/timepoint/part/repetition are carried as a single `session_id` string (`T3_P1_R2`) parsed from the filename; the report does not separate participant/timepoint/part/rep into discrete fields, and crucially **does not state the asset/marker-set identity** (prefix). 
14. **Frame/time preserved for Layer 2.5?** *Fact:* yes — `qc_mask` has `frame` + `time_s`, validated to match session frames within tolerance (`io._validate_qc_mask`), monotonic, no dups. This is the strongest part of the contract.

---

## 5. Gap detection logic

*Source: `gaps.detect_gaps_for_marker`, `gaps.run_layer2_gaps`, `parse.py` validity.*

1. **Definition of a gap:** a maximal run of consecutive frames where a marker is *not valid*.
2. **Mechanism:** validity = `np.isfinite(coord).all(axis=2)` — i.e. derived from **NaN** coordinates. Blank cells are converted to NaN (`convert_blank_cells_to_nan: true`). *It does not treat zeros or repeated values as missing* (repeated values are handled separately as constant-hold artifacts, currently disabled).
3. **Per marker and per frame:** yes — gaps are per-marker contiguous runs; a separate frame-level missing count is built in `frame_qc_mask` / coverage metrics.
4. **X/Y/Z handled together or separately:** together for validity (all-3-required), but partial-axis cases are *counted and warned* (`partial_axis_invalid_count`, `PARTIAL_AXIS_MISSING`). *Interpretation:* good that partial-axis is surfaced; but a marker with only Z present is treated as fully missing, which is correct for downstream geometry.
5. **Missing if one coordinate missing?** Yes — any missing axis ⇒ marker missing that frame. Reasonable and clearly the safe choice.
6. **Gap start/end frames:** yes (`gap_start_frame`, `gap_end_frame`, plus `prev_valid_frame`/`next_valid_frame` and `touches_start_or_end`).
7. **Durations:** yes, frames and seconds.
8. **Counts per marker:** yes (`n_gaps_total`, `n_gaps_ge_0p025/0p1/0p2/0p5/1p0s`, longest, mean/median).
9. **Counts per frame:** yes via `frame_qc_mask.missing_labeled_count/percent`.
10. **Long vs short distinguished:** yes — severity labels `single_frame/tiny/minor/moderate/large/severe` from config thresholds (0.025/0.1/0.2/0.5/1.0 s).
11. **Isolated vs sustained:** yes — single-frame gaps explicitly labeled; sustained-dropout count uses ≥2.0 s.
12. **Windows scored for gap burden:** yes (`windows.py` overlap seconds, max gap duration).
13. **Too strict?** *Interpretation:* the *gap detection itself* is appropriately strict (NaN-based, exact). It is not over-flagging gaps.
14. **Too permissive?** Two soft spots: (a) it relies entirely on NaN — if Motive ever exported a held/last-known value instead of blank, that would not be a gap (constant-hold detection that would catch it is **disabled** in config); (b) partial-axis frames are counted as missing (good) but there's no separate "axis dropout" gap stream.
15. **Thresholds documented?** Yes, in `config.yaml` and spec.
16. **Scientifically justified?** *Interpretation:* the thresholds (0.2/0.5/1.0 s at 120 Hz = 24/60/120 frames) are reasonable, conventional motion-capture choices, but they are **stated, not derived** — no citation/justification beyond convention. Acceptable for QC.
17. **Local or contaminating?** Gap *events* are fully local (per-marker, per-frame-range). **But** the `qc_mask` status derived from them is a **union across markers** (see §11 / §21) — one marker's long gap turns the whole span to `exclude`.
18. **Can L2.5 flag only affected windows?** Yes — `qc_mask_intervals` carries `affected_markers`, and `gaps_over_0p5s.csv` lists per-marker intervals; window tables carry `worst_gap_marker` and `affected_body_groups`. Frame-level granularity of *which* marker is, however, only at the interval level, not in `qc_mask.csv` itself.
19. **"absent because not in marker set" vs "temporarily lost":** **This distinction does not exist for cross-session marker-set changes.** Within a file the quarantine system handles phantom/never-solved markers (so a phantom skeleton's 100%-missing markers are *not* counted as gaps — verified in T2_P1_R2: 48 quarantined `phantom_skeleton`, 0 gaps assigned). But a marker that is simply *named differently in T3* is not "absent" within T3 (it tracks fine as `T3_671:...`); the problem is purely cross-session and Layer 1 never compares.

**671 T3 specifically:** *Fact:* the T3 files do **not** produce spurious "missing marker" gaps from the marker-set change, because within T3 every marker is present under its `T3_671:` name. So the prompt's worry "T3 marker-set differences incorrectly counted as gaps" is **not** realized — within-file gap counting is clean. The real risk is the inverse: the change is *silent* (no flag at all), not over-counted.

---

## 6. Gap handling versus gap reporting

1. **Fills gaps?** No.
2. **Interpolates?** No.
3. **Smooths through gaps?** No — kinematics are computed *only within valid segments* (`marker_valid_segments`), so gaps are bridged-around, never interpolated.
4. **Removes frames?** No.
5. **Masks frames?** Yes — advisory only (`qc_mask.status` ∈ `use/caution/exclude`; `frame_qc_mask`, window labels).
6. **Reports without modifying raw data?** Yes — this is the central, clearly-honored design principle.
7/8. **Documented either way?** Yes, explicitly and repeatedly (README "Out of scope", deliverables docstring "Nothing here repairs data").
9. **Downstream expected to handle gaps?** Yes — `recommend_remediation` in `batch_metrics.py` literally suggests "interpolate short gaps (0.2-0.5s)", "Butterworth-filter velocity spikes", etc., for Layer 2.
10. **Passed as masks or QC scores?** Both — frame mask + interval table + per-marker summaries.
11. **Risk downstream thinks gaps were repaired?** Low. The naming (`qc_mask`, "advisory", "candidate") and docs are consistent. *Minor risk:* the column `recommended_bvh_action = exclude_from_bvh_analysis` could be read as an instruction rather than advice, but the README is clear.

**Verdict (§6):** This is the strongest, cleanest aspect of Layer 1. Detect-and-report is faithfully implemented.

---

## 7. Marker jump / spike detection

*Source: `artifacts._detect_velocity_acceleration`, `_detect_single_frame_spikes`, `segments.py`.*

1. **Jump definition:** two independent screens — (a) **velocity-MAD**: speed (m/s) exceeds `max(median + σ·MAD, p99.97)` within a valid segment, with local-peak suppression; (b) **single-frame spike**: displacement ≥ `min_jump_distance_m` (0.10 m) followed by return within `return_near_original_tolerance_m` (0.005 m).
2. **Based on:** position displacement → speed (and acceleration, but **acceleration_mad is disabled** in config). Distance-to-neighbor is handled separately as the swap screen, not as a jump.
3. **Per marker?** Yes.
4. **Per frame?** Yes (candidate per frame, then clustered into events).
5. **3D magnitude vs per-axis:** 3D Euclidean displacement magnitude (`np.linalg.norm(diff)`), not per-axis. *Interpretation:* reasonable; per-axis glitches still show up in magnitude.
6. **Thresholds:** `velocity_mad_multiplier: 8.0`, `velocity_percentile_threshold: 99.97`, spike `min_jump_distance_m: 0.10`, `return_near_original_tolerance_m: 0.005`.
7. **Where defined:** `config.yaml → artifacts`.
8. **Global or marker-specific:** the MAD/percentile threshold is computed **pooled over all in-analysis labeled-marker speeds in the session** (one threshold per session), then applied per marker. So it is *session-adaptive, not marker-specific*.
9. **Absolute or adaptive:** adaptive (MAD + percentile), floored by percentile. Good for expressive movement.
10. **Sampling-rate assumptions:** explicit — `dt = 1/effective_frame_rate_hz`; effective rate comes from CSV metadata (export/capture) with mismatch guard.
11. **Estimates or assumes rate?** Reads from metadata, validates capture vs export match and time-column consistency. Solid.
12. **True fast movement vs artifact:** *Interpretation:* the pooled-MAD-with-high-percentile-floor + local-peak rule is a sensible way to avoid flagging genuinely fast Gaga motion. The README documents tuning guidance and per-segment velocity histograms are produced.
13. **Gaga false positives?** *Interpretation:* low risk for the velocity screen given σ=8 and p99.97. The single-frame-spike screen (0.10 m out-and-back in one frame = ~12 m/s) is physically implausible for a real marker, so few false positives.
14. **Small swaps → false negatives?** Yes — a clean L/R swap keeps velocity smooth (no spike); this is exactly why the rigid-body segment screen exists (§8). The velocity screen alone *would* miss swaps; the design acknowledges this.
15. **Events reported with marker/frame/time/severity:** yes (`artifact_events`: marker, body group, method, start/end frame+time, duration, event_class, severity, near_gap, peak_metric_value).
16. **Contamination scope:** an artifact event is **local to its marker and frame range**. In `qc_mask`, a sigma artifact sets that frame to `caution` only (not `exclude`) — appropriately mild.
17. **L2.5 usable:** yes — events carry seconds and markers; windows count artifact events.

**671 evidence (T1_R1):** 272 artifact events; velocity candidates concentrate in `wrist_hand`/`shoulder_upper_arm`. Acceleration candidates = 0 (method disabled). Consistent and plausible.

---

## 8. Marker swap detection

*Source: `artifacts.detect_segment_length_violations`, `_bootstrap_marker_pairs`, `_marker_side`.*

1. **Attempts swap detection?** Yes — via rigid-body **intra-pair distance** violations (a swap distorts anatomy even when velocity stays smooth).
2. **Definition:** for each rigid pair, frame-wise Euclidean distance deviating from the session **median** distance by > `max_segment_length_change_pct` (18%). ≥50% deviation ⇒ `severe`, else `moderate`.
3. **Method used:** distance-to-partner / segment-length plausibility (not trajectory crossing, not velocity reversal). Vectorized, gap-aware (NaN distances ignored via `nanmedian`).
4. **Per pair?** Yes. Pairs come from `config/marker_pair_map.csv` **if present, else auto-bootstrapped**. *Fact:* no `config/marker_pair_map.csv` exists in the repo, so **auto-pairing is always used** for 671.
5. **Candidate pairs reported?** Yes — `segment_length_qc.csv` (pair, markers, median distance, n/pct violating frames, n_events).
6. **Frame ranges reported?** Yes — clustered into `artifact_events` with method `segment_length_violation`, and surfaced in `qc_mask_intervals` as `SEGMENT_SWAP` with `affected_markers`.
7. **Severity reported?** Yes (moderate/severe).
8. **Confirmed vs possible:** All are labeled *candidates* (`recommended_status="manual_review"`). No "confirmed swap" claim. Correct.
9. **Repairs swaps?** No — flag only.
10. **Repair logged?** N/A (no repair).
11. **Clear it doesn't repair?** Yes.
12. **Useful for human QC?** Partially — see false-positive concern below.
13. **Misses swaps in dense upper-body?** *Interpretation:* possible. Auto-pairing keeps only the single most-rigid **same-side, same-body-region** partner per marker (`max_rigid_cv: 0.05`). A genuine L↔R swap (cross-side) is **never paired**, so a pure left/right confusion between symmetric markers would **not** be caught by this screen. Dense regions where the true partner isn't the lowest-CV neighbor can also be mispaired.
14. **False-positives on normal close trajectories?** *Fact, observed in 671_T1_R1:* `wrist_hand` shows **48 `segment_swap` events**, dominated by `RHandIn__RHandOut`. Hand markers are not truly rigid relative to each other during expressive movement, so an 18%-of-median deviation is easily exceeded. *Interpretation:* these are likely **false swap candidates**; the 18% threshold + auto-pairing is too aggressive for hand/forearm pairs.
15. **L2.5 usable?** Yes structurally (events + intervals + `flag_segment_swap` in `qc_mask`), but the false-positive rate in hand regions reduces trust without a curated `marker_pair_map.csv`.

**Net (§8):** The *idea* (rigid-pair distance to catch velocity-invisible swaps) is sound and better than many QC tools. The *implementation* is only superficially reliable for 671 because (a) cross-side swaps are structurally invisible to same-side pairing, and (b) auto-pairing produces clear false positives in non-rigid hand pairs. It should be treated as a **rough screen**, not a swap detector.

---

## 9. Unlabeled-marker burden

*Source: `gaps.build_unlabeled_summary`.*

1. **Detects unlabeled?** Yes.
2. **Identification:** name regex (`^unlabeled...`) ⇒ `is_unlabeled`.
3. **Per-frame counts:** yes (`unlabeled_count` per frame in `unlabeled_frame_counts`, written when `write_unlabeled_frame_counts: true`).
4. **Bursts detected?** Yes — contiguous runs of frames with ≥1 unlabeled marker.
5. **Burst start/end frames:** *Partial.* Burst **count** and **longest burst seconds** are reported; the *summary* table does not enumerate each burst's start/end (the per-frame counts table allows reconstruction, but there is no `unlabeled_bursts` interval table).
6. **Per session/window:** session-level summary yes; **window-level unlabeled burden is not integrated into window scoring** (windows score gaps + artifacts, not unlabeled bursts).
7. **Isolated vs sustained:** longest-burst seconds distinguishes, but no per-burst breakdown.
8. **Could indicate swaps/instability/occlusion?** The summary includes `overlap_with_labeled_gaps` (a useful proxy: unlabeled present while a labeled marker is missing = likely the same marker tracking unlabeled). Good signal, but not turned into a swap hypothesis.
9. **Useful for selected-window QC?** Weak — not fed into window labels or `qc_mask` by default (`flag_unlabeled_present: false`).
10/11. **In human + machine outputs?** Human report §3 yes; machine: `unlabeled_marker_summary` + `unlabeled_frame_counts`. *But* neither is in the **essential** tier export list, so by default the per-session run **does not write** an unlabeled CSV unless tier=full (it is in L2 tables but not in `ESSENTIAL_TABLES`). *Fact:* the 6 671 runs (essential tier) contain no `unlabeled_*.csv` — only the report's §3 summary. The L2.5-consumed folder likewise lacks unlabeled tables.

**671 evidence:** unlabeled tracks range 15→61 across sessions; T3_R2 has 61 unlabeled tracks, 98.1% of frames with ≥1 unlabeled, longest burst 72 s — a strong instability signal that is **reported in the markdown but not exported as a machine table** in essential tier and not used in window scoring.

---

## 10. General artifact candidate detection

*Source: `artifacts.py`.*

1. **Types detected:** velocity-MAD spike; single-frame out-and-back spike; rigid-pair segment-length violation (swap proxy); constant-position-hold and acceleration-MAD exist but are **disabled** in config.
2. **Per marker + frame?** Yes.
3. **Per window?** Summarized into windows (L3) and per body region (`artifacts_by_segment`).
4. **Physically implausible movement?** Partly — via velocity + spike + segment-length.
5. **Extreme velocity?** Yes.
6. **Extreme acceleration?** **Disabled** by default (`acceleration_mad: false`). So acceleration artifacts are not screened in the current config (verified: 671 reports 0 acceleration candidates).
7. **Implausible distances / segment-length change?** Yes (rigid pairs).
8. **Frozen / constant trajectories?** Capability exists (`constant_position_hold`) but **disabled**. So a held/frozen marker would currently **not** be flagged as an artifact (and, since a frozen marker has finite coords, it is also **not** a gap). *Interpretation:* this is a real blind spot if Motive ever emits held values.
9. **Disappear/reappear artifacts:** captured as gaps + edge-effect buffers, plus near-gap velocity is suppressed (`max_frames_after_gap_for_velocity: 0`).
10. **Outlier frames affecting many markers:** **not directly detected** — there is no "system-wide frame" detector that says "frame N is bad across many markers". You could infer it from `frame_qc_mask.missing_labeled_percent`, but multi-marker simultaneous *artifact* spikes are not aggregated into a single system event.
11. **System-wide instability:** only indirectly (coverage %, unlabeled burst). No explicit global-glitch detector.
12. **Categorized by type?** Yes (`method`, `event_class`).
13. **Severity scores?** Yes (minor/moderate/severe by metric ratio).
14. **Thresholds documented?** Yes.
15. **Sufficient for human raw-capture review?** *Interpretation:* mostly yes for spikes/gaps; weaker for swaps (false positives) and frozen markers (off).
16. **Sufficient for L2.5 window flagging?** Yes structurally.

---

## 11. Local vs global flagging analysis

| artifact type | session | window | frame | marker | marker-pair | axis | downstream-usable |
|---|---|---|---|---|---|---|---|
| missing marker sample | ✓ (counts) | ✓ | ✓ (`frame_qc_mask`) | ✓ | – | counted (partial-axis) | ✓ |
| short gap (<0.5s, ≥0.2s) | ✓ | ✓ | ✓ (`flag_gap_0p2`, caution) | ✓ (`gap_events`) | – | no | ✓ |
| long gap (≥0.5s) | ✓ | ✓ | ✓ (`flag_gap_0p5`, **exclude, union**) | ✓ event-level / interval-level | – | no | ✓ but global-union status |
| marker jump / velocity spike | ✓ | ✓ | ✓ (caution) | ✓ | – | no (3D mag) | ✓ |
| acceleration spike | (disabled) | – | – | – | – | – | n/a |
| possible marker swap | ✓ | ✓ | ✓ (caution) | via pair | ✓ (`segment_length_qc`) | no | ✓ (noisy) |
| unlabeled burst | ✓ | ✗ (not in window score) | ✓ (counts, not in mask by default) | track-level | – | no | weak |
| frozen marker | (disabled) | – | – | – | – | – | n/a |
| outlier marker position | via spike/velocity | ✓ | ✓ | ✓ | – | no | ✓ |
| system-wide artifact | ✗ (no detector) | inferable | inferable (missing%) | – | – | – | weak |
| **marker-set mismatch (cross-session)** | **✗** | **✗** | **✗** | **✗** | **✗** | **✗** | **✗ — absent** |
| selected-window artifact burden | ✓ | ✓ | – | – | – | – | ✓ |

Answers:
- **Too broad?** Yes in one specific, high-impact way: the **`qc_mask.status` exclusion is a marker-union** — one in-analysis labeled marker with a ≥0.5 s gap sets every frame in that gap to `exclude` regardless of the other 47 markers. (Demonstrated: 671_T3_R2 ⇒ 92% exclude from essentially one 103 s marker dropout plus a few others.)
- **Too narrow?** Yes in two ways: no cross-session marker-set detection at all; no system-wide multi-marker glitch detector; unlabeled burden not in window scoring.
- **One bad marker contaminates all markers?** *For the headline `status` column, yes.* For the per-criterion flag columns and `qc_mask_intervals.affected_markers`, **no** — locality is preserved there, and `deliverables.load_qc_mask` lets a caller choose which criteria to honor.
- **One bad frame contaminates the whole window?** Window labeling uses overlap thresholds (a 0.5 s window with ≥0.5 s gap overlap ⇒ exclude), so a single sustained gap will exclude its windows — but **windows are independent**, so a bad window does not contaminate good windows. Session is not contaminated by a single bad frame.
- **Enough info for local downstream decisions?** Yes if the consumer reads `qc_mask_intervals` / per-marker tables; **not** if it trusts only `qc_mask.status`.
- **Can L2.5 flag only affected windows vs discarding sessions?** Yes — window tables + intervals support per-window decisions.

---

## 12. Marker-set consistency and participant 671 T3 issue

This is the crux of the audit. Findings are stated as verified facts first.

### 12.1 What the data actually is (verified by parsing raw headers)
| File | asset prefix(es) | # canonical labeled short-names | symmetric diff vs T1_R1 (canonical) |
|---|---|---|---|
| 671_T1_P1_R1 | `671:` | 54 | — |
| 671_T1_P1_R2 | `671:` | 54 | none |
| 671_T2_P1_R1 | `671:` | 54 | none |
| 671_T2_P1_R2 | `671:` **and** `FKA-671_` (duplicate) | 54 (+phantom copy) | none |
| 671_T3_P1_R1 | `T3_671:` | 54 | none |
| 671_T3_P1_R2 | `T3_671:` | 54 | none |

**Key fact:** T3 is **anatomically the same 54-marker set**; only the **asset/skeleton prefix differs** (`671:` → `T3_671:`). So "different marker set" = **different marker-set *identity / naming*, not different anatomy.** This is good news scientifically (windows are comparable after harmonization) but means the difference is *invisible to any count-based check* — `n_labeled_markers = 54`, `n_labeled_markers_in_analysis = 48` are **identical** across T1/T2/T3.

### 12.2 The ten questions
1. **Computes marker list per file?** Yes internally (`marker_inventory` with `marker_name`, `canonical_short_name`, `skeleton_prefix`).
2. **Exports the marker list?** **No** in the default essential tier — `marker_inventory` is **not** in `ESSENTIAL_TABLES` (only full/debug tier). Verified: the 6 671 essential runs contain no `marker_inventory.csv`. The only place a prefixed name *leaks* into essential output is incidental (`session_summary.longest_gap_marker_labeled = T3_671:ChestTop`; `gaps_over_*`/`artifact_events`/`segment_length_qc` marker columns).
3. **Compares marker lists across files?** **No.** No function anywhere compares marker name sets across sessions. The batch aggregator (`batch_metrics`/`batch_report`) aggregates counts/metrics only.
4. **Identifies markers in T1/T2 absent in T3?** **No** (and in this dataset the canonical answer is "none", but Layer 1 cannot state that).
5. **Identifies markers in T3 absent earlier?** **No.**
6. **Distinguishes marker-set differences from within-file gaps?** Within a file, yes (quarantine vs gap). **Across files, there is nothing to distinguish.**
7. **Warns when marker sets differ?** **No cross-session warning exists.** (It does warn on within-file duplicate skeletons — `DUPLICATE_MARKER_SET_DETECTED`/`PHANTOM_SKELETON_QUARANTINED`, confirmed firing on T2_P1_R2 ⇒ 48 quarantined.)
8. **Marker-set manifest for L2.5?** **No.** `layer1_segmentation_notebook_manifest.json` contains `subject_id, session_id, run_key, input_csv, frame_rate_hz, n_frames, frame/time columns, qc_mask paths` — **no marker list, no marker count, no prefix, no marker-set id.**
9. **Shows whether selected windows affected by marker-set diffs?** No (Layer 1 does not know selected windows, and has no marker-set concept across sessions).
10. **Clarifies whether mismatch affects Layer 2 skeleton solving vs only raw QC?** No statement anywhere.

### 12.3 Is the issue visible at all?
Only **accidentally and only to a careful human**: the prefixed marker name appears in `session_summary.longest_gap_marker_labeled` and in marker-level CSVs. Nothing labels it as "this session uses a different asset name." The human `qc_report.md` for T3 shows `Export type detected: consistent_with_marker_xyz`, `Labeled markers: 54` — visually identical to T1 — and never mentions `T3_671`.

### 12.4 Recommendations on where to address it
- **Detection + reporting → Layer 1 (must).** Layer 1 is the only layer that sees every raw file in isolation and already computes `canonical_short_name`/`skeleton_prefix`. It should (a) emit a per-session **marker-set fingerprint** (sorted canonical names + hash + observed prefixes) into the segmentation manifest, and (b) in batch (Layer 6) compare fingerprints across sessions and raise a `MARKER_SET_MISMATCH` warning + a `marker_set_comparison.csv`. **Do not implement now — recommendation only.**
- **Harmonization → Layer 2.5 (already there, but make it explicit/robust).** L2.5 already strips prefixes (`marker_family.normalize_marker_name`, regex `^(?:T3_)?671[_:]?`). Keep harmonization there, but it must be *triggered/validated* by a Layer 1 fingerprint rather than a hard-coded subject-specific regex.
- **Layer 2 skeleton solving:** the prefix change will matter to any solver/join keyed on full marker name; this is a Layer 2 concern but must be *flagged* by Layer 1.
- **Blocker for T3 vs T1/T2 comparison?** **Treat as "must-confirm-harmonization" before cross-timepoint JcvPCA.** The anatomy matches, so it is *not* a hard scientific blocker once harmonized; it **is** a blocker for any pipeline path that joins by full marker name without prefix stripping.

### 12.5 Does the pipeline risk comparing incompatible raw marker sets without warning?
*Fact:* Yes for any consumer that keys on full marker names; *No* for the actual current L2.5 path (which joins QC on `frame` and rebuilds marker families with prefix-stripping). The risk is **latent**: it is "fixed" only by a brittle regex in one downstream module, with **no Layer 1 guard** and **no test** protecting it. A new subject, a new prefix style, or a different consumer would silently break.

---

## 13. Alignment with Layer 2.5 selected-window QC

1. **Frame-level QC flags output?** Yes (`qc_mask.csv`, 1 row/frame, with `flag_*` columns).
2. **Window-level summaries?** Yes (`window_quality_0p5s/1p0s`) — **but these are Layer 1's *own fixed* 0.5/1.0 s bins, not Layer 2.5's selected windows.**
3. **Does L1 know the selected windows?** **No** — Layer 2.5 selects analysis windows later; Layer 1 windows are generic fixed bins. *Fact:* `load_layer1.py` recomputes per-window flag percentages from `qc_mask` over `[frame_start, frame_end]` chosen by L2.5 — i.e. **L2.5 computes its own window QC from L1's frame mask.** This is the right division of labor.
4. **Frame numbers compatible?** Yes — `qc_mask.frame` = Motive export frame; validated monotonic and matching session frames.
5. **Time compatible?** Yes — `time_s` validated within tolerance of Motive `Time (Seconds)`.
6. **Window boundaries traceable to raw QC?** Yes via frame join.
7. **L2.5 can compute gap burden in selected windows?** Yes (`flag_gap_0p2/0p5` per frame).
8. **Artifact burden in windows?** Yes (`flag_artifact_sigma`, `flag_segment_swap`).
9. **Which markers caused window problems?** Only via `qc_mask_intervals.affected_markers` (interval-level) — **`qc_mask.csv` itself does not name the culprit marker per frame.** L2.5 would need to join intervals to attribute per-window blame; achievable but not turnkey.
10. **Can L2.5 report whether a JcvPCA window should be trusted?** Yes, mechanically.
11. **Organized for notebook review?** Yes — predictable folder layout; the L2.5 input folder `Layer1_QC/QC_671_*` mirrors it.
12. **Names/manifest consistent with pipeline?** Mostly. *Concern:* the L2.5-side folders are named `QC_671_T1_P1_R1` while L1 emits `671_T1_P1_R1_{timestamp}`; the timestamped folder name is **not** recorded in any field a consumer can match on except `run_output_dir` (absolute path). There is no stable, timestamp-free `run_key`-named folder, so wiring relies on manual copy/rename (evidenced by the `QC_` prefix in L2.5 input).

**Gap for L2.5:** the single most useful missing artifact is a **consolidated, marker-set-aware, frame-or-window QC file** with participant/timepoint/rep + marker-set id (see §"Consolidated file" below). Today L2.5 must (a) join multiple CSVs, (b) re-derive marker families from raw CSV + DataDescriptions, and (c) trust a hard-coded prefix regex.

---

## 14. Alignment with Layer 3 JcvPCA interpretation

1. **Trace each window back to raw QC?** Yes, transitively (Layer 3 window → L2.5 window → L1 `qc_mask` frames). No direct Layer 1↔Layer 3 link/field exists; it depends on L2.5 carrying provenance.
2. **Know if a Layer 3 result came from a gappy window?** Possible only if L2.5 propagates L1 flags into its export; Layer 1 provides the raw material (`flag_gap_*`).
3. **Know if from a suspected-swap window?** Same — `flag_segment_swap` exists but is noisy (§8).
4. **Know if T1/T2/T3 had comparable raw quality?** *Fact:* **Not from Layer 1 outputs directly.** There is no cross-session quality comparison table retained (no `batch_runs/`), and — critically — no marker-set comparability statement. A user cannot currently tell from Layer 1 that T3 is the same anatomy re-labelled.
5. **Could a JcvPCA difference be capture-quality not movement?** This is a real risk the audit must flag: `671_T3_P1_R2` is ≈92% excluded (one long thigh dropout); if it nonetheless feeds JcvPCA, any T3 "difference" could be an artifact of capture quality, not behavior. Layer 1 surfaces the evidence (intervals) but the **headline session status `caution` actively understates this**.
6. **Concise enough?** Yes (`qc_report.md` is compact).
7. **Detailed enough for debugging?** Yes (intervals, per-marker gaps, segment_length_qc) — at full tier even more.
8. **Organized consistently with L2.5/L3 manifests?** Partially (see §13.12 naming concern).
9. **Recommended QC field to carry forward?** Yes — a **`marker_set_id` / `marker_set_fingerprint`** and a **`session_usability` verdict that reconciles frame-level and session-level** should be propagated into L2.5 → L3 manifests.

---

## 15. Existing tests and missing tests

**Existing:** *Fact:* **none.** No `tests/`, `test_*.py`, `conftest.py`, `pytest.ini`, or `pyproject.toml` under `Layer1_motive_qc/` (the only matching path is a *data* file `archive/..._raw test.csv`). By contrast Layer 2.5 and Layer 3 have `tests/` + `.pytest_cache/`. Layer 1 is the **only** layer with zero tests, despite being the QC foundation.

**Recommended tests (do not implement — propose only).** For each checklist item:
1. **Marker column parsing** — synthetic Motive header with mixed Marker/RigidBody/Bone/Quaternion columns ⇒ only Markers in inventory; assert `excluded_non_marker_column_count`.
2. **Labeled vs unlabeled** — names `671:ChestTop`, `Unlabeled 2041`, `T3_671:HeadTop`, `FKA-671_Back` ⇒ correct `is_labeled/is_unlabeled` and `canonical_short_name`.
3. **Gap detection** — known NaN pattern ⇒ exact gap start/end/duration; boundary gaps (`touches_start_or_end`); single-frame gaps on/off.
4. **Short vs long classification** — durations at 0.199/0.2/0.5/1.0 s at 120 Hz ⇒ correct severity & `n_gaps_ge_*`, including `use_greater_equal_thresholds` edge.
5. **Marker-set comparison (new capability)** — two sessions, identical anatomy different prefix ⇒ assert "same canonical set, different prefix" *(currently impossible — no function exists)*.
6. **671 T3 marker-set difference** — fixture from real headers ⇒ assert a `MARKER_SET_MISMATCH`/fingerprint is produced *(currently fails — no such output)*.
7. **Velocity jump** — injected 12 m/s spike ⇒ flagged; verify near-gap suppression.
8. **Fast-but-legitimate movement** — broad high-velocity Gaga-like segment ⇒ **not** flagged at σ=8/p99.97 (false-positive guard).
9. **Swap candidate** — swap two symmetric markers mid-trajectory ⇒ segment-length violation fires; **and** a same-side non-rigid hand pair with large natural excursion ⇒ assert it is **not** flagged (false-positive guard — currently would fail given observed `RHandIn__RHandOut`).
10. **Frozen marker** — held constant value ⇒ should be flagged (currently disabled ⇒ test documents the gap).
11. **Frame-level QC output** — `qc_mask` row count == frames, monotonic, time alignment (this logic exists in `_validate_qc_mask`; add a unit test around it).
12. **Marker-level QC output** — per-marker missing% denominator excludes quarantined/excluded markers.
13. **Window-level QC output** — window with a ≥0.5 s gap ⇒ `exclude`; clean window ⇒ `use`.
14. **Schema compatibility with L2.5** — assert `qc_mask` columns exactly match what `load_layer1.load_qc_mask` reads; assert manifest keys.
15. **Report generation** — smoke test markdown builds; assert session status is **reconciled** with frame-mask exclude % (would currently expose the T3_R2 contradiction).
16. **Reproducibility** — same input twice ⇒ identical tables (modulo timestamp).

---

## 16. Participant 671 files discovered

*Fact (from `data/671/` and run outputs).* Timepoint/part/rep parsed unambiguously from filename (`{subj}_{T#_P#_R#}_Take ...`).

| # | File | Timepoint | Part/Rep | Capture date |
|---|---|---|---|---|
| 1 | `671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv` | T1 | P1/R1 | 2026-01-06 |
| 2 | `671_T1_P1_R2_Take 2026-01-06 03.57.12 PM_003.csv` | T1 | P1/R2 | 2026-01-06 |
| 3 | `671_T2_P1_R1_Take 2026-01-15 04.35.25 PM_005.csv` | T2 | P1/R1 | 2026-01-15 |
| 4 | `671_T2_P1_R2_Take 2026-01-15 04.35.25 PM_009.csv` | T2 | P1/R2 | 2026-01-15 |
| 5 | `671_T3_P1_R1_Take 2026-02-03 08.05.01 PM_000.csv` | T3 | P1/R1 | 2026-02-03 |
| 6 | `671_T3_P1_R2_Take 2026-02-03 08.05.01 PM_005.csv` | T3 | P1/R2 | 2026-02-03 |

(There are also flat copies directly under `data/` and a `data/archive/..._raw test.csv` excluded by `exclude_globs`.) No timepoint/rep uncertainty.

---

## 17. Participant 671 Layer 1 run results

*Fact — from the `20260623_*` runs (essential tier). Frame rate = 120 Hz, units = Meters, Motive Body 3.4.0.2 for all.*

| Field | T1_R1 | T1_R2 | T2_R1 | T2_R2 | T3_R1 | T3_R2 |
|---|---|---|---|---|---|---|
| frames | 30604 | 30235 | 30356 | 30479 | 31674 | 31392 |
| duration (s) | 255.0 | 252.0 | 253.0 | 254.0 | 263.9 | 261.6 |
| labeled markers | 54 | 54 | 54 | **108** | 54 | 54 |
| in-analysis | 48 | 48 | 48 | 48 | 48 | 48 |
| quarantined | 0 | 0 | 0 | **48 (phantom)** | 0 | 0 |
| unlabeled tracks | 48 | 33 | 15 | 23 | 20 | **61** |
| missing% (labeled) | 0.304 | 0.357 | 0.064 | 0.161 | 0.165 | **2.090** |
| gaps total (labeled) | 279 | 222 | 72 | 128 | 128 | 114 |
| gaps ≥0.2 s | 47 | 51 | 5 | 21 | 28 | 43 |
| gaps ≥0.5 s | 11 | 13 | 2 | 9 | 5 | 18 |
| gaps ≥1.0 s | 5 | 5 | 1 | 3 | 4 | 12 |
| longest gap (s) | 3.25 | 5.49 | 3.98 | 5.27 | 4.32 | **103.3** |
| longest-gap marker | `671:LShoulderTop` | `671:LShoulderTop` | `671:ChestTop` | `FKA-671_ChestTop` | `T3_671:ChestTop` | `T3_671:LThighFront` |
| coverage mean % | 99.70 | 99.64 | 99.94 | 99.84 | 99.83 | 97.91 |
| sustained-dropout markers | 2 | 3 | 1 | 1 | 2 | 2 |
| session status | caution | caution | caution | caution | caution | caution |
| qc_mask use/caution/exclude | 26618/2464/1522 | – | – | 27893/1182/1404 | 29498/982/1194 | **2339/112/28941** |
| artifact events | 272 | – | – | – | 192 | 268 |
| segment_length pairs (auto) | 22 | – | – | – | 22 | – |

Per-file notes:
- **T1_R1 / T1_R2:** moderate gap burden, several multi-second gaps (shoulder), ~5–8% frames flagged. **Usable with caution.**
- **T2_R1:** cleanest (5 gaps ≥0.2 s). **Usable with caution (closest to ready).**
- **T2_R2:** **duplicate skeleton present and correctly handled** — 108 labeled, 48 quarantined `phantom_skeleton` (the `FKA-671_` copy is 100% missing and excluded from the denominator). After quarantine it behaves like a normal 48-marker session. **Usable with caution** *(but note the longest-gap marker is reported with the phantom prefix `FKA-671_ChestTop` — a labeling inconsistency).*
- **T3_R1:** good (93% use). **Usable with caution.**
- **T3_R2:** **103.3 s** dropout on `T3_671:LThighFront` (+ others); ≈92% of frames `exclude`, 91% of 0.5 s windows excluded; 61 unlabeled tracks; 98% frames with an unlabeled marker. **Not ready / requires investigation** — despite the headline session status of `caution`.

**Affected markers / frame ranges (T3_R2, from `qc_report.md` intervals):** large `exclude` blocks at frames `7961–21637` (114 s) and `24339–31391` (59 s) spanning nearly all body groups; thigh_knee implicated throughout. This is consistent with a long single-marker dropout dominating the union mask.

---

## 18. Fine-grained comparison across 671 files

**Table 1 — session comparison**

| file | T/R | frames | dur(s) | n_in_analysis | marker_set_id (auditor) | missing% | gaps≥0.2 | gaps≥0.5 | longest_gap | swap_cands(events) | usable_for_L2.5 | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 671_T1_P1_R1 | T1/R1 | 30604 | 255.0 | 48 | `671:` | 0.30 | 47 | 11 | 3.25 | ~ (wrist FP) | caution | shoulder gaps |
| 671_T1_P1_R2 | T1/R2 | 30235 | 252.0 | 48 | `671:` | 0.36 | 51 | 13 | 5.49 | n/r | caution | similar to R1 |
| 671_T2_P1_R1 | T2/R1 | 30356 | 253.0 | 48 | `671:` | 0.06 | 5 | 2 | 3.98 | n/r | caution | cleanest |
| 671_T2_P1_R2 | T2/R2 | 30479 | 254.0 | 48 | `671:`+`FKA-671_`(dup) | 0.16 | 21 | 9 | 5.27 | n/r | caution | duplicate skeleton quarantined |
| 671_T3_P1_R1 | T3/R1 | 31674 | 263.9 | 48 | **`T3_671:`** | 0.17 | 28 | 5 | 4.32 | 22 pairs | caution | clean; different prefix |
| 671_T3_P1_R2 | T3/R2 | 31392 | 261.6 | 48 | **`T3_671:`** | 2.09 | 43 | 18 | **103.3** | n/r | **NOT READY** | 92% frames exclude; status says caution |

*"marker_set_id" is the auditor's label; Layer 1 emits no such field.*

**Table 2 — repeatedly-problematic markers / pairs**

| marker / pair | files affected | type | frame ranges | severity | should affect downstream? |
|---|---|---|---|---|---|
| `*:LShoulderTop` / shoulder region | T1_R1, T1_R2 | multi-second gaps | ~45–48 s (R1) | large | yes (shoulder windows) |
| `*:ChestTop` (incl. pair `ChestTop__WaistCBack`) | T1_R1, T2_R1, T3_R1 | gaps + segment-swap candidate | e.g. T1 frames 1136–1531 | moderate | review (some swap FPs) |
| `RHandIn__RHandOut`, `LHandIn__LHandOut` (wrist_hand pairs) | T1_R1 (48 swap events) | segment-length "swap" | many short | moderate | **likely false positive** — do not auto-exclude |
| `T3_671:LThighFront` | T3_R2 | **103.3 s dropout** | 7961–21637, 24339–31391 | severe | **yes — exclude** |
| `*:RFArm`, `*:LElbowOut` | T1_R1 | ≥0.5 s gaps | 131–157 s | large | yes |

**Table 3 — marker-set differences**

| comparison | markers only in A | markers only in B | likely consequence | needs L1 action? | needs L2.5 action? |
|---|---|---|---|---|---|
| T1 (`671:`) vs T3 (`T3_671:`) | none (canonical) | none (canonical) | full-name join ⇒ 0% overlap; canonical join ⇒ 100% overlap | **yes: detect+report+fingerprint** | yes: prefix-normalize (already done, but make robust/triggered) |
| T1 (`671:`) vs T2_R2 (`671:`+`FKA-671_`) | none | `FKA-671_*` phantom (quarantined) | handled within file | no (works) | no |
| Is T3 anatomically different? | — | — | **No — same 54 anatomical markers** | report this explicitly | confirm before cross-T JcvPCA |

**Is one timepoint worse?** Yes — **T3_R2** is by far the worst (single long dropout). Otherwise quality is comparable across T1/T2/T3, supporting that T3 is *capture-comparable* anatomically; the only structural difference is the naming.

---

## 19. Problematic markers / marker pairs / frame ranges

- **Genuinely problematic (act on):** `T3_671:LThighFront` in T3_R2 (103 s) ⇒ that session not ready. Shoulder/forearm multi-second gaps in T1. Chest/waist gaps across several files.
- **Probable false positives (do not over-trust):** `RHandIn__RHandOut` / `LHandIn__LHandOut` segment-swap candidates — hand markers aren't rigid; 48 such events in T1_R1 alone.
- **Structurally invisible (won't be caught):** true left↔right swaps (same-side-only pairing); frozen/held markers (detector disabled); cross-session marker-set change (no detector).

---

## 20. Trustworthiness for Layer 2.5 and Layer 3

1. Raw gaps identified clearly? **Yes.**
2. Marker jumps clearly? **Yes** (velocity + spike), acceleration off.
3. Swaps / candidates clearly? **Partially** — present but noisy & cross-side-blind.
4. Unlabeled bursts clearly? **In the human report yes; machine export weak** (not in essential tier; not in window scoring).
5. Marker-set differences clearly? **No.**
6. 671 T3 difference reported clearly? **No.**
7. Artifact flags local enough? **Yes at flag/interval level; no at headline `status` (union-exclude).**
8. Selected windows traceable to raw QC? **Yes (frame join).**
9. Output files organized/named consistently? **Mostly; timestamped run folders complicate stable wiring.**
10. Schemas stable? **Yes, but no formal schema contract/tests.**
11. Reports concise for humans? **Yes.**
12. Reports detailed for debugging? **Yes (more at full tier).**
13. Anything missing before using L2.5 outputs for L3? **Yes — marker-set fingerprint/mismatch flag; reconciled session usability; consolidated downstream QC file.**
14. Enough evidence to trust Group 4 windows? **Per-window yes; cross-timepoint comparability of Group 4 windows — not from L1 alone (marker-set + T3_R2 exclusion must be checked).**
15. Files to mark "usable with caution" / "not ready"?
    - `671_T1_P1_R1`, `671_T1_P1_R2`, `671_T2_P1_R1`, `671_T2_P1_R2`, `671_T3_P1_R1` → **usable with caution**.
    - `671_T3_P1_R2` → **not ready / requires investigation**.

---

## 21. Weak points and risks (answering §21 of the prompt)

1. Only reports gaps, never repairs — **confirmed, good.**
2. Repairs anything? **No.** Documented.
3. One marker gap contaminates a window? **For `qc_mask.status` (union) yes; per-criterion/interval, no.** Demonstrated by T3_R2.
4. One artifact frame contaminates a session? **No** (session verdict is coverage-based; window/frame are independent). If anything the opposite problem: a 92%-exclude session is still rated "caution".
5. Swap candidates local & traceable? **Yes (pair + frames + affected_markers), but noisy.**
6. Artifact thresholds appropriate for Gaga? **Velocity yes (σ=8, p99.97); segment-swap 18% too tight for hand pairs.**
7. Fast movement falsely flagged? **Low for velocity; the swap screen over-flags non-rigid pairs.**
8. Subtle swaps missed? **Yes — cross-side swaps structurally invisible.**
9. Marker-set diffs treated differently from tracking gaps? **Within-file yes (quarantine); cross-file: not detected at all.**
10. 671 T3 difference clearly visible? **No.**
11. Provides fields L2.5 needs? **Frame/time/flags yes; marker-set id and per-frame culprit marker no.**
12. Enough context for L3 interpretation? **Indirect only; cross-session comparability not asserted.**
13. Reports easy for humans? **Yes — but the headline status can be misleading (T3_R2).**
14. Machine outputs complete & stable? **Stable; not complete (no marker-set/consolidated file; unlabeled not exported in essential tier).**
15. QC outputs linked to frame/time indices? **Yes — validated.**
16. Hidden assumption that all sessions share the same marker set? **Not asserted in code, but there is no guard, and the human report's identical-looking counts invite that assumption.**

---

## 22. Recommended changes, if any (NOT implemented)

For each: *issue / why it matters / recommended change / risk of changing / risk of not changing / downstream impact / approval needed.*

**R1 — Export a per-session marker-set fingerprint + emit a cross-session mismatch warning.**
- Issue: no marker-set identity is detected/reported/exported across sessions; 671 T3 (`T3_671:`) is invisible.
- Why: prevents silent comparison of incompatibly-named raw sets; makes the known issue undeniable.
- Change: add `marker_set_id` (hash of sorted `canonical_short_name`), `asset_prefixes`, `n_canonical_markers`, and the sorted canonical list to `layer1_segmentation_notebook_manifest.json` and a new `marker_set.csv`; in Layer 6 compare across sessions → `marker_set_comparison.csv` + `MARKER_SET_MISMATCH`/`MARKER_SET_PREFIX_CHANGE` message.
- Risk of changing: low (additive output); must not change existing schemas.
- Risk of not changing: **high** — cross-timepoint JcvPCA can compare mislabeled/incompatible sets; relies on a brittle downstream regex.
- Downstream impact: enables L2.5/L3 to assert comparability; lets L3 caption "same anatomy, re-labelled".
- Approval: **yes** (new outputs/contract change).

**R2 — Reconcile session-level status with frame/window-level exclusion in the report headline.**
- Issue: T3_R2 shows `Overall QC status: caution` while 92% frames excluded.
- Why: the headline misleads a PI into trusting an unusable session.
- Change: add a `frame_exclude_pct` / `window_exclude_pct` to the identity block and derive a combined `session_usability` that cannot be "caution" when >X% frames excluded.
- Risk of changing: low–medium (verdict semantics change; could re-label sessions).
- Risk of not changing: **high** — unusable sessions enter L2.5/L3 unnoticed.
- Downstream impact: clearer gating.
- Approval: **yes** (changes a reported verdict).

**R3 — Make `qc_mask.status` locality explicit / configurable.**
- Issue: ≥0.5 s gap on a single marker ⇒ whole span `exclude` for all markers.
- Why: over-aggressive; can gut window yield for an otherwise-fine session.
- Change: keep union as default but add per-frame `n_markers_gap_ge_0p5` and the dominant marker into `qc_mask.csv` (not only intervals), and document that the headline status is union; optionally a config switch for "marker-union vs coverage-fraction" exclude.
- Risk of changing: medium (semantics).
- Risk of not changing: medium — downstream must always read intervals to avoid over-exclusion.
- Downstream impact: finer L2.5 decisions.
- Approval: **yes.**

**R4 — Tune / curate marker-swap pairing.**
- Issue: hand pairs (`RHandIn__RHandOut`) produce false swap candidates; cross-side swaps invisible.
- Why: false positives erode trust; false negatives miss real L/R swaps.
- Change: ship a curated `config/marker_pair_map.csv`; raise `max_segment_length_change_pct` for non-rigid groups; add an optional cross-side symmetric-distance check.
- Risk: medium (changes detections).
- Risk of not: noisy swap flags / missed swaps.
- Approval: **yes.**

**R5 — Re-enable frozen-marker (constant-hold) screening, or document the blind spot.**
- Issue: held/frozen values are neither a gap nor an artifact in the current config.
- Change: enable `constant_position_hold` with conservative params, or add an explicit note in the report.
- Approval: **yes** (threshold/behavior change).

**R6 — Export unlabeled burden in the essential tier and feed it into window scoring.**
- Issue: strong instability signal (T3_R2: 98% frames with unlabeled, 72 s burst) is human-report-only.
- Change: add `unlabeled_frame_counts`/`unlabeled_marker_summary` to essential outputs; optionally factor bursts into window caution.
- Approval: **yes.**

**R7 — Add a Layer 1 test suite.**
- Issue: zero tests on the QC foundation.
- Change: add the tests in §15.
- Approval: **no** (tests are additive and safe) — but still do **not** implement during this audit per instructions.

**R8 — Stable, timestamp-free run folder / `run_key` field for wiring.**
- Issue: L2.5 input uses hand-renamed `QC_671_T1_P1_R1`; L1 emits timestamped dirs.
- Change: also write/symlink a `run_key`-named folder or record `run_key` folder mapping in a discoverable index.
- Approval: **yes.**

---

## 23. What should be reviewed in a Jupyter notebook

1. **`671_T3_P1_R2` first** — plot `qc_mask.status` over time vs the `T3_671:LThighFront` trajectory; confirm the 103 s dropout and decide exclude-session vs interpolate-one-marker.
2. **Cross-session marker-set check** — load all 6 `marker_inventory` (requires full-tier rerun, since essential omits it) and compare `canonical_short_name` sets and prefixes; confirm T3 = same anatomy.
3. **Swap false positives** — overlay `RHandIn`/`RHandOut` distance vs the 18% band; decide whether to curate `marker_pair_map.csv`.
4. **Velocity threshold sanity** — per-segment velocity histograms (already produced) vs σ=8 line for Gaga arms/legs.
5. **Session-vs-frame verdict reconciliation** — for each session, plot `frame_exclude_pct` vs the `caution/acceptable/poor` label to expose mismatches.
6. **Window yield by timepoint** — compare 0.5 s window `use%` across T1/T2/T3 to judge cross-timepoint comparability for Group 4.

---

## 24. Open questions for the user

1. For JcvPCA, are T3 markers harmonized to T1/T2 by **canonical short name** (recommended, anatomy matches) — and is that harmonization currently *only* the L2.5 regex? (If yes, this needs a Layer 1 guard.)
2. Should `671_T3_P1_R2` be **excluded** from cross-timepoint analysis, or salvaged by treating `LThighFront` as a removed marker?
3. Is the **marker-union** `qc_mask.status` the intended downstream gate, or should L2.5 use coverage-fraction instead?
4. Are there other subjects with different prefixes (e.g. `T3_252`)? The L2.5 regex is `671`-specific and would not strip a non-671 asset suffix the same way.
5. Is acceleration/frozen-marker screening intentionally off for all data, or only for this tuning pass?

---

## 25. Independent auditor observations beyond the requested questions

**O1 — Session readiness verdict and the primary deliverable can flatly contradict each other.**
- Observation: `evaluate_preprocessing_status` (coverage-based) yields `caution` for T3_R2 while `qc_mask` excludes 92% of frames. The two QC signals are computed from different logics (coverage fraction vs marker-union gap) and are never reconciled or cross-checked.
- Why it matters: the headline a human reads is the optimistic one; downstream automated gates that read session status would admit an unusable session.
- Severity: **blocking** (for trustworthy reporting).
- Next step: add a reconciled usability field (R2) + a test (item 15).
- Requires user decision: yes (verdict semantics).

**O2 — The 671 T3 fix lives as a hard-coded regex in Layer 2.5, with no Layer 1 detection and no test.**
- Observation: `marker_family.py` literally encodes `^(?:T3_)?671[_:]?`. This is subject- and timepoint-specific and untested; Layer 1 provides nothing to trigger or validate it.
- Why: brittle single-point-of-failure for cross-timepoint comparability; new subjects/prefixes break silently.
- Severity: **blocking**.
- Next step: R1 (L1 fingerprint + mismatch) and a contract test.
- Requires user decision: yes.

**O3 — `marker_inventory` (the only place the real marker list/prefix lives) is excluded from the essential tier.**
- Observation: default runs export counts but not names; the L2.5-consumed folder has no marker list.
- Why: makes any cross-session marker audit impossible from default outputs; forces full-tier reruns.
- Severity: **important**.
- Next step: include a compact `marker_set.csv` in essential tier (R1/R6).
- Requires user decision: yes (output change).

**O4 — Naming inconsistency inside outputs.**
- Observation: `segment_length_qc.pair_name` uses short names (`ChestTop__WaistCBack`) while `marker_a/marker_b` and gap markers use full prefixed names (`671:ChestTop`, `T3_671:...`, even `FKA-671_ChestTop` for a phantom in T2_R2). `qc_mask_intervals.affected_markers` mixes both styles in one cell.
- Why: cross-session joins/aggregations on these columns silently mismatch; phantom prefixes leak into summaries.
- Severity: **important**.
- Next step: add a `canonical_*` column alongside raw names everywhere markers appear.
- Requires user decision: yes.

**O5 — Auto-pairing uses the session median as the rigid baseline; a sustained swap can bias the baseline.**
- Observation: `nanmedian` of the distance defines "normal". If a swap persists for a large fraction of frames, the median shifts toward the swapped distance, shrinking deviations and hiding the swap.
- Why: long swaps (the most damaging) are the ones most able to evade a median baseline.
- Severity: **important**.
- Next step: baseline from a known-clean window or robust mode; flag bimodal distance distributions.
- Requires user decision: no (analysis improvement) — but do not implement now.

**O6 — `effective_frame_rate` mismatch handling can hard-fail a run.**
- Observation: `require_capture_export_rate_match: true` raises on any capture≠export mismatch. For heterogeneous Motive exports this could block otherwise-good files (none of the 671 files hit it — all 120 Hz).
- Severity: **minor**.
- Next step: confirm intended; consider warn-not-fail.
- Requires user decision: yes.

**O7 — No system-wide "bad frame across many markers" detector.**
- Observation: simultaneous multi-marker spikes (e.g. a calibration glitch) are only visible as many independent per-marker candidates, not one global event.
- Severity: **minor/important** depending on data.
- Next step: add an optional per-frame multi-marker artifact count.
- Requires user decision: no.

**O8 — Reproducibility/timestamp coupling.**
- Observation: outputs land in `..._{timestamp}/`; the L2.5 input uses manually renamed `QC_*` folders. Wiring is implicit and easy to get wrong (e.g. mixing an old `20260619` run with new ones — there is even a leftover `671_T1_P1_R1_20260619_192857.zip`).
- Severity: **important** (provenance).
- Next step: R8 + record exact run folder in L2.5 manifests.
- Requires user decision: yes.

**O9 — `qc_mask.reason` is `NaN` for `use` frames (object column).**
- Observation: minor schema wart; downstream must treat NaN as empty. `load_layer1` only coerces flag columns, not `reason`.
- Severity: **minor**.
- Next step: write empty string instead of NaN.
- Requires user decision: no.

---

## 26. Final verdict

### 26.1 Overall
**Layer 1 raw marker QC is: `usable with caution`.**
The per-file gap/artifact engine is solid and faithfully report-only; but (a) cross-session marker-set identity is undetected/unexported, (b) the session headline can contradict the frame-level reality, and (c) there are no tests. These must be addressed (or compensated downstream with eyes open) before Layer 1 outputs are trusted for **cross-timepoint** Layer 3 JcvPCA.

### 26.2 Per-stage
| Stage | Verdict |
|---|---|
| gap detection | **ready** |
| gap reporting | **ready** (headline-status caveat for union exclusion) |
| marker jump detection | **ready** (acceleration off by choice) |
| marker swap detection | **requires fix** (hand false positives; cross-side blind; median-baseline bias) |
| unlabeled-marker burden | **usable with caution** (not in essential export / window scoring) |
| artifact candidate detection | **usable with caution** (frozen-marker off; no system-wide detector) |
| marker-set consistency | **requires fix** (no cross-session detection/export) |
| participant 671 T3 marker-set issue | **requires fix** (invisible in L1; only a downstream regex saves it) |
| local-vs-global flagging | **usable with caution** (headline union-exclude vs local flags) |
| selected-window QC support | **ready** (frame join is clean and validated) |
| Layer 2.5 compatibility | **usable with caution** (works today; brittle on marker-set + naming) |
| Layer 3 interpretability support | **usable with caution** (no comparability assertion across T1/T2/T3) |

### 26.3 Participant 671 outputs
**For Layer 2.5 and Layer 3, participant 671 Layer 1 outputs are: `usable with caution` — with one exception that is `not ready`.**
- `T1_P1_R1`, `T1_P1_R2`, `T2_P1_R1`, `T2_P1_R2`, `T3_P1_R1` → **usable with caution**.
- `T3_P1_R2` → **not ready** (≈92% frames excluded by a 103 s thigh dropout; do not feed to JcvPCA without remediation).

**Exactly what the caution is / what to check before use:**
1. Confirm **marker-set harmonization** of T3 (`T3_671:` → canonical) is applied and validated, not assumed — Layer 1 does not assert it. (The anatomy *is* identical across all 6 files; verified by header parsing.)
2. **Do not** join Layer 1 marker-level tables across sessions by full marker name — strip the asset prefix first.
3. Treat `qc_mask.status` as a **marker-union** signal; for per-window decisions, read `qc_mask_intervals.affected_markers` / per-criterion flags rather than the headline `status`.
4. Treat marker-**swap** candidates (especially hand pairs) as **manual-review**, not exclusions.
5. Re-examine `T3_P1_R2` specifically before any cross-timepoint comparison; its session status `caution` understates a 92%-exclude reality.

---

## Latest Layer 1 output files reviewed and consistency check

### Output-file inventory (essential tier, per the 671 runs)

| output file | purpose | producer | key columns | human-readable? | machine-readable? | downstream-ready? | issues |
|---|---|---|---|---|---|---|---|
| `session_summary.csv` | one-row session metrics + readiness verdict | `gaps.update_session_summary_layer2` | counts, missing%, gap counts, coverage, `raw_qc_preprocessing_status` | partial | yes | partial | no marker list; status can contradict frame mask; carries no marker-set id |
| `qc_mask.csv` | **PRIMARY** frame-level advisory mask | `deliverables.build_qc_mask` | `frame,time_s,status,flag_gap_0p2,flag_gap_0p5,flag_artifact_sigma,flag_segment_swap,flag_edge_effect,reason` | no | yes (validated) | **yes** | `status` is marker-union; no per-frame culprit marker; `reason` NaN on `use` |
| `qc_mask_intervals.csv` | interval rollup of mask | `deliverables._mask_intervals` | start/end frame+s, status, reason, criterion, `affected_markers`, has_* | yes | yes | yes | `affected_markers` mixes prefixed names + short pair names |
| `gaps_over_0p2s.csv` / `gaps_over_0p5s.csv` | per labeled marker gaps ≥ threshold | `deliverables.build_gaps_over_threshold` | marker, group, n_gaps, totals, intervals | yes | yes | yes | full prefixed marker names (cross-session mismatch) |
| `artifact_events.csv` | clustered artifact events | `artifacts.cluster_artifact_events` | marker, group, method, frames, time, class, severity, near_gap | yes | yes | yes | swap method noisy (hand pairs) |
| `artifact_session_summary.csv` | one-row artifact tallies + recommendation | `artifacts.build_artifact_session_summary` | counts by class, recommendation | yes | yes | yes | – |
| `artifacts_by_segment.csv` | artifact burden per body region | `deliverables.build_artifacts_by_segment` | region, counts, `n_segment_swap`, per-min | yes | yes | yes | includes possibly-FP swaps |
| `segment_length_qc.csv` | rigid-pair distance QC | `artifacts.detect_segment_length_violations` | pair, marker_a/b, median, n/pct violating | yes | yes | partial | mixed naming; auto-pairing FPs |
| `quarantined_markers.csv` | phantom/never-solved markers | `gaps.run_layer2_gaps` | marker, group, missing%, reason | yes | yes | yes | works (T2_R2 = 48 phantom) |
| `qc_report.md` / `.html` | human report | `report.build_qc_report_markdown` | narrative | yes | no | n/a | headline status can mislead; no marker-set note |
| `qc_reason_codes.md` | reason-code glossary | `reason_codes` | text | yes | no | n/a | – |
| `layer1_segmentation_notebook_manifest.json` | **L2.5 handoff** | `io._write_segmentation_manifest` | subject/session/run_key, fps, n_frames, frame/time cols, mask paths | partial | yes | partial | **no marker list / no marker-set id / no usability verdict** |
| `RUN_MANIFEST.json` | run provenance | `io._write_manifest` | version, tier, table row counts, files | partial | yes | yes | timestamped dir only |
| `config_used.yaml` | thresholds snapshot | `io.write_outputs` | full config | yes | yes | yes | – |
| plots `*.png` | visual QC | `plots.py` | – | yes | no | n/a | – |
| **missing:** `marker_inventory.csv`, `unlabeled_*.csv`, window tables | (full tier only) | — | — | — | — | — | absent in essential ⇒ no per-session marker list / unlabeled table downstream |
| **missing:** any cross-session `marker_set_comparison` / `batch_runs/*` | — | — | — | — | — | — | not produced |

### Consistency check

| consistency check | result | evidence | concern | recommendation |
|---|---|---|---|---|
| All reports agree on frame counts | **PASS** | `qc_mask` rows == `n_frames` == manifest (`_validate_qc_mask`); T1_R1=30604, T3_R1=31674 | none | keep validation |
| Agree on marker counts | **PASS (within file)** | `session_summary` vs quarantined; T2_R2 108→48+48 phantom | none within file | — |
| Agree on gap counts | **PASS** | `session_summary.n_gaps_*` consistent with `gaps_over_*` | none | — |
| Agree on artifact counts | **PASS** | RUN_MANIFEST row counts == events table | none | — |
| Agree on selected-window boundaries | **N/A** | L1 uses fixed bins; L2.5 selects later | acceptable | document |
| Participant/session labels match across files | **PASS** | `subject_id=671`, `session_id` consistent | none | — |
| Time/frame columns aligned | **PASS** | `qc_mask.time_s` validated vs Motive time | none | — |
| Marker names written consistently | **FAIL** | prefixed vs short vs phantom (`671:`,`T3_671:`,`FKA-671_`, `ChestTop__WaistCBack`) | cross-session joins mismatch | add canonical columns (R1/O4) |
| Missing-markers vs marker-set diffs represented consistently | **FAIL** | within-file quarantine exists; cross-file marker-set change has no representation | T3 invisible | R1 |
| **Session status vs frame-mask exclusion consistent** | **FAIL** | T3_R2: status `caution` vs 92% frames `exclude` | misleading headline | R2 |
| T3 marker-set difference visible in outputs | **FAIL** | only incidental prefixed names; no field/flag/warning | known issue hidden | R1 |

### Are Layer 1 outputs downstream-ready, or do they need an aggregation/harmonization file first?
**They need an additional consolidated, marker-set-aware QC file before Layer 2.5/3 can be fully trusted for cross-timepoint work.** Today L2.5 succeeds only because it (a) joins `qc_mask` on `frame` and (b) re-derives marker families with a hard-coded prefix regex. That is fragile.

**Recommended (describe only — do NOT implement):**
- `layer1_selected_window_qc_summary.csv` — *not feasible in Layer 1* (L1 doesn't know selected windows); this belongs to L2.5. Recommend L2.5 produce it from L1's `qc_mask`.
- `layer1_marker_set.csv` (per session) — `session_id, participant_id, timepoint, part_id, repetition_id, source_file, asset_prefixes, n_canonical_markers, marker_set_id (hash), canonical_marker_list`.
- `layer1_qc_events.parquet` (event-level; one row per gap/artifact/swap) with at minimum: `session_id, participant_id, timepoint, part_id, repetition_id, source_file, marker_name, canonical_marker_name, marker_set_id, marker_set_mismatch_flag, qc_event_type, gap_flag, jump_flag, swap_candidate_flag, unlabeled_burden_flag, artifact_flag, severity, affected_coordinate_or_axis, event_start_frame, event_end_frame, event_duration_frames, event_duration_sec, notes`. Event-level (not frame×marker) keeps it small.
- Keep the existing frame-level `qc_mask.csv` as the frame mask; add `marker_set_id` + `marker_set_mismatch_flag` columns and the per-frame dominant culprit marker.
- A Layer 6 `marker_set_comparison.csv` across sessions with a `MARKER_SET_MISMATCH` verdict.

These additions would make the 671 T3 difference **impossible to ignore** downstream while leaving harmonization in Layer 2.5.

---

*End of audit. No source, config, threshold, test, output, or data file was modified. The only file written by this audit is this report (`LAYER1_RAW_MARKER_QC_AUDIT_REPORT.md`) at the repository root; relocate to a dedicated `audits/` or `reports/` directory if preferred.*
