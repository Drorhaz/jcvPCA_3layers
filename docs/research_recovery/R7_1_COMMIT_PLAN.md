# R7.1 — Commit Plan (do not run yet)

**Date:** 2026-06-30  
**Purpose:** Record evidence-package/report path refactor for explicit staging when ready.

---

## Suggested commit message

```
refactor: load evidence scripts from config paths

Wire Layer3 evidence package builder and markdown report generator to
project_paths / config/paths.yaml with optional CLI overrides; no change
to aggregation or report content logic.
```

---

## Files to stage

```bash
git add \
  Layer3_JcvPCA/scripts/generate_poster_evidence_report.py \
  Layer3_JcvPCA/scripts/generate_poster_ready_evidence_package.py \
  docs/research_recovery/R7_1_EVIDENCE_SCRIPT_REFACTOR.md \
  docs/research_recovery/R7_1_COMMIT_PLAN.md
```

**Expected staged count:** 4 files

---

## Files NOT to stage

| Category | Examples |
|----------|----------|
| Poster scripts (R7.0.1) | `scripts/make_poster_final_figures.py`, `scripts/make_poster_671_figures.py` |
| Path loader (R6.1) | `src/project_paths.py`, `scripts/check_project_paths.py` |
| Config registry (R5.1) | `config/paths.yaml` |
| Other Layer 3 analysis scripts | `Layer3_JcvPCA/scripts/generate_*`, `analyze_*`, `run_gaga_batch_jcvpca.py` |
| Layer 3 / 2.5 source changes | `Layer3_JcvPCA/src/**`, `Layer2.5_Segmentation/**` |
| Generated outputs | `Layer3_JcvPCA/outputs/**`, `outputs/poster_final_figures/**` |
| Archive deletions | `Layer2_Motive_Kinematics/outputs/archive/**` |
| Raw data | any `data/` trees |

---

## Pre-commit verification

```bash
python scripts/check_project_paths.py
python3 -m py_compile \
  Layer3_JcvPCA/scripts/generate_poster_evidence_report.py \
  Layer3_JcvPCA/scripts/generate_poster_ready_evidence_package.py
git diff --cached --name-only
```

Expected staged paths only:

```
Layer3_JcvPCA/scripts/generate_poster_evidence_report.py
Layer3_JcvPCA/scripts/generate_poster_ready_evidence_package.py
docs/research_recovery/R7_1_COMMIT_PLAN.md
docs/research_recovery/R7_1_EVIDENCE_SCRIPT_REFACTOR.md
```

Optional (Layer 3 venv):

```bash
cd Layer3_JcvPCA/scripts
python generate_poster_evidence_report.py --validate-paths
python generate_poster_ready_evidence_package.py --dry-run
```

Do **not** run full package generation in the commit workflow.

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
- No evidence package regeneration
- No heavy analysis
- No file moves or deletions
