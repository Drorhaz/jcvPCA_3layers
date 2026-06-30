# `.gitignore` Review — Recommendations Only

**Date:** 2026-06-30  
**Status:** Review complete; **`.gitignore` not modified** (per Stage B.5 rules).

Current file: `.gitignore` (81 lines at repo root).

---

## What works well today

| Category | Current rules | Assessment |
|----------|---------------|------------|
| Python cache | `__pycache__/`, `*.py[cod]`, `.pytest_cache/` | Good |
| Virtual environments | `.venv/`, `venv/`, `env/` | Good |
| Notebook checkpoints | `.ipynb_checkpoints/` | Good |
| OS / IDE | `.DS_Store`, `.idea/`, `.vscode/`, `.cursor/` | Good |
| Array binaries | `**/*.parquet`, `**/*.npy`, `**/*.npz` | Good — covers most Layer 3 bulk |
| Video | `**/*.avi`, `**/*.mp4`, etc. | Good |
| Raw Motive CSVs | Layer 1/2 data paths, `671_test_data_des/*_Take*.csv` | Good |
| Large Layer 2 frame CSVs | Stages 05–08 specific filenames | Good |
| QC event dumps | `combined_qc_events.csv`, etc. | Good |
| Nested `.git/` | `**/.git/` | Good |
| Layer 2.5 diag scratch | `pre_jvcpca_review/_diag/` | Good |

---

## Gaps and recommended additions

### 1. Local cleanup archive (new — high priority)

Stage B created `archive/2026-06-30_cleanup_stage_B/` (~2 GB, **untracked, not ignored**).

**Recommended (Stage C or pre-commit):**

```gitignore
# Local cleanup archives (Stage B+ moves; keep off git remote)
archive/
```

Or narrower:

```gitignore
archive/2026-06-30_cleanup_stage_B/
```

**Rationale:** Prevents accidental `git add .` staging of moved superseded batches and scratch folders.

---

### 2. Layer 3 generated batch outputs

Canonical and superseded batch folders contain large PNG/NPY/CSV/MD mixes. NPY/parquet already ignored; **PNGs and summary CSVs are not**.

**Recommended:**

```gitignore
# Layer 3 batch run outputs (regenerate from scripts + Layer 2.5 exports)
Layer3_JcvPCA/outputs/gaga_batch_jcvpca_*/
Layer3_JcvPCA/outputs/_workbench_*/
Layer3_JcvPCA/outputs/671_g4_validation_001/
```

**Exception option:** Track only small manifest files via negation (advanced):

```gitignore
Layer3_JcvPCA/outputs/gaga_batch_jcvpca_*/
!Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/batch_summary.md
```

**Conservative default:** Ignore entire batch folders; keep canonical reports in `poster_ready_evidence_package/` or docs if needed in git.

---

### 3. Poster outputs

**Recommended:**

```gitignore
# Poster figure binaries (regenerate via scripts/make_poster_*.py)
outputs/poster_final_figures/*.pdf
outputs/poster_final_figures/*.png
outputs/poster_final_figures/*.svg

# Optional: keep plot tables and captions tracked
# !outputs/poster_final_figures/*.csv
# !outputs/poster_final_figures/*.md
```

**Rationale:** ~13 MB figures are regeneratable if evidence package + batch CSVs remain local.

---

### 4. Poster evidence package (keep local, optional ignore)

**Recommended (optional — medium priority):**

```gitignore
Layer3_JcvPCA/outputs/poster_ready_evidence_package/
```

**Caution:** Required for poster regeneration. Ignoring is fine for git **if** files stay on disk and are backed up; do **not** ignore if you need remote reproducibility without re-running Layer 3 reports.

**Stage B.5 recommendation:** Keep untracked locally for now; add ignore rule only after off-repo backup confirmed.

---

### 5. Raw data (strengthen, no change required)

Existing rules are adequate. Optional clarity:

```gitignore
# Raw capture — never commit
**/data/**/*.csv
!**/data/**/README.md
!**/data/**/*_manifest*.csv
```

**Do not relax** ignores on `Layer1_motive_qc/motive_qc/data/` or `Layer2_Motive_Kinematics/data/`.

---

### 6. Processed / interim data

Already covered for largest Layer 2 CSVs and all parquet/npy. Optional additions:

```gitignore
# Layer 2 full session output trees (regenerate via layer2-motive)
Layer2_Motive_Kinematics/outputs/*_Take_*/
Layer2_Motive_Kinematics/outputs/layer2_exports/
```

**Defer Layer 2 archive rule change until Stage C:**

Current `**/outputs/archive/` ignores paths ending in `outputs/archive/`. After Stage B, Layer 2.5's `outputs/archive/` was **moved out**; Layer 2's `outputs/archive/` (22 GB) **still matches** this rule and is already ignored.

---

### 7. Generated CSVs (selective)

Blanket `**/*.csv` ignore would break tracked small configs and reports.

**Recommended targeted patterns:**

```gitignore
# Large generated Layer 3 reports (optional; MD may stay tracked)
Layer3_JcvPCA/outputs/**/comparisons/**/
Layer3_JcvPCA/outputs/**/*.npy
# (parquet/npy already global)
```

Keep small index CSVs in `Layer2_Motive_Kinematics/outputs/stage*_index.csv` **tracked** if they document pipeline state.

---

### 8. Generated figures (Layer 3 comparison PNGs)

**Recommended:**

```gitignore
Layer3_JcvPCA/outputs/**/plots/
Layer3_JcvPCA/outputs/**/comparisons/**/*.png
```

Workflow schematic in `Layer3_JcvPCA/docs/figures/` should **remain tracked**.

---

### 9. Cache / temp (minor additions)

```gitignore
*.egg-info/
.mplconfig/
.matplotlib/
```

(`*.egg-info/` partially covered; `.mplconfig/` already listed.)

---

### 10. Stale rules to update after Stage B

| Line | Current | Issue | Recommended action |
|------|---------|-------|-------------------|
| 62 | `Layer2.5_Segmentation/reevluate_project/*_Take*.csv` | Folder moved to `archive/...` | Remove or replace with `archive/**/reevluate_project/` if needed |

---

## Recommended ignore priority (when editing `.gitignore`)

| Priority | Rule | Risk if omitted |
|----------|------|-----------------|
| P0 | `archive/` | Accidental 2 GB commit |
| P1 | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_*/` | Accidental 3.6 GB commit |
| P2 | Poster figure binaries | 13 MB noise in diffs |
| P3 | `_workbench_*`, validation run folders | Clutter |
| P4 | Stale `reevluate_project` path cleanup | Confusion only |

---

## What should stay tracked

- All `src/`, `tests/`, `scripts/` (including poster generators)
- Config templates (`*.yaml`, small manifest CSV templates)
- Markdown specs, cleanup docs, `PROJECT_STATUS.md`
- Segmentation `.xlsx` (scientific annotations)
- Small Layer 2 stage index CSV/MD (if used as pipeline registry)
- Reference paper CSVs in `Layer3_JcvPCA/references/`
- `Layer3_JcvPCA/docs/figures/jcvpca_workflow_schematic.svg`

---

*Recommendations only. Apply in a dedicated Stage C git-hygiene commit after user approval.*
