# Layer 2.5 — Segmentation and pre-JcvPCA outputs

Outputs from segmentation validation, interactive notebook review, and pre-JcvPCA window export.

## What is included in Git

| Folder | Contents |
|--------|----------|
| `segmentation_validation/671_T1_P1_R1/` | Input validation report, checks CSV, summary JSON |
| `pre_jvcpca_review/session_window/` | Window decision tables, mapping logic, JcvPCA matrix summary, preview XLSX, export manifest |
| `pre_jvcpca_review/smoke/` | Smoke-test summary tables |
| `notebook_review/*/window_review_report.md` | Per-window validation reports from development runs |
| `notebook_review/*/window_validation_summary.json` | Per-window validation summaries |
| `window_review/*/window_review_report.md` | Window review reports |

## What is excluded from Git

| Pattern | Typical size | Reason |
|---------|-------------|--------|
| `*.parquet` | 0.5–134 MB | Window rotvec matrices; regenerate from notebook |
| `combined_qc_events.csv` | 5–63 MB | Frame-level QC event dump from debug runs |
| `qc_event_display.csv` | 5–10 MB | Frame-level QC display table from debug runs |

The `combined_qc_events.csv` files in `notebook_review/` and `window_review/` are development/debug artifacts. Regenerate by running the segmentation review notebook with the desired frame window.

## Key deliverable for Layer 3

The curated pre-JcvPCA export lives at:

```text
pre_jvcpca_review/session_window/
  window_jvcpca_matrix_summary.md      ← in Git
  window_jvcpca_matrix_preview.xlsx    ← in Git (~600 KB)
  window_export_manifest.json          ← in Git
  window_decision_summary.csv          ← in Git
  window_jvcpca_matrix.parquet         ← excluded; regenerate locally
```

## How to regenerate

1. Ensure Layer 1 QC and Layer 2 exports are in `input/`.
2. Open `notebooks/post_layer2_segmentation_review.ipynb` for window selection.
3. Open `notebooks/pre_jvcpca_review.ipynb` for matrix export.

Or run validation CLI:

```bash
python scripts/validate_segmentation_inputs.py \
  --layer1-dir input/Layer1_QC/QC_671_T1_P1_R1 \
  --layer2-dir input/Layer2_Kinematics/671_T1_P1_R1 \
  --out outputs/segmentation_validation/671_T1_P1_R1
```
