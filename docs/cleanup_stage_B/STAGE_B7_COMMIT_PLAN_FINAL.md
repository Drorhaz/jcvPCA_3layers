# Stage B.7 — Final Checkpoint Commit Plan

**Date:** 2026-06-30  
**Purpose:** First cleanup checkpoint commit — **prepared only, not executed**  
**Prerequisite:** B.7 CSV review complete — both missing export CSVs → **accept deletion in git**

---

## Commit scope (single checkpoint)

One commit containing:

1. Updated `.gitignore` (Stage B.6)
2. Cleanup documentation (Stages A, B, B.5, B.6, B.7)
3. `PROJECT_STATUS.md`, `docs/CLEANUP_INDEX.md`
4. Poster generator scripts
5. Optional poster plot tables/captions (small CSV/MD)
6. Segmentation xlsx at new canonical path
7. All intentional deletions (reevluate archive move, xlsx relocate, two export CSVs)

**Explicitly excluded:** Layer 2.5/3 code changes, Layer 2 indices, notebooks, PDF reference — **second commit** when ready.

---

## Missing CSV resolution (B.7)

| File | Decision | Action in this commit |
|------|----------|----------------------|
| `mapping_logic_table.csv` | Accept deletion | `git add -u` on path |
| `joint_overlap_table.csv` | Accept deletion | `git add -u` on path |

**No `git restore`.** Optional local copy of `joint_overlap_table.csv` from `_archive/` is documented in B.7 review but **not part of this commit**.

---

## Files to stage

### Git hygiene

```bash
git add .gitignore
```

### Project documentation

```bash
git add PROJECT_STATUS.md
git add docs/PROJECT_AUDIT_DRAFT.md
git add docs/CLEANUP_INDEX.md
git add docs/cleanup_stage_A/
git add docs/cleanup_stage_B/
```

### Poster scripts (source)

```bash
git add scripts/make_poster_final_figures.py
git add scripts/make_poster_671_figures.py
```

### Poster audit artifacts (optional but recommended — small, regeneratable)

```bash
git add outputs/poster_final_figures/*.csv
git add outputs/poster_final_figures/*.md
```

Do **not** add `outputs/poster_final_figures/*.{pdf,png,svg}` (gitignored).

### Segmentation annotations (scientifically important)

```bash
git add Layer2.5_Segmentation/segmentation/671_ex_segmentatios_frames.xlsx
git add Layer2.5_Segmentation/segmentation/252_ex_segmentatios_frames.xlsx
```

### Deletions — Stage B reevluate move (9 files)

```bash
git add -u Layer2.5_Segmentation/reevluate_project/
```

### Deletions — xlsx old path

```bash
git add -u Layer2.5_Segmentation/671_ex_segmentatios_frames.xlsx
```

### Deletions — export CSVs (B.7 accept)

```bash
git add -u "Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/671_T1_P1_R2/671_T1_P1_R2_g4_s14040_e20880/mapping_logic_table.csv"
git add -u "Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/joint_overlap_table.csv"
```

---

## Files NOT to stage in this commit

| Category | Examples |
|----------|----------|
| `archive/` | Entire tree (gitignored) |
| Raw / large data | `**/data/**`, `671_test_data_des/*_Take*.csv` |
| Layer 2 session outputs | `Layer2_Motive_Kinematics/outputs/*_Take_*/` |
| Layer 2 archive | `Layer2_Motive_Kinematics/outputs/archive/` (gitignored) |
| Layer 3 batch | `gaga_batch_jcvpca_*/` (gitignored) |
| Poster evidence package | `poster_ready_evidence_package/` (keep local; optional later) |
| Poster binaries | `*.pdf`, `*.png`, `*.svg` in poster folder |
| Layer 2.5 / Layer 3 **code** changes | 45 modified tracked source files — defer |
| Layer 2 stage indices | 16 modified index files — defer |
| Notebooks | defer |
| `Layer3_JcvPCA/references/JcvPCA and JsvCRP.pdf` | defer (check size) |

---

## Files to restore

**None for this commit.**

Optional local-only (do not stage):

```bash
# Only if you want joint_overlap on disk before running Layer 2.5 notebook:
cp "Layer2.5_Segmentation/outputs/pre_jvcpca_review/_archive/pre_jvcpca_review_671_252_20260626_181500/671/joint_overlap_table.csv" \
   "Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/joint_overlap_table.csv"
```

---

## Full staging script (copy-paste)

Run from repository root. **Review `git diff --cached` after each block if preferred.**

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

## Verification before commit

```bash
# Staged summary — scan for surprises
git diff --cached --stat

# Must be empty — no archive paths
git diff --cached --name-only | grep '^archive/' && echo "STOP: archive staged" || echo "OK: no archive"

# Must be empty — no raw CSV
git diff --cached --name-only | grep -E '(/data/.*\.csv|671_test_data_des.*\.csv)' && echo "STOP: raw CSV staged" || echo "OK: no raw CSV"

# Must be empty — no batch output folders
git diff --cached --name-only | grep 'gaga_batch_jcvpca_' && echo "STOP: batch output staged" || echo "OK: no batch outputs"

# List deletions being committed
git diff --cached --diff-filter=D --name-only

# Confirm poster chain still on disk (not necessarily staged)
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319 && echo "OK: canonical batch"
test -d Layer3_JcvPCA/outputs/poster_ready_evidence_package && echo "OK: evidence package"
test -f scripts/make_poster_final_figures.py && echo "OK: poster script"

# Full status
git status
```

Expected deletions in staged set (**12 paths**):

- 9× `Layer2.5_Segmentation/reevluate_project/*`
- 1× `Layer2.5_Segmentation/671_ex_segmentatios_frames.xlsx`
- 1× `mapping_logic_table.csv`
- 1× `joint_overlap_table.csv`

---

## Suggested commit message

```
Add cleanup audit docs, gitignore for archives/outputs, and resolve stale tracked exports.

Document Stages A–B.7 project cleanup including move log for archived
superseded Layer 3 batches and Layer 2.5 scratch folders. Apply conservative
gitignore for archive/, generated batch outputs, Layer 2 session trees, and
poster figure binaries. Accept removal of tracked reevluate scratch files
(moved to local archive/), relocate segmentation xlsx to segmentation/,
and drop superseded export CSVs superseded by window_export_manifest and
on-demand joint_overlap regeneration.
```

---

## After this commit (not B.7)

1. Update `PROJECT_STATUS.md` → B.7 complete / checkpoint committed.
2. Second commit: Layer 2.5 / Layer 3 source, tests, notebooks (when reviewed).
3. Stage C: Layer 2 `outputs/archive/` physical move (unchanged plan).

---

## What this commit does NOT do

- Does not commit analysis code changes
- Does not commit `archive/` contents
- Does not commit canonical batch or evidence package
- Does not restore missing CSVs to git index
- Does not run `git add .`

---

*Prepared for manual execution. No git commands were run except documentation authoring.*
