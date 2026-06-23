# Motive_QC

**Version:** 0.6.0

Reproducible quality-control pipeline for **raw OptiTrack Motive marker XYZ CSV exports** — before gap filling, smoothing, skeleton solving, or BVH export. The pipeline parses capture files, quantifies missingness and gaps, screens kinematic artifact **candidates**, judges fixed-duration analysis windows for PCA/jPCA planning, and writes shareable QC reports.

**Primary deliverable (per session):** `tables/qc_mask.csv` — frame-level advisory mask with `frame` and `time_s` for joining Layer 2 Stage 08 parquet.

**In scope:** raw marker XYZ QC, gap structure, frame/window warnings, artifact event screening, `qc_mask` / `qc_mask_intervals`.

**Out of scope:** modifying the CSV, gap filling, smoothing/filtering, BVH parsing, automatic frame deletion, PCA/jPCA execution.

Full specification: [`docs/PROJECT_SPEC_MOTIVE_QC.md`](docs/PROJECT_SPEC_MOTIVE_QC.md)

---

## Setup

**Requirements:** Python 3.10+, dependencies in [`requirements.txt`](requirements.txt)

```bash
cd motive_qc
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

For headless runs (CI / servers), set a writable Matplotlib config dir:

```bash
export MPLCONFIGDIR="$PWD/.mplconfig"
export MPLBACKEND=Agg
```

---

## Data layout

Organize Motive CSV exports under subject folders:

```
data/
  671/
    671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv
    ...
  252/
    ...
  archive/          # excluded by exclude_globs
```

**Filename pattern:** `{subject_id}_{T#_P#_R#}_Take {date} {time}[_suffix].csv`

If CSVs start flat under `data/`, **copy** (do not move) them into `data/{subject_id}/` so batch discovery works. Keep flat originals until you confirm nothing else references them.

---

## Run one session (CLI)

### 1. Dry-run (header / metadata only)

```bash
python motive_raw_qc.py --config config.yaml --dry-run \
  --input "data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv"
```

### 2. Full pipeline (Layers 1–5)

```bash
python motive_raw_qc.py --config config.yaml --verbose \
  --input "data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv"
```

**CLI overrides** (optional; config.yaml is the base):

| Flag | Purpose |
|------|---------|
| `--input PATH` | Motive CSV path (overrides `paths.input_csv`) |
| `--subject-id ID` | e.g. `671` (auto-parsed from filename if omitted) |
| `--session-id ID` | e.g. `T1_P1_R1` (auto-parsed from filename if omitted) |

You can also set `paths.input_csv`, `project.subject_id`, and `project.session_id` in [`config.yaml`](config.yaml) and run without `--input`.

**Output folder:** `outputs/runs/{subject_id}_{session_id}_{YYYYMMDD_HHMMSS}/`  
Example: `outputs/runs/671_T1_P1_R1_20260619_192544/`

**Layers 1–2 only:** set `reporting.stop_after_layer: 2` in config (no `qc_mask.csv` — that is a Layer 5 deliverable).

---

## Run batch (Layer 6)

Discover sessions under `data/{subject_id}/`:

```bash
python motive_batch_qc.py --config config.yaml --discover --subject 671
```

Run all sessions for one subject, all subjects, or a filter:

```bash
python motive_batch_qc.py --config config.yaml --subject 671 --verbose
python motive_batch_qc.py --config config.yaml --all-subjects --verbose
python motive_batch_qc.py --config config.yaml --subject 671 \
  --sessions T1_P1_R1,T2_P1_R1 --verbose
```

Each session gets its own `outputs/runs/671_T1_P1_R1_*/` folder (mask CSV, manifest, optional HTML). Layer 6 also writes a cross-session package under `outputs/batch_runs/batch_{timestamp}/`.

Exit code `1` if any session failed (`failures.csv` in the batch folder).

---

## Per-session output manifest

Each full L1–L5 run creates:

```
outputs/runs/671_T1_P1_R1_{YYYYMMDD_HHMMSS}/
├── RUN_MANIFEST.json
├── layer1_segmentation_notebook_manifest.json   ← Layer 2 handoff
├── config_used.yaml
├── qc_report.md
├── qc_reason_codes.md
├── qc_report.html                               ← best-effort; optional
├── tables/
│   ├── session_summary.csv
│   ├── quarantined_markers.csv
│   ├── gaps_over_0p2s.csv
│   ├── gaps_over_0p5s.csv
│   ├── artifacts_by_segment.csv
│   ├── segment_length_qc.csv
│   ├── artifact_events.csv
│   ├── artifact_session_summary.csv
│   ├── qc_mask.csv                              ← PRIMARY deliverable
│   └── qc_mask_intervals.csv
└── plots/
    ├── gap_timeline.png
    ├── window_quality_timeline.png
    ├── artifact_timeline.png
    └── artifact_velocity_histogram*.png
```

### Essential tier tables (default: `outputs.tier: essential`)

| File | Layer | Content |
|------|-------|---------|
| `session_summary.csv` | L2 | One row: missing %, gap stats, preprocessing status |
| `quarantined_markers.csv` | L2 | Never-solved / phantom markers |
| `gaps_over_0p2s.csv` | L5 | Labeled gaps ≥ 0.2 s |
| `gaps_over_0p5s.csv` | L5 | Labeled gaps ≥ 0.5 s |
| `artifacts_by_segment.csv` | L5 | Artifact burden by body region |
| `segment_length_qc.csv` | L4 | Rigid-body pair length violations |
| `artifact_events.csv` | L4 | Clustered artifact events |
| `artifact_session_summary.csv` | L4 | Event counts + recommendation |
| **`qc_mask.csv`** | L5 | **Frame-level mask — join key for Layer 2** |
| `qc_mask_intervals.csv` | L5 | Interval summary of mask flags |

Set `outputs.tier: full` for debug tables (`marker_inventory`, `gap_events`, `frame_qc_mask`, window tables, heatmaps, etc.).

### `qc_mask.csv` columns

| Column | Purpose |
|--------|---------|
| `frame` | Motive export frame index |
| `time_s` | Seconds from Motive `Time (Seconds)` |
| `status` | Advisory: `use` / `caution` / `exclude` |
| `flag_gap_0p2` | Gap ≥ 0.2 s on any in-analysis labeled marker |
| `flag_gap_0p5` | Gap ≥ 0.5 s |
| `flag_artifact_sigma` | Velocity MAD / spike artifact |
| `flag_segment_swap` | Rigid-body segment length violation |
| `flag_edge_effect` | Buffer frames adjacent to large gaps |
| `reason` | Semicolon-separated reason codes |

The pipeline validates row count, monotonic `frame`, and `time_s` alignment before writing `layer1_segmentation_notebook_manifest.json`. Mask validation failure **fails the run**; HTML failure does not (unless `outputs.fail_on_html_error: true`).

---

## Segmentation notebook handoff (Layer 2)

After each full run, read **`layer1_segmentation_notebook_manifest.json`** at the run root:

```json
{
  "subject_id": "671",
  "session_id": "T1_P1_R1",
  "run_key": "671_T1_P1_R1",
  "input_csv": "data/671/671_T1_P1_R1_Take ...csv",
  "frame_rate_hz": 120.0,
  "n_frames": 30604,
  "frame_index_column": "frame",
  "time_column": "time_s",
  "qc_mask_csv": "tables/qc_mask.csv",
  "qc_mask_intervals_csv": "tables/qc_mask_intervals.csv",
  "alignment_notes": "Join Layer 2 Stage 08 parquet on frame (preferred) or time_s",
  "run_output_dir": "outputs/runs/671_T1_P1_R1_..."
}
```

**Join Layer 2 Stage 08 parquet** on `frame` (preferred) or `time_s` from `tables/qc_mask.csv`. Use `status` and `flag_*` columns to filter or flag frames downstream; the mask is advisory and does not modify the raw CSV.

---

## Per-batch output manifest (Layer 6)

```
outputs/batch_runs/batch_{YYYYMMDD_HHMMSS}/
├── BATCH_MANIFEST.json
├── dataset_eda_report.md
├── dataset_eda_report.csv
├── dataset_quality_report.html          ← cross-session HTML
├── failures.csv                         ← if any session failed
├── config_snapshot.yaml
├── plots/batch_*.png
├── sessions/{subject_id}_{session_id}.json   ← pointers to per-session runs/
└── details/
    ├── {subject}_{session}_qc_mask_intervals.csv
    ├── top_markers_by_session.csv
    ├── artifact_type_distribution.csv
    └── velocity_by_body_segment.csv
```

Per-session **`qc_mask.csv`** remains in each `outputs/runs/671_T1_P1_R1_*/tables/` folder — the batch package aggregates metrics and interval CSVs, not the full frame mask.

---

## Pipeline architecture

**Execution order (v0.5+):** L1 → L2 → **L4** → **L3** → L5

```
CSV under data/{subject_id}/
   │
   ▼
Layer 1  Parse + marker inventory
Layer 2  Gaps, missingness, frame QC mask (full tier)
Layer 4  Kinematic artifact candidates → events
Layer 3  Fixed windows (0.5 s, 1.0 s)
Layer 5  qc_report.md, qc_mask, qc_mask_intervals
   │
   └─► Layer 6  Cross-session batch aggregator
```

| Layer | Module | Role |
|-------|--------|------|
| L1 | `motive_qc/parse.py` | Read Motive CSV; build `MotiveSession` |
| L2 | `motive_qc/gaps.py` | Gap events, summaries, `frame_qc_mask` (full tier) |
| L4 | `motive_qc/artifacts.py` | Velocity/spike/hold screening → `artifact_events` |
| L3 | `motive_qc/windows.py` | Window bins + combined L2+L4 flags |
| L5 | `motive_qc/report.py` | `qc_mask`, intervals, markdown report |
| L6 | `motive_qc/batch.py` | Cross-session orchestration + executive EDA |

Entry points: [`motive_raw_qc.py`](motive_raw_qc.py) (single session), [`motive_batch_qc.py`](motive_batch_qc.py) (batch)

---

## Configuration reference (`config.yaml`)

Key output settings:

| Key | Default | Description |
|-----|---------|-------------|
| `outputs.tier` | `essential` | `essential` or `full` (debug tables) |
| `outputs.write_html_report` | `true` | Write `qc_report.html` per session |
| `outputs.fail_on_html_error` | `false` | If `true`, HTML failure fails the run |
| `reporting.stop_after_layer` | `5` | `2` = L1–L2 only; `5` = full pipeline |
| `paths.use_timestamp_subfolder` | `true` | `{subject_id}_{session_id}_{timestamp}/` |

All scientific thresholds live in config — see [`config.yaml`](config.yaml) and the full spec for gaps, artifacts, windows, readiness, and marker groups.

---

## Interactive QC (notebooks)

| Notebook | Purpose |
|----------|---------|
| [`notebooks/01_raw_csv_qc_layers_1_2.ipynb`](notebooks/01_raw_csv_qc_layers_1_2.ipynb) | Layers 1–2 validation |
| [`notebooks/02_raw_csv_qc_layers_3_5.ipynb`](notebooks/02_raw_csv_qc_layers_3_5.ipynb) | Full L1–L5 + batch picker |

Open from the project root so `config.yaml` resolves correctly.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Batch `--discover` finds 0 sessions | Copy CSVs into `data/{subject_id}/`, not flat `data/` |
| `Input CSV not found` | Use `--input` with path under `data/671/...` or fix `paths.input_csv` |
| Matplotlib font/cache errors | Set `MPLCONFIGDIR` to a writable directory |
| No `qc_mask.csv` | Run full L1–L5 (`stop_after_layer: 5`); mask is Layer 5 |
| No `qc_report.html` | Check logs for HTML warning; essential CSVs still written unless `fail_on_html_error: true` |
| Exit code 1 | QC validation failed — see stderr / `qc_report.md` |

---

## Artifact detection & tuning (expressive movement)

Defaults target expressive motion (e.g. Gaga) — flags extreme kinematic outliers, not normal fast movement.

- **Vel MAD σ** (`velocity_mad_multiplier`): higher = looser (fewer flags)
- **Vel percentile** (`velocity_percentile_threshold`): higher = looser
- Keep **acceleration_mad** off unless investigating accel-specific glitches
- Use notebook 02 or per-segment **velocity histograms** before tightening thresholds

Reason codes: [`motive_qc/reason_codes.py`](motive_qc/reason_codes.py) → `qc_reason_codes.md` each run.

---

## Python API (selected)

```python
from pathlib import Path
from motive_qc import load_config, run_full_pipeline

config = load_config("config.yaml")
config["_base_dir"] = Path(".").resolve()
layer1, layer2, layer3, layer4, layer5, files = run_full_pipeline(config, verbose=True)
```

Batch:

```python
from motive_qc import discover_sessions, run_batch, load_config

config = load_config("config.yaml")
config["_base_dir"] = Path(".").resolve()
result = run_batch(config, subject_ids=["671"], verbose=True)
```

---

## Validation workflow

1. **Notebook 01** — approve parse + gaps (Layers 1–2).
2. **Notebook 02** or CLI — full pipeline; review `qc_mask.csv`, artifact events, intervals.
3. Use **`layer1_segmentation_notebook_manifest.json`** to load mask into Layer 2 segmentation notebook.
4. Sign off via validation log → `docs/VALIDATION_LOG.md`.

The pipeline **does not** modify raw CSV data or automatically exclude frames — it produces evidence and recommendations for human decisions before Motive preprocessing and PCA/jPCA.

---

## License / citation

Academic QC tooling for OptiTrack Motive raw exports. Cite session `qc_report.md`, `config_used.yaml`, `layer1_segmentation_notebook_manifest.json`, and `RUN_MANIFEST.json` for reproducibility.
