# Poster Reproduction Path Check — Stage B.5

**Date:** 2026-06-30  
**Method:** Static inspection of poster scripts + filesystem existence checks (no script execution, no heavy computation).

---

## Scripts inspected

| Script | Output directory |
|--------|------------------|
| `scripts/make_poster_final_figures.py` | `outputs/poster_final_figures/` |
| `scripts/make_poster_671_figures.py` | `outputs/poster_final_figures/` (imports helpers from final-figures script) |

---

## Search path configuration (`make_poster_final_figures.py`)

```python
SEARCH_DIRS = [
    PROJECT_ROOT / "Layer3_JcvPCA/outputs/poster_ready_evidence_package",
    PROJECT_ROOT / "Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319",
    PROJECT_ROOT / "Layer3_JcvPCA/outputs",
    PROJECT_ROOT / "outputs",
    PROJECT_ROOT,
]
OUT_DIR = PROJECT_ROOT / "outputs/poster_final_figures"
```

| Path | Exists? | Notes |
|------|---------|-------|
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | **Yes** | Primary CSV source |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | **Yes** | Canonical batch — **explicitly referenced** |
| `Layer3_JcvPCA/outputs/` | **Yes** | Fallback search |
| `outputs/` | **Yes** | Fallback |
| `outputs/poster_final_figures/` | **Yes** | Write target |

**Canonical batch `193319`:** Referenced directly in `SEARCH_DIRS[1]` and in `make_poster_671_figures.py` JRW audit path.

---

## CSV inputs — `make_poster_final_figures.py`

| CSV | Required for | Found at | Status |
|-----|--------------|----------|--------|
| `longitudinal_delta_nv_ratio_by_link.csv` | Figure A | `poster_ready_evidence_package/` | OK |
| `body_region_anatomical_family_summary.csv` | Figure B | `poster_ready_evidence_package/` | OK |
| `nullspace_top7_links_all_contexts.csv` | Figure B annotations | `poster_ready_evidence_package/` | OK |
| `natural_variability_scalar_poster_table.csv` | Figure C | `poster_ready_evidence_package/` | OK |
| `concentration_metrics_all_analyses.csv` | Figure C | `poster_ready_evidence_package/` | OK |
| `directional_robustness_t1_t2_summary.csv` | Figure D | `gaga_batch_jcvpca_20260626_193319/` | OK |
| `directional_robustness_t1_t3_summary.csv` | Figure D | `gaga_batch_jcvpca_20260626_193319/` | OK |
| `directional_robustness_t2_t3_summary.csv` | Figure D | `gaga_batch_jcvpca_20260626_193319/` | OK |
| `direction_vs_magnitude_integrated_report.csv` | Figure D | `poster_ready_evidence_package/` | OK |
| `poster_takehome_numeric_summary.csv` | Supplementary | `poster_ready_evidence_package/` | OK |

All 10 CSVs resolve via `find_csv()` without modification.

---

## Additional paths — `make_poster_671_figures.py`

| Path / CSV | Purpose | Status |
|------------|---------|--------|
| `longitudinal_delta_nv_ratio_by_link.csv` | Figure 1 | OK (evidence package) |
| `natural_variability_scalar_poster_table.csv` | Figure 2 | OK |
| `body_region_anatomical_family_summary.csv` | Figures 3–4 | OK |
| `nullspace_top7_links_all_contexts.csv` | Annotations | OK |
| `nullspace_noise_vs_structure_diagnostic.csv` | Figure 4 | OK (evidence package) |
| `nullspace_threshold_stability_summary.csv` | Referenced in captions/docs | OK (evidence package) |
| Hard-coded JRW audit: `.../193319/comparisons/671_B_L1_T1_vs_T2/run/link_level_jrw_rss.csv` | Fig 1 PP conversion check | **OK** |

---

## Hard-coded / fragile paths

| Path pattern | Fragility | Impact if broken |
|--------------|-----------|------------------|
| `gaga_batch_jcvpca_20260626_193319` in `SEARCH_DIRS` and 671 JRW path | **High** — batch folder name baked in | Poster scripts fail if batch renamed/moved |
| Superseded batch folders | None — moved to `archive/` in Stage B | No impact (not referenced) |
| `reevluate_project/` | None — not used by poster scripts | No impact |
| `find_csv()` fallback to `Layer3_JcvPCA/outputs/` | Low | Could pick wrong file if duplicate CSV names appear in multiple batch folders — only `193319` remains in outputs now |

**Stage B impact:** Moving superseded batches **removed duplicate batch folders** from `Layer3_JcvPCA/outputs/`, reducing risk of `find_csv()` resolving the wrong file.

---

## Existing poster outputs (regeneration baseline)

| Item | Path | Exists? |
|------|------|---------|
| Combined panel PDF | `outputs/poster_final_figures/final_4figure_poster_panel_portrait.pdf` | Yes |
| Figure A–D assets | `outputs/poster_final_figures/figure_*` | Yes |
| 671 figure set | `outputs/poster_final_figures/poster_671_figure*` | Yes |
| Plot tables | `outputs/poster_final_figures/figure_*_plot_table.csv` | Yes |
| Captions | `final_figure_captions.md`, `poster_671_captions.md` | Yes |

Existing outputs confirm a prior successful run; Stage B.5 did not remove any of these.

---

## Broken paths

**None detected.**

All required input directories, canonical batch path, evidence package CSVs, directional robustness summaries in batch `193319`, and 671 JRW audit file exist on disk.

---

## Poster reproduction safety assessment

| Question | Answer |
|----------|--------|
| Can poster scripts find all CSV inputs? | **Yes** |
| Is canonical batch `193319` intact? | **Yes** (3.6 GB, 72 comparison dirs) |
| Is evidence package intact? | **Yes** (~908 KB) |
| Did Stage B break any referenced path? | **No** |
| Is reproduction safe without re-running Layer 3 batch? | **Yes** — scripts read existing CSVs only |
| Fragile dependency | Batch folder name `gaga_batch_jcvpca_20260626_193319` hard-coded — do not rename |

**Overall:** Poster reproduction appears **safe** for a CSV-driven re-run of `make_poster_final_figures.py` and `make_poster_671_figures.py`.

---

## Not tested in this check

- Actual execution of poster scripts (matplotlib render, validation logic pass/fail)
- Font / `adjustText` optional dependency behavior
- Whether regenerated figures match prior PDFs byte-for-byte

Recommend a lightweight smoke test (`python scripts/make_poster_final_figures.py`) only when user explicitly requests — not part of Stage B.5.

---

*Static path check only. No analysis code modified.*
