# Layer 1 output contract (evidence-only)

Layer 1 is **descriptive evidence only**. It records what happened in the raw Motive CSV — gaps, missing frames, artifact candidates, marker-set identity — without assigning session go/no-go labels.

## What Layer 1 does **not** do

- No `caution`, `not_ready`, `acceptable`, or `exclude` session verdicts
- No `recommended_bvh_action` or preprocessing recommendations
- No implied “discard entire session” when one marker has long gaps

**Decisions belong in Layer 2.5** (marker subsets, windows) and **Layer 3** (analysis segments).

## Union frame mask vs per-marker evidence

`qc_mask.csv` uses a **union rule**: if **any** in-analysis labeled marker has a gap ≥0.5 s on a frame, `flag_gap_0p5=True` for that frame — even when other markers (e.g. upper body) still have valid data.

Always check per-marker tables before excluding body regions:

| File | Content |
|------|---------|
| `layer1_marker_gap_evidence.csv` | Per-marker % frames/time in gap ≥0.5 s (primary attribution) |
| `gaps_over_0p5s.csv` | Which markers, gap durations, intervals |
| `gaps_over_0p2s.csv` | Moderate gaps |
| `artifact_events.csv` | Per-marker artifact candidates |
| `layer1_marker_set.csv` | Prefix / canonical marker-set identity |
| `layer1_qc_handoff.csv` | Interval-level flags + affected markers |

All marker-level tables include `marker_name_raw`, `marker_name_canonical`, and `asset_prefix` where applicable.

## Primary outputs

### `qc_mask.csv`

| Column | Meaning |
|--------|---------|
| `frame`, `time_s` | Join keys for Layer 2 parquet |
| `flag_gap_0p2` … `flag_edge_effect` | Boolean criterion flags |
| `reason` | Semicolon-separated codes (`GAP_GE_0P5`, `ARTIFACT_SIGMA`, …) |

### `layer1_marker_gap_evidence.csv`

One row per labeled marker with at least one gap ≥0.5 s:

| Column | Meaning |
|--------|---------|
| `pct_frames_in_gap_ge_0p5` | % of session frames where **this marker** is in a gap ≥0.5 s |
| `pct_session_time_in_gap_ge_0p5` | % of session duration in that marker's gaps ≥0.5 s |
| `total_gap_seconds_ge_0p5`, `longest_gap_seconds`, `n_gaps_ge_0p5` | Duration evidence |

### `session_summary.csv` (factual fields)

- Missingness counts and percentages
- `markers_with_gap_ge_0p5s`, `n_markers_with_gap_ge_0p5s`
- `gap_evidence_summary` (one-line factual summary)
- **Union mask:** `pct_frames_union_flag_*`, `pct_frames_union_any_flag`
- **Dominant marker:** `dominant_gap_marker_canonical`, `pct_frames_dominant_marker_in_gap_ge_0p5`, `pct_session_time_dominant_marker_in_gap_ge_0p5`
- `dominant_criterion` (longest qc_mask interval criterion)

### Windows (Layer 3 internal)

Window tables use `reason_codes` only (e.g. `LARGE_GAP_OVERLAP`). There is no `window_quality_label` verdict.

## Example: participant 671 T3_P1_R2

One marker (`LThighFront`) can dominate gap burden while most other markers remain largely present.

- `pct_frames_union_flag_gap_0p5` ≈ 92% reflects the **union mask** (any marker triggers the frame).
- `pct_frames_dominant_marker_in_gap_ge_0p5` on `LThighFront` ≈ 92% shows **which marker** drives that burden.
- Upper-body markers may have low `pct_frames_in_gap_ge_0p5` in `layer1_marker_gap_evidence.csv`.
