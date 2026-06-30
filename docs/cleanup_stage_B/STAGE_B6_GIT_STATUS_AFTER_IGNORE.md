# Stage B.6 — Git Status After `.gitignore` Update

**Date:** 2026-06-30  
**Branch:** `main`  
**`.gitignore`:** Updated (modified, not committed)

---

## Before vs after (approximate)

| Metric | Stage B.5 | Stage B.6 |
|--------|-----------|-----------|
| Untracked not ignored | ~33,084 files | **~135 files** |
| Ignored untracked | ~98,455 | **~131,409** |
| `git status --short` lines | ~199 | **~131** |
| Untracked `??` lines | ~142 | **~73** |

---

## Current change summary

| Type | Count |
|------|-------|
| Modified tracked (`M`) | **46** (includes `.gitignore`) |
| Deleted tracked (`D`) | **12** |
| Untracked not ignored (`??`) | **~73** status lines |

---

## Modified tracked files (46)

### Git hygiene

- `.gitignore`

### Layer 2.5 (32 files)

- Dashboard: `dashboard_state.py`, `pre_jvcpca_dashboard.py`, `pages/1_Layer3_JcvPCA_Analysis.py`
- Notebooks: `post_layer2_segmentation_review.ipynb`, `pre_jvcpca_review.ipynb`
- Source: `app_controller.py`, `canonical_manifest.py`, `exercise_segments.py`, `export_constants.py`, `export_window.py`, `joint_overlap.py`
- Tests: 5 files
- Tracked export manifests (still indexed): 9 JSON/MD under `pre_jvcpca_review/671/.../g4_...`
- `outputs/session_index.csv`

### Layer 2 indices (16 files)

- `Layer2_Motive_Kinematics/outputs/stage00_01` through `stage08` index `.csv` and `.md`

### Layer 3 (3 files)

- `Layer3_JcvPCA/README.md`
- `Layer3_JcvPCA/references/JcvPCA and JsvCRP.pdf`
- `Layer3_JcvPCA/src/layer3_jcvpca/viz.py`

---

## Deleted tracked files (12)

See **`STAGE_B6_DELETED_TRACKED_REVIEW.md`** for per-path decisions.

Summary:

- **9** — `reevluate_project/*` (moved to `archive/` in Stage B)
- **1** — `671_ex_segmentatios_frames.xlsx` (relocated to `segmentation/`)
- **2** — export CSVs missing on disk (`mapping_logic_table.csv`, `joint_overlap_table.csv`)

---

## Untracked files still visible (~135 files)

These are **not ignored** and may be staged explicitly:

| Prefix | ~Files | Examples |
|--------|--------|----------|
| `Layer3_JcvPCA/scripts/` | 22 | Analysis/report scripts |
| `Layer3_JcvPCA/src/` | 16 | Package modules |
| `Layer3_JcvPCA/tests/` | 9 | Test suite |
| `Layer3_JcvPCA/outputs/` | 29 | `poster_ready_evidence_package/`, review report folders |
| `outputs/poster_final_figures/` | 18 | `*.csv`, `*.md` (binaries now ignored) |
| `docs/cleanup_stage_A/` | 7 | Audit artifacts |
| `docs/cleanup_stage_B/` | 6+ | Stage B/B.5/B.6 docs (this file set) |
| `docs/`, `PROJECT_STATUS.md` | few | Index + status |
| `scripts/make_poster_*.py` | 2 | Poster generators |
| `Layer2.5_Segmentation/` | ~15 | New source, configs, segmentation xlsx, tests |
| `Layer3_JcvPCA/docs/` | 5 | Scope, figures |

**No longer visible:** `archive/`, superseded batch folders, bulk Layer 2 session outputs, Layer 2.5 export trees, poster PDF/PNG/SVG.

---

## Is `archive/` now ignored?

| Check | Result |
|-------|--------|
| `git check-ignore -v archive/` | **Yes** — rule: `.gitignore:89:archive/` |
| Sample nested path | **Ignored** — `archive/2026-06-30_cleanup_stage_B/...` |
| In git index | **No** tracked files under `archive/` |

---

## Are raw / generated heavy files now ignored?

| Category | Ignored? | Rule |
|----------|----------|------|
| `archive/` (~2 GB) | **Yes** | `archive/` |
| Layer 3 batch `193319` (~3.6 GB) | **Yes** | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_*/` |
| Layer 2 session outputs | **Yes** | `Layer2_Motive_Kinematics/outputs/*_Take_*/` |
| Layer 2 `outputs/archive/` (~22 GB) | **Yes** (pre-existing) | `**/outputs/archive/` |
| Raw CSV in `data/` | **Yes** (pre-existing) | Path-specific + nested Layer2 `.gitignore` |
| `*.parquet`, `*.npy`, video | **Yes** (pre-existing) | Global patterns |
| Poster PDF/PNG/SVG | **Yes** | `outputs/poster_final_figures/*.{pdf,png,svg}` |
| Poster evidence package CSVs | **No** (visible untracked) | Intentional — may commit or ignore later |
| Poster plot tables (`*.csv`) | **No** | Intentional — small curated artifacts |

---

## Remaining staging risks

1. **`Layer3_JcvPCA/references/JcvPCA and JsvCRP.pdf`** — modified tracked; verify size before commit.
2. **Deleted tracked paths** — staging must include intentional deletions (see deleted-file review).
3. **`Layer2_Motive_Kinematics/data/252/`** — directory may appear untracked; contents are mostly ignored — do not force-add raw data.
4. **`poster_ready_evidence_package/`** — visible untracked; only add if you want CSVs in remote repo.
5. **Do not use `git add .`** — still could stage unwanted paths (e.g. large PDF, wrong exports).

---

## Poster path stability (post-`.gitignore`)

Static existence check — **no scripts executed**:

| Path | Exists? |
|------|---------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | **Yes** |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | **Yes** |
| `scripts/make_poster_final_figures.py` | **Yes** |
| `scripts/make_poster_671_figures.py` | **Yes** |
| `outputs/poster_final_figures/` | **Yes** |
| `outputs/poster_final_figures/final_4figure_poster_panel_portrait.pdf` | **Yes** |

**Conclusion:** `.gitignore` changes affect git visibility only; poster reproduction paths on disk are **unchanged and intact**.

---

*No commit performed. See `STAGE_B6_COMMIT_PLAN.md` for recommended staging commands.*
