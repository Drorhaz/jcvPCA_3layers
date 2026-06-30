# Poster final figures manifest

**Physical path:** `outputs/poster_final_figures/`  
**Config key:** `poster.final_figures`  
**Symlink (P3):** [`final_figures`](final_figures)

## Figures A–D

| Figure | PDF | PNG | SVG | Data |
|--------|-----|-----|-----|------|
| A — Longitudinal shift vs NV | `figure_A_longitudinal_shift_vs_NV.pdf` | `.png` | `.svg` | `figure_A_plot_table.csv` |
| B — Functional vs nullspace | `figure_B_functional_vs_nullspace_family.pdf` | `.png` | `.svg` | `figure_B_plot_table.csv` |
| C — Movement organization | `figure_C_movement_organization_metrics.pdf` | `.png` | `.svg` | `figure_C_plot_table.csv` |
| D — Directional robustness | `figure_D_directional_robustness.pdf` | `.png` | `.svg` | `figure_D_plot_table.csv`, `figure_D_direction_vs_magnitude_counts.csv`, `figure_D_sign_agreement_long.csv` |

## Supporting docs

- `data_validation_report.md`
- `combined_panel_readability_check.md`

## Regenerate

```bash
python scripts/make_poster_final_figures.py --help
python scripts/make_poster_671_figures.py --help
```

**Size:** ~13 MB total (gitignored binaries).
