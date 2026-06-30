# Stage B.6 — `.gitignore` Rules Applied

**Date:** 2026-06-30  
**File modified:** `.gitignore` (root)  
**Commit:** Not performed in this stage.

---

## Summary

Added a **Stage B.6** section to `.gitignore` and removed one **stale rule**. Untracked-not-ignored files dropped from **~33,084 → ~135**. Ignored untracked rose from **~98,455 → ~131,409**.

---

## Rules added (exact lines)

### Local cleanup archive

```gitignore
archive/
```

| Why | Prevents accidental staging of ~2 GB Stage B archive (superseded batches + Layer 2.5 scratch). |
| Risk if omitted | High — `git add .` could include entire `archive/2026-06-30_cleanup_stage_B/`. |

---

### Layer 1 generated QC outputs

```gitignore
Layer1_motive_qc/motive_qc/outputs/batch_runs/
Layer1_motive_qc/motive_qc/outputs/runs/
```

| Why | Batch and per-session QC HTML/plots/CSVs are regeneratable from raw data + pipeline. |
| Risk if omitted | Medium — dozens of new run folders were untracked. |

---

### Layer 2 session outputs (not Layer 2 archive)

```gitignore
Layer2_Motive_Kinematics/outputs/*_Take_*/
Layer2_Motive_Kinematics/outputs/layer2_exports/
```

| Why | Full per-session stage trees (~2–3 GB each) are regeneratable via `layer2-motive`. |
| Risk if omitted | High — active 671/252 session outputs were untracked. |
| **Not added** | `Layer2_Motive_Kinematics/outputs/archive/` — already matched by existing `**/outputs/archive/`; deferred Stage C physical move per instructions. |

---

### Layer 2.5 export bulk (selective)

```gitignore
Layer2.5_Segmentation/outputs/pre_jvcpca_review/252/
Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/
Layer2.5_Segmentation/outputs/pre_jvcpca_review/_archive/
Layer2.5_Segmentation/outputs/pre_jvcpca_review/layer25_export_*.csv
Layer2.5_Segmentation/outputs/pre_jvcpca_review/layer25_session_coverage_report.csv
Layer2.5_Segmentation/outputs/pre_jvcpca_review/review_table_repair_*.md
Layer2.5_Segmentation/outputs/pre_jvpca_review/
```

| Why | Bulk participant export trees (parquet already global-ignored); typo folder `pre_jvpca_review/`. |
| Risk if omitted | Medium — ~1.2 GB export tree mostly hidden now. |
| **Note** | Already-**tracked** small JSON/MD under `671/.../g4_.../` still show as modified — `.gitignore` does not untrack indexed files. |

---

### Layer 3 batch and exploratory outputs

```gitignore
Layer3_JcvPCA/outputs/gaga_batch_jcvpca_*/
Layer3_JcvPCA/outputs/_workbench_*/
Layer3_JcvPCA/outputs/671_g4_validation_001/
Layer3_JcvPCA/outputs/layer3_jcvpca/
```

| Why | Canonical batch `193319` (~3.6 GB) and all batch runs are regeneratable; keeps repo index clean. |
| Risk if omitted | High — largest untracked prefix before B.6. |
| **On disk** | Canonical batch **unchanged** — ignore affects git visibility only. |

---

### Poster figure binaries (not tables/captions)

```gitignore
outputs/poster_final_figures/*.pdf
outputs/poster_final_figures/*.png
outputs/poster_final_figures/*.svg
```

| Why | ~13 MB regeneratable from `scripts/make_poster_*.py` + evidence CSVs. |
| Risk if omitted | Low–medium — binary diff noise in commits. |
| **Intentionally not ignored** | `outputs/poster_final_figures/*.csv`, `*.md` — small audit tables and captions may be committed. |

---

## Rule removed / updated

| Before | After |
|--------|-------|
| `Layer2.5_Segmentation/reevluate_project/*_Take*.csv` | Removed (folder moved to `archive/` in Stage B) |
| — | Comment pointing to `archive/` rule |

---

## Rules intentionally NOT added

| Recommended in B.5 review | Reason deferred |
|---------------------------|-----------------|
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | Required for poster regeneration; may be committed or kept local-only — user may want remote CSV backup. Still **visible** as untracked (~29 files under `Layer3_JcvPCA/outputs/`). |
| Blanket `**/*.csv` or `**/*.png` | Would break tracked configs, stage indices, reference CSVs, workflow SVG. |
| `Layer3_JcvPCA/outputs/**/comparisons/**/` | Redundant with `gaga_batch_jcvpca_*/` ignore. |
| `docs/cleanup_stage_A/file_inventory.csv` | Documentation intended for commit. |
| Negation patterns (`!batch_summary.md`) | Avoided — full batch folder ignore is simpler and safer. |

---

## Pre-existing rules retained (unchanged)

- `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ipynb_checkpoints/`, `.DS_Store`
- `**/*.parquet`, `**/*.npy`, `**/*.npz`, video formats
- Raw data paths (`Layer1/.../data/**/*.csv`, `Layer2/.../data/**/*.csv`, `671_test_data_des/*_Take*.csv`)
- Large Layer 2 frame-level CSV patterns (stages 05–08)
- `**/outputs/archive/` (covers Layer 2 `outputs/archive/` ~22 GB)

---

## Risks and notes

1. **Canonical batch is gitignored** — files remain on disk; poster scripts unaffected. Remote clones will not get batch outputs from git (by design).
2. **Tracked modified export JSON/MD** under `pre_jvcpca_review/671/...` still appear in `git status` — only new siblings under ignored dirs are hidden.
3. **`Layer2_Motive_Kinematics/data/252/`** may still show as `??` if directory contains non-ignored entries (e.g. README); raw CSV/AVI inside are ignored via existing rules.
4. **Layer 3 source/scripts/tests** remain untracked — intentional for separate commit; not ignored so `git add` paths work.
5. **No commit performed** — `.gitignore` change is modified tracked file pending commit.

---

*Stage B.6 — apply only. See `STAGE_B6_GIT_STATUS_AFTER_IGNORE.md` for post-change status.*
