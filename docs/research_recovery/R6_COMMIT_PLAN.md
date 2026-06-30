# R6 — Commit Plan (do not run yet)

**Date:** 2026-06-30  
**Purpose:** Record research path loader checkpoint for explicit staging when ready.

---

## Suggested commit message

```
feat: add project path loader and validation script

Introduce src/project_paths.py to load config/paths.yaml with required vs
optional path checks, plus scripts/check_project_paths.py for lightweight
validation before refactors.
```

Shorter alternative (if preferred):

```
feat: add config-driven project path loader
```

---

## Files to stage

```bash
git add \
  src/__init__.py \
  src/project_paths.py \
  scripts/check_project_paths.py \
  docs/research_recovery/R6_PROJECT_PATH_LOADER.md \
  docs/research_recovery/R6_COMMIT_PLAN.md
```

**Expected staged count:** 5 files

---

## Files NOT to stage

Do **not** include any of the following in this commit:

| Category | Examples |
|----------|----------|
| Analysis code changes | `Layer2.5_Segmentation/src/**`, `Layer3_JcvPCA/src/**`, `Layer3_JcvPCA/scripts/**` |
| Modified outputs | `Layer2.5_Segmentation/outputs/**`, `Layer3_JcvPCA/outputs/**` |
| Layer 2 archive deletions | `Layer2_Motive_Kinematics/outputs/archive/**` (R1 move — separate git hygiene commit) |
| Raw data | `Layer2_Motive_Kinematics/data/**`, `671_test_data_des/**` |
| Untracked Layer 3 scripts | bulk `?? Layer3_JcvPCA/scripts/*.py` |
| Config already committed | `config/paths.yaml` (committed in R5.1) |
| Poster binaries | `outputs/poster_final_figures/**` |
| Other research recovery docs | R1–R5 (already in R5.1 commit) |
| Working tree noise | notebooks, dashboards, indices, PDFs |

---

## Pre-commit verification

```bash
git diff --cached --name-only
```

Expected output (only):

```
docs/research_recovery/R6_COMMIT_PLAN.md
docs/research_recovery/R6_PROJECT_PATH_LOADER.md
scripts/check_project_paths.py
src/__init__.py
src/project_paths.py
```

If anything else appears:

```bash
git restore --staged <unwanted-path>
```

---

## Post-commit checks

```bash
python scripts/check_project_paths.py
git status --short
```

Path check should exit `0`. Working tree will remain **not clean** (pending Layer 2.5/3 code commit, archive deletions, etc.).

---

## Suggested follow-up commits (later, not R6)

| Stage | Content |
|-------|---------|
| R7 | Pilot script refactor to use `project_paths` |
| R10 | `git rm --cached` for legacy outputs + archive paths |
| Commit 2 | Layer 2.5 / Layer 3 source per R5 status doc |

---

## Rules reminder

- No `git add .`
- No analysis runs in commit workflow
- No file moves or deletions in R6 commit
