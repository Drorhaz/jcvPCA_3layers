# Stage B.6 — Commit Plan (Do Not Execute Automatically)

**Date:** 2026-06-30  
**Status:** Prepared only — **no commit performed**

Suggested approach: **two commits** (cleanup docs + gitignore first, then code changes) or **one combined checkpoint** if you prefer a single snapshot.

---

## Commit 1 (recommended): Cleanup checkpoint + `.gitignore`

### Files to stage

**Git hygiene:**

```bash
git add .gitignore
```

**Project documentation:**

```bash
git add PROJECT_STATUS.md
git add docs/PROJECT_AUDIT_DRAFT.md
git add docs/CLEANUP_INDEX.md
git add docs/cleanup_stage_A/
git add docs/cleanup_stage_B/
```

**Poster scripts (source — not generated output):**

```bash
git add scripts/make_poster_final_figures.py
git add scripts/make_poster_671_figures.py
```

**Optional — poster audit tables/captions (small, regeneratable):**

```bash
git add outputs/poster_final_figures/*.csv
git add outputs/poster_final_figures/*.md
```

**Stage B deletion — reevluate scratch (accept move to archive):**

```bash
git add -u Layer2.5_Segmentation/reevluate_project/
```

**Segmentation xlsx — new canonical location:**

```bash
git add Layer2.5_Segmentation/segmentation/671_ex_segmentatios_frames.xlsx
git add Layer2.5_Segmentation/segmentation/252_ex_segmentatios_frames.xlsx
git add -u Layer2.5_Segmentation/671_ex_segmentatios_frames.xlsx
```

**Deleted export CSVs — only after manual OK (see DELETED_TRACKED_REVIEW):**

```bash
# Uncomment after confirming mapping_logic_table and joint_overlap_table are obsolete:
# git add -u Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/671_T1_P1_R2/671_T1_P1_R2_g4_s14040_e20880/mapping_logic_table.csv
# git add -u Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/joint_overlap_table.csv
```

### Files NOT to stage in Commit 1

| Category | Examples | Reason |
|----------|----------|--------|
| `archive/` | entire tree | Gitignored; local only |
| Raw data | `Layer1/.../data/`, `Layer2/.../data/`, `671_test_data_des/*_Take*.csv` | Gitignored |
| Layer 2 session outputs | `Layer2_Motive_Kinematics/outputs/*_Take_*/` | Gitignored |
| Layer 2 archive | `Layer2_Motive_Kinematics/outputs/archive/` | Gitignored (~22 GB) |
| Layer 3 batch outputs | `gaga_batch_jcvpca_*/` | Gitignored |
| Poster binaries | `outputs/poster_final_figures/*.{pdf,png,svg}` | Gitignored |
| Poster evidence package | `poster_ready_evidence_package/` | Optional — large CSV set; keep local unless remote repro needed |
| Virtual envs | `.venv/` | Gitignored |

### Suggested commit message (Commit 1)

```
Add cleanup audit docs, Stage B archive log, and conservative gitignore.

Document Stages A–B.6 project cleanup, move log for archived superseded
outputs, and gitignore rules for archive/, generated batch outputs, and
regeneratable intermediates. Accept reevluate_project removal after Stage B
move to local archive/. Relocate segmentation xlsx to segmentation/.
```

---

## Commit 2 (optional, separate): Layer 2.5 / Layer 3 code changes

Stage only when ready for code review — **explicit paths only:**

```bash
git add Layer2.5_Segmentation/src/pre_jvcpca_review/
git add Layer2.5_Segmentation/dashboard/
git add Layer2.5_Segmentation/tests/test_canonical_pilot_export.py
git add Layer2.5_Segmentation/tests/test_dashboard_joint_state.py
git add Layer2.5_Segmentation/tests/test_exercise_segments.py
git add Layer2.5_Segmentation/tests/test_layer2_5_critical_fixes.py
git add Layer2.5_Segmentation/tests/test_notebook_ui.py
git add Layer2.5_Segmentation/notebooks/post_layer2_segmentation_review.ipynb
git add Layer2.5_Segmentation/notebooks/pre_jvcpca_review.ipynb
git add Layer2.5_Segmentation/outputs/session_index.csv
git add Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/671_T1_P1_R1/671_T1_P1_R1_g4_s14280_e21000/
git add Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/671_T1_P1_R2/671_T1_P1_R2_g4_s14040_e20880/
git add Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/671_T2_P1_R2/671_T2_P1_R2_g4_s14040_e21360/
```

**New Layer 2.5 / Layer 3 files (if ready):**

```bash
git add Layer2.5_Segmentation/config/group4_core_14link_within_671_feature_manifest.csv
git add Layer2.5_Segmentation/config/group4_core_16link_within_252_feature_manifest.csv
git add Layer2.5_Segmentation/scripts/build_gaga_exports.py
git add Layer2.5_Segmentation/src/pre_jvcpca_review/datadescriptions_discovery.py
git add Layer2.5_Segmentation/src/pre_jvcpca_review/gaga_batch_export.py
git add Layer2.5_Segmentation/src/pre_jvcpca_review/layer3_export_manifest.py
git add Layer2.5_Segmentation/tests/test_core_participant_manifests.py
git add Layer2.5_Segmentation/tests/test_datadescriptions_discovery.py
git add Layer2.5_Segmentation/tests/test_layer3_export_manifest.py
git add Layer2.5_Segmentation/dashboard/pages/2_Layer3_Gaga_Workbench.py
git add Layer3_JcvPCA/src/
git add Layer3_JcvPCA/scripts/
git add Layer3_JcvPCA/tests/
git add Layer3_JcvPCA/docs/
git add Layer3_JcvPCA/README.md
```

```bash
git add Layer2_Motive_Kinematics/outputs/stage00_01_report_index.csv
git add Layer2_Motive_Kinematics/outputs/stage00_01_report_index.md
git add Layer2_Motive_Kinematics/outputs/stage02_component_order_index.csv
git add Layer2_Motive_Kinematics/outputs/stage02_component_order_index.md
git add Layer2_Motive_Kinematics/outputs/stage03_frame_time_index.csv
git add Layer2_Motive_Kinematics/outputs/stage03_frame_time_index.md
git add Layer2_Motive_Kinematics/outputs/stage04_quaternion_qc_index.csv
git add Layer2_Motive_Kinematics/outputs/stage04_quaternion_qc_index.md
git add Layer2_Motive_Kinematics/outputs/stage05_sign_continuity_index.csv
git add Layer2_Motive_Kinematics/outputs/stage05_sign_continuity_index.md
git add Layer2_Motive_Kinematics/outputs/stage06_relative_quaternion_index.csv
git add Layer2_Motive_Kinematics/outputs/stage06_relative_quaternion_index.md
git add Layer2_Motive_Kinematics/outputs/stage07_rotation_vector_index.csv
git add Layer2_Motive_Kinematics/outputs/stage07_rotation_vector_index.md
git add Layer2_Motive_Kinematics/outputs/stage08_filtering_index.csv
git add Layer2_Motive_Kinematics/outputs/stage08_filtering_index.md
```

**PDF reference (check size first):**

```bash
git add "Layer3_JcvPCA/references/JcvPCA and JsvCRP.pdf"
```

### Suggested commit message (Commit 2)

```
Update Layer 2.5 export pipeline, Layer 3 analysis scripts, and stage indices.

Layer 2.5 pre-JcvPCA export and dashboard updates; Layer 3 JcvPCA batch
reporting scripts and package modules; Layer 2 stage index refresh.
```

---

## Verification commands (run before ANY commit)

```bash
# 1. Review what is staged — must NOT include archive/, raw data, batch outputs
git diff --cached --stat

# 2. Confirm archive is ignored
git check-ignore -v archive/2026-06-30_cleanup_stage_B/

# 3. Confirm canonical batch on disk (not necessarily staged)
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319 && echo "batch OK"

# 4. Confirm no accidental raw CSV staged
git diff --cached --name-only | grep -E 'data/.*\.csv|671_test_data_des.*\.csv' && echo "WARNING: raw CSV staged" || echo "no raw CSV staged"

# 5. Confirm no archive paths staged
git diff --cached --name-only | grep '^archive/' && echo "WARNING: archive staged" || echo "no archive staged"

# 6. List deleted paths in staging area
git diff --cached --diff-filter=D --name-only

# 7. Full status after staging
git status

# 8. Optional: dry-run commit message review
git diff --cached --name-only | head -50
```

---

## Deleted tracked paths — decision checklist

Before committing, confirm:

- [ ] **9 reevluate files** — OK to remove from repo index (files in local `archive/`)
- [ ] **671 xlsx old path** — OK to delete; new `segmentation/` paths staged
- [ ] **mapping_logic_table.csv** — confirmed obsolete OR restored from history
- [ ] **joint_overlap_table.csv** — confirmed obsolete OR restored from history

---

## What never to run

```bash
# DO NOT USE
git add .
git add -A
git commit -a
```

Use **explicit paths** only.

---

## After commit (follow-up, not Stage B.6)

1. Update `PROJECT_STATUS.md` cleanup stage to **B.6 complete**.
2. Update `docs/CLEANUP_INDEX.md` with B.6 document links.
3. Plan **Stage C** — Layer 2 `outputs/archive/` physical move (not gitignore — already ignored).

---

*Prepared for manual execution by project owner. No git commands were run except `.gitignore` edit and status inspection.*
