# Poster evidence package

**Physical path:** `Layer3_JcvPCA/outputs/poster_ready_evidence_package/`  
**Config key:** `layer3.poster_evidence_package`  
**Symlink (P3):** [`../poster/evidence_package`](../poster/evidence_package)

## CSV tables (poster inputs)

| File | Topic |
|------|-------|
| `body_region_anatomical_family_summary.csv` | Body region / family |
| `concentration_metrics_all_analyses.csv` | Concentration metrics |
| `direction_vs_magnitude_integrated_report.csv` | Direction vs magnitude |
| `longitudinal_delta_nv_ratio_by_link.csv` | Longitudinal NV delta |
| `longitudinal_delta_nv_ratio_top7.csv` | Top-7 longitudinal |
| `longitudinal_link_delta_allpc_poster_table.csv` | Link delta all-PC |
| `natural_variability_scalar_poster_table.csv` | NV scalar table |
| `natural_variability_timepoint_pattern_summary.csv` | NV timepoint pattern |
| `natural_variability_top7_links_by_timepoint_focus.csv` | NV top-7 by timepoint |
| `nullspace_explained_variance_weighting_check.csv` | Nullspace EV |
| `nullspace_noise_vs_structure_diagnostic.csv` | Nullspace noise |
| `nullspace_threshold_stability_summary.csv` | Nullspace thresholds |
| `nullspace_top7_links_all_contexts.csv` | Nullspace top-7 |

## Related

- Poster figures: [`../poster/FIGURE_MANIFEST.md`](../poster/FIGURE_MANIFEST.md)
- Canonical batch: [`../active/CANONICAL_BATCH.md`](../active/CANONICAL_BATCH.md)

## Regenerate

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python generate_poster_ready_evidence_package.py --help
```
