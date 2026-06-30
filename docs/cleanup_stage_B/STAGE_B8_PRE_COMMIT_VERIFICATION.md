# Stage B.8 — Pre-Commit Verification

**Date:** 2026-06-30  
**Plan source:** `docs/cleanup_stage_B/STAGE_B7_COMMIT_PLAN_FINAL.md`  
**Commit message (planned):** `chore: checkpoint project cleanup through stage B`

---

## Commands run (staging)

All commands executed from repository root. No `git add .` used.

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project

# 1. Gitignore
git add .gitignore

# 2. Documentation
git add PROJECT_STATUS.md docs/PROJECT_AUDIT_DRAFT.md docs/CLEANUP_INDEX.md
git add docs/cleanup_stage_A/ docs/cleanup_stage_B/

# 3. Poster scripts + small poster artifacts
git add scripts/make_poster_final_figures.py scripts/make_poster_671_figures.py
git add outputs/poster_final_figures/*.csv outputs/poster_final_figures/*.md

# 4. Segmentation xlsx (new path)
git add Layer2.5_Segmentation/segmentation/671_ex_segmentatios_frames.xlsx
git add Layer2.5_Segmentation/segmentation/252_ex_segmentatios_frames.xlsx

# 5. Intentional deletions
git add -u Layer2.5_Segmentation/reevluate_project/
git add -u Layer2.5_Segmentation/671_ex_segmentatios_frames.xlsx
git add -u "Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/671_T1_P1_R2/671_T1_P1_R2_g4_s14040_e20880/mapping_logic_table.csv"
git add -u "Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/joint_overlap_table.csv"
```

---

## Verification commands run

```bash
git status --short
git diff --cached --stat
git diff --cached --name-only | grep '^archive/' && echo "STOP: archive staged" || echo "OK: no archive"
git diff --cached --name-only | grep -E '(/data/.*\.csv|671_test_data_des.*\.csv)' && echo "STOP: raw CSV staged" || echo "OK: no raw CSV"
git diff --cached --name-only | grep 'gaga_batch_jcvpca_' && echo "STOP: batch output staged" || echo "OK: no batch outputs"
git diff --cached --diff-filter=D --name-only
git check-ignore -v archive/
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319 && echo "OK: canonical batch"
test -d Layer3_JcvPCA/outputs/poster_ready_evidence_package && echo "OK: evidence package"
test -f scripts/make_poster_final_figures.py && echo "OK: poster script"
```

---

## Staged files summary

| Metric | Value |
|--------|-------|
| Staged paths | **56** |
| Insertions | **45,938** |
| Deletions | **31,650** |

### Staged by category

| Category | Count | Notes |
|----------|-------|-------|
| `.gitignore` | 1 | Stage B.6 rules |
| Cleanup docs (`docs/cleanup_stage_A/`, `docs/cleanup_stage_B/`, index, audit) | 22 | Includes B.7 plan/review |
| `PROJECT_STATUS.md`, `docs/CLEANUP_INDEX.md`, `docs/PROJECT_AUDIT_DRAFT.md` | 3 | |
| Poster scripts | 2 | `make_poster_final_figures.py`, `make_poster_671_figures.py` |
| Poster plot tables/captions | 19 | CSV + MD only (no PDF/PNG/SVG) |
| Segmentation xlsx | 2 | New canonical path under `segmentation/` |
| Relocation | 1 | `671_ex_segmentatios_frames.xlsx` → `segmentation/` (rename) |

---

## Staged deletions summary

**11 explicit deletions** (`git diff --cached --diff-filter=D`):

| # | Path | Reason |
|---|------|--------|
| 1 | `.../mapping_logic_table.csv` | B.7 — accept deletion (superseded by export manifest) |
| 2 | `.../joint_overlap_table.csv` | B.7 — accept deletion (regeneratable) |
| 3–11 | 9× `Layer2.5_Segmentation/reevluate_project/*` | Stage B move to local `archive/` |

**Segmentation xlsx old path:** recorded as **rename** (`R`), not a separate deletion line — `671_ex_segmentatios_frames.xlsx` → `segmentation/671_ex_segmentatios_frames.xlsx`.

---

## Exclusion checks (must pass)

| Check | Result |
|-------|--------|
| No `archive/` staged | **OK** |
| No raw data CSV staged | **OK** |
| No `gaga_batch_jcvpca_*` batch outputs staged | **OK** |
| No Layer 2 `outputs/archive/` staged | **OK** (not in staged set) |
| No `.venv/` staged | **OK** |
| No cache folders staged | **OK** |

---

## `archive/` ignored

```
.gitignore:89:archive/	archive/
```

Confirmed: `archive/` is gitignored and does not appear in staged paths.

---

## Poster reproduction paths (on disk)

| Path | Status |
|------|--------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | **Exists** |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | **Exists** |
| `scripts/make_poster_final_figures.py` | **Exists** |
| `outputs/poster_final_figures/` (plot tables) | **Staged** (CSV/MD) |

---

## Canonical batch `193319`

**Confirmed on disk:** `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` — not staged (gitignored generated output).

---

## Unstaged / untracked remaining (expected)

### Modified but not staged (deferred per plan)

- Layer 2.5 source, tests, notebooks, dashboard (~20 paths)
- Layer 2.5 export JSON/MD under `pre_jvcpca_review/671/` (~9 paths)
- Layer 2 stage indices (~16 paths)
- Layer 3 README, viz.py, PDF reference (~3 paths)

### Untracked (`??`) — not staged

- New Layer 2.5 config manifests, scripts, tests
- Layer 2 `data/252/`
- Layer 3 scripts, src, tests, docs, outputs (evidence package, etc.)

These remain for a **second commit** (analysis code) or remain local/gitignored.

---

## Pre-commit conclusion

**Safe to commit.** Staged set matches `STAGE_B7_COMMIT_PLAN_FINAL.md` with no forbidden paths.

This document will be staged and included in the checkpoint commit.
