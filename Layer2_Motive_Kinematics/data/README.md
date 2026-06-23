# Layer 2 — Input Motive CSV data

Place **Motive mixed CSV exports** (with global bone quaternions) here for Layer 2 kinematic processing:

```text
data/
  671/
    671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv
    ...
```

## What is excluded from Git

All `*.csv` files under `data/` are **gitignored**. These are full-resolution Motive exports (typically 200+ MB) with frame-level marker and quaternion data.

## What is included in Git

- This README
- Small test fixtures under `tests/fixtures/` (synthetic headers and QC cases)

## Example outputs (in Git)

Stage-by-stage reports and small summary CSVs for session `671_T1_P1_R1` are included under:

```text
outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/
outputs/layer2_exports/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001/
```

Large intermediate files (parquet, frame-level kinematic CSVs) are excluded — see [`outputs/README.md`](../outputs/README.md).

## How to regenerate

```bash
layer2-motive run-until \
  --input data/671/671_T1_P1_R1_Take\ 2026-01-06\ 03.57.12\ PM_001.csv \
  --stage 08 \
  --output-dir outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001
```

See [`scripts/README.md`](../scripts/README.md) for batch commands.
