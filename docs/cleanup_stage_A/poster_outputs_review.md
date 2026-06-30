# Poster Outputs Review — Stage A

**Date:** 2026-06-30  
**Scope:** Poster figures, evidence packages, generator scripts, and upstream CSV dependencies.

---

## 1. Final poster figures (deliverables)

**Location:** `outputs/poster_final_figures/`  
**Size:** ~13 MB, **48 files**

### Primary figure assets

| Asset | Formats | Role |
|-------|---------|------|
| `figure_A_longitudinal_shift_vs_NV` | PDF, PNG, SVG | Longitudinal delta vs natural variability (671 flagship in standalone A) |
| `figure_B_functional_vs_nullspace_family` | PDF, PNG, SVG | Functional vs null-space family comparison |
| `figure_C_movement_organization_metrics` | PDF, PNG, SVG | Movement organization metrics |
| `figure_D_directional_robustness` | PDF, PNG, SVG | Directional robustness summary |
| `final_4figure_poster_panel_portrait` | PDF, PNG, SVG | Combined 4-panel poster layout (90×180 cm portrait) |

### Participant 671 supplementary set (same folder)

| Asset | Formats |
|-------|---------|
| `poster_671_figure1_longitudinal_vs_NV` | PDF, PNG, SVG |
| `poster_671_figure2_nv_magnitude_gini` | PDF, PNG, SVG |
| `poster_671_figure3_functional_nullspace_family` | PDF, PNG, SVG |
| `poster_671_figure4_nullspace_sensitivity` | PDF, PNG, SVG |

### Plot tables (reproducibility audit trail)

- `figure_A_plot_table.csv`, `figure_B_plot_table.csv`, `figure_C_plot_table.csv`, `figure_D_plot_table.csv`
- `figure_D_sign_agreement_long.csv`, `figure_D_direction_vs_magnitude_counts.csv`
- `poster_671_figure1_plot_table.csv`, `poster_671_figure1_distribution_summary.csv`
- `poster_671_figure2_plot_table.csv`, `poster_671_figure3_plot_table.csv`, `poster_671_figure4_plot_table.csv`

### Documentation in folder

- `final_figure_captions.md`
- `poster_671_captions.md`
- `poster_671_figure1_logic.md`
- `poster_671_validation_report.md`
- `combined_panel_readability_check.md`
- `data_validation_report.md`
- `optional_extra_figure_recommendations.md`

**Preserve because:** These are the publication-facing outputs and their validated plot tables document exact plotted values.

---

## 2. Evidence packages (upstream CSV sources)

### `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` (~908 KB)

Curated CSV inputs used by poster scripts. Key files:

| CSV | Used by figure |
|-----|----------------|
| `longitudinal_delta_nv_ratio_by_link.csv` | Figure A |
| `body_region_anatomical_family_summary.csv` | Figure B |
| `nullspace_top7_links_all_contexts.csv` | Figure B (PC-count annotations) |
| `natural_variability_scalar_poster_table.csv` | Figure C |
| `concentration_metrics_all_analyses.csv` | Figure C |
| `directional_robustness_t1_t2_summary.csv` | Figure D |
| `directional_robustness_t1_t3_summary.csv` | Figure D |
| `directional_robustness_t2_t3_summary.csv` | Figure D |
| `direction_vs_magnitude_integrated_report.csv` | Figure D |
| `poster_takehome_numeric_summary.csv` | Supplementary take-home table |

Also includes: `poster_ready_evidence_report.md`, `poster_master_figure_data_index.md`, nullspace diagnostic CSVs, longitudinal link delta tables.

**Preserve because:** Primary curated inputs; regenerating requires re-running multiple Layer 3 report scripts against batch `193319`.

### `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/`

Secondary search path for poster scripts. Supplies directional robustness full numeric reports and:

- `poster_plot_shortlist.md`
- `poster_scientific_story_and_figure_plan.md`
- Raw directional robustness CSVs if evidence package is incomplete

**Preserve because:** Canonical batch; referenced in `make_poster_final_figures.py` `SEARCH_DIRS`.

### `Layer3_JcvPCA/outputs/671_g4_validation_001/`

First validation run (documented in Layer 3 README). Contains early JcvPCA tables and plots for participant 671 Group 4.

**Preserve because:** Historical validation reference; not primary poster source but supports methods narrative.

---

## 3. Generator scripts

| Script | Output dir | Imports / depends on |
|--------|------------|---------------------|
| `scripts/make_poster_final_figures.py` | `outputs/poster_final_figures/` | `poster_ready_evidence_package/`, batch `193319/`, `find_csv()` search |
| `scripts/make_poster_671_figures.py` | `outputs/poster_final_figures/` | Imports shared helpers from `make_poster_final_figures.py`; same CSV sources |

**Search order in `make_poster_final_figures.py`:**

1. `Layer3_JcvPCA/outputs/poster_ready_evidence_package/`
2. `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/`
3. `Layer3_JcvPCA/outputs/`
4. `outputs/`
5. Project root

**Do not modify** in Stage A/B; scripts are part of active reproducibility chain.

---

## 4. CSVs required to reproduce poster figures

Minimum set (from script `find_csv()` calls):

1. `longitudinal_delta_nv_ratio_by_link.csv`
2. `body_region_anatomical_family_summary.csv`
3. `nullspace_top7_links_all_contexts.csv`
4. `natural_variability_scalar_poster_table.csv`
5. `concentration_metrics_all_analyses.csv`
6. `directional_robustness_t1_t2_summary.csv`
7. `directional_robustness_t1_t3_summary.csv`
8. `directional_robustness_t2_t3_summary.csv`
9. `direction_vs_magnitude_integrated_report.csv`
10. `poster_takehome_numeric_summary.csv` (supplementary)

If these remain in `poster_ready_evidence_package/`, poster figures are regeneratable even if batch comparison `.npy` files are archived.

---

## 5. Redundant or older poster-related outputs

| Item | Assessment | Recommendation |
|------|------------|----------------|
| `outputs/poster_final_figures/` PNG+PDF+SVG triplets | Intentional multi-format delivery, not redundant | Keep all formats until poster submission format finalized |
| Batch runs pre-193319 | No poster reports | Archive later; not poster inputs |
| `671_g4_validation_001/plots/` | Superseded by final poster figures for publication | Keep for validation audit; low priority |
| Plot tables in `poster_final_figures/` vs evidence package CSVs | Plot tables are **derived outputs** of figures; evidence package holds **source** data | Keep both until regeneration verified |
| `Layer3_JcvPCA/docs/figures/jcvpca_workflow/jcvpca_workflow_schematic.svg` | Methods schematic, not data figure | Keep active (methods poster panel) |

**No checksum duplicates detected** between `poster_ready_evidence_package/` CSVs and `figure_*_plot_table.csv` — plot tables are aggregated subsets derived at render time.

---

## 6. Files that must be preserved (poster conclusions)

**Tier 1 — required for numeric reproducibility:**

- Entire `poster_ready_evidence_package/` folder
- Batch `193319` root CSV/MD reports (especially directional robustness + NV reports)
- `scripts/make_poster_final_figures.py` and `scripts/make_poster_671_figures.py`

**Tier 2 — required for visual deliverables:**

- `outputs/poster_final_figures/` final PDF/SVG/PNG files
- `final_figure_captions.md`, `poster_671_captions.md`
- All `figure_*_plot_table.csv` and `poster_671_*_plot_table.csv`

**Tier 3 — supporting narrative:**

- `poster_scientific_story_and_figure_plan.md` (in batch 193319)
- `poster_plot_shortlist.md`
- `FINAL_integrated_deep_review_after_p50_p60.md`

**Do not archive before poster submission:** Tiers 1–2. Tier 3 can move to docs after submission if CSV sources remain.
