# R7 — Commit Plan (do not run yet)

**Date:** 2026-06-30  
**Purpose:** Record pilot poster-script path refactor for explicit staging when ready.

---

## Suggested commit message

```
refactor: load poster script paths from config registry

Wire make_poster_final_figures.py and make_poster_671_figures.py to
project_paths / config/paths.yaml with optional CLI overrides; no change
to plotting or analysis logic.
```

---

## Files to stage

```bash
git add \
  scripts/make_poster_final_figures.py \
  scripts/make_poster_671_figures.py \
  docs/research_recovery/R7_PILOT_REFACTOR.md \
  docs/research_recovery/R7_COMMIT_PLAN.md
```

**Expected staged count:** 4 files

---

## Files NOT to stage

| Category | Examples |
|----------|----------|
| Path loader (already committed R6.1) | `src/project_paths.py`, `scripts/check_project_paths.py` |
| Config registry (R5.1) | `config/paths.yaml` |
| Layer 3 analysis scripts | `Layer3_JcvPCA/scripts/*.py` (except if accidentally edited) |
| Layer 2.5 / Layer 3 source changes | `Layer*/src/**`, dashboards, notebooks |
| Generated outputs | `outputs/poster_final_figures/**`, `Layer3_JcvPCA/outputs/**` |
| Archive deletions | `Layer2_Motive_Kinematics/outputs/archive/**` |
| Raw data | any `data/` trees |
| Unrelated docs | R1–R6 docs unless intentionally updating index |

---

## Pre-commit verification

```bash
python scripts/check_project_paths.py
git diff --cached --name-only
```

Expected staged paths only:

```
docs/research_recovery/R7_COMMIT_PLAN.md
docs/research_recovery/R7_PILOT_REFACTOR.md
scripts/make_poster_671_figures.py
scripts/make_poster_final_figures.py
```

If anything else is staged:

```bash
git restore --staged <unwanted-path>
```

Optional smoke test (stdlib + path loader only):

```bash
python3 -c "
import sys; sys.path.insert(0,'src')
from project_paths import load_project_paths
p = load_project_paths()
assert p.layer3_canonical_batch.is_dir()
print('OK')
"
```

Do **not** run full poster figure generation in the commit workflow unless explicitly requested.

---

## Post-commit checks

```bash
git status --short
```

Working tree will remain **not clean** (pending Layer 2.5/3 code commit, archive deletions, etc.).

---

## Rules reminder

- No `git add .`
- No heavy analysis in commit workflow
- No file moves or deletions
- R7.1 is separate follow-up for additional scripts
