# R7.2 — Commit Plan (do not run yet)

**Date:** 2026-06-30  
**Purpose:** Record read-only Layer 3 report path refactor for explicit staging when ready.

---

## Suggested commit message

```
refactor: load read-only Layer 3 report paths from config

Add layer3_batch_report_paths helper and wire integrated, master, and
natural-variability report generators to project_paths with validate/dry-run
CLI modes; no change to report logic.
```

---

## Files to stage

```bash
git add \
  Layer3_JcvPCA/scripts/layer3_batch_report_paths.py \
  Layer3_JcvPCA/scripts/generate_final_integrated_review.py \
  Layer3_JcvPCA/scripts/generate_master_full_numeric_report.py \
  Layer3_JcvPCA/scripts/generate_natural_variability_full_numeric_report.py \
  docs/research_recovery/R7_2_READONLY_REPORT_REFACTOR.md \
  docs/research_recovery/R7_2_COMMIT_PLAN.md
```

**Expected staged count:** 6 files

---

## Files NOT to stage

| Category | Examples |
|----------|----------|
| Path loader (R6.1) | `src/project_paths.py`, `scripts/check_project_paths.py` |
| Poster / evidence scripts (R7.0.1, R7.1.1) | `scripts/make_poster_*.py`, `generate_poster_*` |
| Skipped Layer 3 scripts | `analyze_*`, `run_gaga_batch_jcvpca.py`, `generate_pc_focus_review.py`, DR report scripts not refactored in R7.2 |
| Layer 3 / 2.5 source (unrelated) | `Layer3_JcvPCA/src/**`, `Layer2.5_Segmentation/**` |
| Generated outputs | `Layer3_JcvPCA/outputs/**`, canonical batch MD/CSV |
| Archive deletions | `Layer2_Motive_Kinematics/outputs/archive/**` |
| Raw data | any `data/` trees |

---

## Pre-commit verification

```bash
python scripts/check_project_paths.py
python3 -m py_compile \
  Layer3_JcvPCA/scripts/layer3_batch_report_paths.py \
  Layer3_JcvPCA/scripts/generate_final_integrated_review.py \
  Layer3_JcvPCA/scripts/generate_master_full_numeric_report.py \
  Layer3_JcvPCA/scripts/generate_natural_variability_full_numeric_report.py
git diff --cached --name-only
```

Expected staged paths only:

```
Layer3_JcvPCA/scripts/generate_final_integrated_review.py
Layer3_JcvPCA/scripts/generate_master_full_numeric_report.py
Layer3_JcvPCA/scripts/generate_natural_variability_full_numeric_report.py
Layer3_JcvPCA/scripts/layer3_batch_report_paths.py
docs/research_recovery/R7_2_COMMIT_PLAN.md
docs/research_recovery/R7_2_READONLY_REPORT_REFACTOR.md
```

Optional (Layer 3 venv):

```bash
cd Layer3_JcvPCA/scripts
python generate_final_integrated_review.py --validate-paths
python generate_master_full_numeric_report.py --dry-run
```

Do **not** run full report generation in the commit workflow.

If anything else is staged:

```bash
git restore --staged <unwanted-path>
```

---

## Post-commit checks

```bash
git status --short
```

Working tree will remain **not clean**.

---

## Rules reminder

- No `git add .`
- No report regeneration
- No heavy analysis
- No file moves or deletions
