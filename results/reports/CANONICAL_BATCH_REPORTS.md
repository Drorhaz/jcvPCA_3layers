# Canonical batch reports index

**Batch ID:** `gaga_batch_jcvpca_20260626_193319`  
**Physical path:** `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/`  
**Config key:** `layer3.canonical_batch`

Frozen poster-era batch — **do not overwrite or delete.**

## Top-level markdown reports (14)

| Report | File |
|--------|------|
| Integrated deep review | `FINAL_integrated_deep_review_after_p50_p60.md` |
| Master full numeric | `Gaga_JcvPCA_MASTER_full_numeric_report.md` |
| PC focus interpretation | `PC_focus_p50_p60_interpretation_review.md` |
| Batch summary | `batch_summary.md` |
| Directional robustness T1–T2 | `directional_robustness_t1_t2_FULL_NUMERIC_REPORT.md` |
| Directional robustness T1–T3 | `directional_robustness_t1_t3_FULL_NUMERIC_REPORT.md` |
| Directional robustness review | `directional_robustness_t1_t3_review.md` |
| Batch interpretation | `gaga_batch_interpretation_report.md` |
| Joint heatmap numeric | `joint_heatmap_full_numeric_report.md` |
| Joint heatmap prep | `joint_heatmap_preparation_review.md` |
| Natural variability numeric | `natural_variability_FULL_NUMERIC_REPORT.md` |
| Natural variability deep dive | `natural_variability_deep_dive_report.md` |
| Poster plot shortlist | `poster_plot_shortlist.md` |
| Poster story plan | `poster_scientific_story_and_figure_plan.md` |

## Plots

Batch plots live under `plots/` (~2,500+ PNG). Not indexed here — browse via symlink [`../active/canonical_batch`](../active/canonical_batch) after P3.

## Validate (read-only)

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python generate_final_integrated_review.py --validate-paths
../.venv/bin/python generate_master_full_numeric_report.py --dry-run
```
