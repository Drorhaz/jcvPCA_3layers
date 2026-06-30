# R7.3 — Commit Plan (do not run yet)

**Date:** 2026-06-30  
**Purpose:** Record directional robustness + nullspace report path refactor for explicit staging when ready.

---

## Suggested commit message

```
refactor: load directional robustness and nullspace report paths from config

Wire three directional-robustness and nullspace full-numeric report scripts
to layer3_batch_report_paths; extend preflight for review-folder inputs;
no change to report logic.
```

---

## Files to stage

```bash
git add \
  Layer3_JcvPCA/scripts/layer3_batch_report_paths.py \
  Layer3_JcvPCA/scripts/generate_directional_robustness_full_numeric_report.py \
  Layer3_JcvPCA/scripts/generate_directional_robustness_t1_t2_full_numeric_report.py \
  Layer3_JcvPCA/scripts/generate_directional_robustness_t2_t3_full_numeric_report.py \
  Layer3_JcvPCA/scripts/generate_nullspace_full_numeric_report.py \
  docs/research_recovery/R7_3_SAFE_REPORT_REFACTOR.md \
  docs/research_recovery/R7_3_COMMIT_PLAN.md
```

**Expected staged count:** 7 files

---

## Files NOT to stage

| Category | Examples |
|----------|----------|
| R7.2 report scripts (already committed) | `generate_final_integrated_review.py`, `generate_master_full_numeric_report.py`, `generate_natural_variability_full_numeric_report.py` |
| Path loader (R6.1) | `src/project_paths.py`, `config/paths.yaml`, `scripts/check_project_paths.py` |
| Poster / evidence (R7.0.1, R7.1.1) | `scripts/make_poster_*.py`, `generate_poster_*` |
| Skipped Layer 3 scripts | `analyze_*`, `run_gaga_batch_jcvpca.py`, `generate_pc_focus_review.py`, `generate_movement_organization_question_report.py` |
| Layer 3 / 2.5 source (unrelated) | `Layer3_JcvPCA/src/**`, `Layer2.5_Segmentation/**` |
| Generated outputs | `Layer3_JcvPCA/outputs/**`, canonical batch MD/CSV, nullspace review CSVs |
| Archive deletions | `Layer2_Motive_Kinematics/outputs/archive/**` |
| Raw data | any `data/` trees |

---

## Pre-commit verification

```bash
python scripts/check_project_paths.py
python3 -m py_compile \
  Layer3_JcvPCA/scripts/layer3_batch_report_paths.py \
  Layer3_JcvPCA/scripts/generate_directional_robustness_full_numeric_report.py \
  Layer3_JcvPCA/scripts/generate_directional_robustness_t1_t2_full_numeric_report.py \
  Layer3_JcvPCA/scripts/generate_directional_robustness_t2_t3_full_numeric_report.py \
  Layer3_JcvPCA/scripts/generate_nullspace_full_numeric_report.py
git diff --cached --name-only
```

Expected staged paths only:

```
Layer3_JcvPCA/scripts/generate_directional_robustness_full_numeric_report.py
Layer3_JcvPCA/scripts/generate_directional_robustness_t1_t2_full_numeric_report.py
Layer3_JcvPCA/scripts/generate_directional_robustness_t2_t3_full_numeric_report.py
Layer3_JcvPCA/scripts/generate_nullspace_full_numeric_report.py
Layer3_JcvPCA/scripts/layer3_batch_report_paths.py
docs/research_recovery/R7_3_COMMIT_PLAN.md
docs/research_recovery/R7_3_SAFE_REPORT_REFACTOR.md
```

Optional (Layer 3 env with numpy/pandas):

```bash
cd Layer3_JcvPCA/scripts
python generate_directional_robustness_full_numeric_report.py --validate-paths
python generate_nullspace_full_numeric_report.py --dry-run
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
- No commit until explicitly requested
