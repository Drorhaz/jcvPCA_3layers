# Layer 1 — Raw Motive data

Place **raw OptiTrack Motive marker XYZ CSV exports** here, organized by subject:

```text
data/
  671/
    671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv
    ...
  252/
    ...
  archive/    # excluded from batch discovery
```

## What is excluded from Git

All `*.csv` files under `data/` are **gitignored** because they are full-resolution Motive exports (typically 100–230 MB each) containing frame-level participant capture data.

## What is included in Git

- This README
- Folder structure (empty subject directories may not appear until populated locally)

## Example QC outputs (in Git)

A complete Layer 1 run for session `671_T1_P1_R1` is included under:

```text
outputs/runs/671_T1_P1_R1_20260619_192857/
```

This includes `qc_mask.csv`, summary tables, plots, HTML report, and `layer1_segmentation_notebook_manifest.json`.

## How to regenerate

1. Copy Motive CSVs into `data/{subject_id}/`.
2. Run the QC pipeline:

```bash
python motive_raw_qc.py --config config.yaml --verbose \
  --input "data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv"
```

Or batch:

```bash
python motive_batch_qc.py --config config.yaml --subject 671 --verbose
```

See the project [`README.md`](../README.md) for full setup.
