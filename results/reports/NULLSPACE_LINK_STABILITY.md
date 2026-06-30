# Nullspace link stability sidecar report

**Physical path:** `Layer3_JcvPCA/outputs/nullspace_link_stability_review/`  
**Symlink (P3):** [`nullspace_link_stability`](nullspace_link_stability)

## Files

| File | Purpose |
|------|---------|
| `nullspace_FULL_NUMERIC_REPORT.md` | Full numeric report |
| `nullspace_top7_full_numeric_report.md` | Top-7 focus report |
| `nullspace_anatomical_family_summary.csv` | Family summary |
| `nullspace_link_recurrence_summary.csv` | Link recurrence |
| `nullspace_threshold_stability_summary.csv` | Threshold stability |
| `nullspace_p50_p60_link_overlap.csv` | P50/P60 overlap |
| `nullspace_p50_p60_p70_link_overlap.csv` | P50/P60/P70 overlap |
| `nullspace_explained_variance_weighting_check.csv` | EV weighting |
| `nullspace_noise_diagnostic_summary.csv` | Noise diagnostic |
| `nullspace_top7_links_all_contexts.csv` | Top-7 all contexts |

## Validate

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python generate_nullspace_full_numeric_report.py --dry-run
../.venv/bin/python analyze_nullspace_link_stability.py --help
```
