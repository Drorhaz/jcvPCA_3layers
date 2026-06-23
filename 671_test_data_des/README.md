# Test data descriptions

This folder holds a **data-description sidecar** for a sample Motive export used during Layer 2 parser development.

## Contents

| File | In Git? | Description |
|------|---------|-------------|
| `671_T1_P1_R1_Take ..._DataDescriptions.csv` | Yes (~10 KB) | Motive column metadata / data descriptions |
| `671_T1_P1_R1_Take ..._001.csv` | **No** (232 MB) | Full raw Motive export — excluded as heavy participant data |

## Why the raw CSV is excluded

The full-resolution Motive CSV exceeds GitHub's 100 MB file limit and contains frame-level participant capture data. It is not needed to understand the pipeline structure.

## How to regenerate / obtain

Place Motive CSV exports under `Layer1_motive_qc/motive_qc/data/{subject_id}/` or point Layer 2 at your local copy:

```bash
layer2-motive run-until --input /path/to/671_T1_P1_R1_Take*.csv --stage 08 --output-dir outputs/session_name
```

The `_DataDescriptions.csv` sidecar is kept in Git as a small reference for column structure.
