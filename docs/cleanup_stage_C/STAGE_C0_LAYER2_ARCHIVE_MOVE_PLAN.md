# Stage C.0 — Layer 2 Archive Move Plan (Proposed, Not Executed)

**Date:** 2026-06-30  
**Status:** **PLAN ONLY** — do not execute until Stage C.1 approval  
**Prerequisite review:** [`STAGE_C0_LAYER2_ARCHIVE_REVIEW.md`](STAGE_C0_LAYER2_ARCHIVE_REVIEW.md)

---

## Recommended timing

Execute **after poster submission**, not before (conservative default from C.0 review).

---

## Source and destination

| | Path |
|---|------|
| **Source** | `Layer2_Motive_Kinematics/outputs/archive/` |
| **Destination** | `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` |
| **Absolute destination (expected)** | `/Users/drorhazan/Desktop/gaga_psilo/projects/gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` |
| **Estimated size** | ~22.5 GB (852 files) |

**Parent folder (create if missing):**

```
../gaga_psylo_external_archive/
```

Same external root used for Stage B.10 (`archive_2026-06-30_cleanup_stage_B/`).

---

## What will be moved

Entire `outputs/archive/` tree:

- 6× archived 671 `*_Take_*` session folders
- 6× `audit_rerun_*` folders
- `layer2_exports/` (archive copy, ~134 MB)
- 27 root index/QC/report files

---

## What must remain untouched

| Path | Reason |
|------|--------|
| `Layer2_Motive_Kinematics/outputs/*_Take_*` (12 active sessions) | Active Layer 2 pipeline outputs |
| `Layer2_Motive_Kinematics/outputs/layer2_exports/` | Active Layer 2.5 input bundle |
| `Layer2_Motive_Kinematics/outputs/stage*_index.*` | Active indices at outputs root |
| `Layer2_Motive_Kinematics/data/` | Raw input CSVs |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | Layer 3 upstream exports |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | Canonical batch |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | Poster evidence |
| `outputs/poster_final_figures/` | Poster deliverables |
| `671_test_data_des/` | Raw-adjacent (separate review) |
| `../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/` | Stage B.10 external archive |

**No raw data** is inside `outputs/archive/` — only derived kinematics outputs.

---

## Pre-move checks

Run from repository root before any `mv`:

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project

# 1. Source exists and size baseline
test -d Layer2_Motive_Kinematics/outputs/archive && echo "OK: source exists"
du -sh Layer2_Motive_Kinematics/outputs/archive
find Layer2_Motive_Kinematics/outputs/archive -type f | wc -l

# 2. Git ignore (new files won't be tracked)
git check-ignore -v Layer2_Motive_Kinematics/outputs/archive/

# 3. Confirm NOT moving active sessions
test -d Layer2_Motive_Kinematics/outputs/671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001 && echo "OK: active session present"

# 4. Poster / batch / L2.5 paths exist
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319 && echo "OK: batch 193319"
test -d Layer3_JcvPCA/outputs/poster_ready_evidence_package && echo "OK: evidence package"
test -d outputs/poster_final_figures && echo "OK: poster figures"
test -d Layer2.5_Segmentation/outputs/pre_jvcpca_review && echo "OK: L2.5 exports"

# 5. Destination parent writable
mkdir -p ../gaga_psylo_external_archive
test -w ../gaga_psylo_external_archive && echo "OK: destination parent writable"

# 6. Destination must not already exist (or deliberate merge decision)
test ! -d ../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30 && echo "OK: destination free" \
  || echo "STOP: destination already exists — resolve before move"

# 7. Optional: record Git tracked file list for later untrack
git ls-files Layer2_Motive_Kinematics/outputs/archive/ | wc -l
```

**Human gates before move:**

- [ ] Poster submitted (or explicit user approval to proceed early)
- [ ] T3_R1 stage07 active vs archive difference documented
- [ ] External disk / backup location confirmed

---

## Planned move command (Stage C.1 — not run in C.0)

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project

mkdir -p ../gaga_psylo_external_archive

mv Layer2_Motive_Kinematics/outputs/archive \
   ../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30
```

**Properties:**

- Single `mv` — reversible, no deletion
- Renames folder to dated external name
- Leaves empty gap at `outputs/archive/` (path absent after move — expected)

---

## Post-move checks

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project

# Source gone
test ! -d Layer2_Motive_Kinematics/outputs/archive && echo "OK: source removed" \
  || echo "FAIL: source still exists"

# Destination exists with expected size
test -d ../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30 && echo "OK: destination exists"
du -sh ../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30
find ../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30 -type f | wc -l
# Expect ~22G and 852 files

# Active Layer 2 untouched
du -sh Layer2_Motive_Kinematics/outputs/*_Take_* | head -3
test -d Layer2_Motive_Kinematics/outputs/layer2_exports && echo "OK: active layer2_exports"

# Canonical / poster / L2.5
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319 && echo "OK: batch 193319"
test -d Layer3_JcvPCA/outputs/poster_ready_evidence_package && echo "OK: evidence package"
test -d outputs/poster_final_figures && echo "OK: poster figures"
test -d Layer2.5_Segmentation/outputs/pre_jvcpca_review && echo "OK: L2.5 exports"

# Raw data untouched
test -d Layer2_Motive_Kinematics/data && echo "OK: L2 raw data dir"

# Git status — expect deleted tracked paths if 389 files were in index
git status --short Layer2_Motive_Kinematics/outputs/archive/ | head -5
```

Compare `du` and file counts: source baseline must match destination.

---

## Restore command

From repository root:

```bash
mv /Users/drorhazan/Desktop/gaga_psilo/projects/gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30 \
   /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project/Layer2_Motive_Kinematics/outputs/archive
```

Relative form:

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
mv ../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30 \
   Layer2_Motive_Kinematics/outputs/archive
```

---

## Git follow-up (separate stage — not part of physical move)

After move, Git will show **389 deleted tracked files** unless cleaned first.

**Option A — before move:**

```bash
git rm -r --cached Layer2_Motive_Kinematics/outputs/archive/
# commit with docs only — explicit paths, no git add .
```

**Option B — after move:** same command; files already absent on disk.

Do **not** use `git add .`. Stage in dedicated doc commit.

---

## Poster and batch verification statement

Moving `outputs/archive/` to external storage **does not affect**:

| Check | Why |
|-------|-----|
| Poster script CSV resolution | Reads evidence package + batch `193319` |
| Batch `193319` on disk | Separate path under Layer 3 outputs |
| Layer 2.5 export regeneration | `session_index.py` skips `archive/` paths |
| Active Layer 2 sessions | Sibling paths under `outputs/`, not under `archive/` |

Post-move verification commands above are **mandatory** before declaring Stage C complete.

---

## Rollback plan

1. Run restore `mv` command.
2. Verify `du` and file count match pre-move baseline.
3. Re-run poster path checks.
4. If Git untrack was done, restore index from prior commit or `git checkout HEAD -- Layer2_Motive_Kinematics/outputs/archive/` (only if files restored on disk).

---

## Stage sequence (proposed)

| Stage | Action |
|-------|--------|
| **C.0** (this doc) | Review + plan — **complete** |
| **C.1** | Execute move after poster / approval |
| **C.2** | Move log + summary docs |
| **C.3** | Git untrack + doc commit |
| **C.4** | Update `PROJECT_STATUS.md`, `CLEANUP_INDEX.md` |

---

*Plan only. No files moved in Stage C.0.*
