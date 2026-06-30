# W2 — Target Visible Structure

**Date:** 2026-06-30  
**Goal:** A human-readable working surface without breaking the runnable pipeline  
**Principle:** **Physical layout stays layer-coupled; mental model uses docs + pointers + gitignore**

The layer folders (`Layer1_*`, `Layer2_*`, `Layer3_*`) remain on disk where code expects them. Ergonomics come from **what you open daily**, not from flattening 62 GB of science data into a new tree.

---

## Design principles

1. **Root is a control panel**, not a data warehouse.
2. **Heavy data stays in layer paths** until a deliberate path migration (with yaml update).
3. **Generated outputs are gitignored and documented**, not deleted.
4. **Pointer README files** replace physical copies where symlinks would be fragile.
5. **External archive** holds superseded/historical bulk; repo holds active runnable chain.
6. **One daily README** (`README_WORKING.md`) beats scattered layer READMEs for continuation work.

---

## Target: what you see at repo root

```text
3Layers_project/
├── README_WORKING.md          ← START HERE (daily front door)
├── README.md                  ← Scientific overview + git policy (keep)
├── PROJECT_STATUS.md          ← Checkpoint status (optional later → docs/)
│
├── config/                    ← paths.yaml (do not touch casually)
├── src/                       ← project_paths.py
├── scripts/                   ← check_project_paths.py + poster scripts
│
├── docs/                      ← all planning, audit, recovery docs
├── results/                   ← lightweight indexes + pointers (not bulk data)
│
├── outputs/                   ← poster figures only (until migrated)
│
├── Layer1_motive_qc/          ← Layer 1 (open rarely)
├── Layer2_Motive_Kinematics/  ← Layer 2 code + heavy data/outputs
├── Layer2.5_Segmentation/     ← Layer 2.5 code + exports
└── Layer3_JcvPCA/             ← Layer 3 code + batches
```

**Hidden from daily view (but present):** `.venv/` in each layer, `.gitignore`d outputs, external archive.

---

## Target: mental map by purpose

| I want to… | Go here |
|------------|---------|
| Check project health | `python scripts/check_project_paths.py` |
| Read what to do next | `README_WORKING.md` → `docs/research_recovery/CONTINUATION_RUNBOOK.md` |
| Change paths | `config/paths.yaml` + `src/project_paths.py` (careful) |
| Run Layer 2 | `Layer2_Motive_Kinematics/` + its `.venv` |
| Run Layer 2.5 exports | `Layer2.5_Segmentation/scripts/` + its `.venv` |
| Run Layer 3 batch/reports | `Layer3_JcvPCA/scripts/` + **`Layer3_JcvPCA/.venv`** |
| Find canonical results | `results/active/CANONICAL_BATCH.md` |
| Find smoke test results | `results/active/SMOKE_BATCH_671.md` *(proposed pointer)* |
| Find poster figures | `results/poster/README.md` → `outputs/poster_final_figures/` |
| Find raw data | Layer `data/` trees + `671_test_data_des/` — **do not move** |
| Find old batches/plots | `../gaga_psylo_external_archive/` via `results/archive_index/` |

---

## Folder roles (target state)

### Daily working surface (open regularly)

| Path | Purpose |
|------|---------|
| `README_WORKING.md` | Commands, don’t-touch list, next steps |
| `config/paths.yaml` | Path registry |
| `scripts/check_project_paths.py` | Health gate |
| `docs/research_recovery/` | Runbook, M12 logs, continuation plan |
| `results/` | Human indexes only |
| `Layer3_JcvPCA/scripts/` | Batch + report entry points |
| `Layer3_JcvPCA/.venv/` | Validated Python env (M12a/M12b) |

### Active but heavy (documented, not daily)

| Path | Purpose | Visibility tactic |
|------|---------|-------------------|
| `Layer2_Motive_Kinematics/outputs/*_Take_*` | L2 session outputs (~32 GB) | Gitignored; note in layer README |
| `Layer2_Motive_Kinematics/data/` | L2 raw inputs (~21 GB) | Gitignored; yaml-registered |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | Parquet exports (~1.2 GB) | Gitignored; yaml-registered |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | Canonical batch (~3.6 GB) | Pointer in `results/active/` |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` | Smoke batch (~370 MB) | Pointer in `results/active/` |
| `outputs/poster_final_figures/` | Poster PDFs/PNGs | Pointer in `results/poster/` |
| `../gaga_psylo_external_archive/` | Historical archives | `results/archive_index/EXTERNAL.md` |

### Generated outputs (stay ignored; optional archive)

| Path | Action |
|------|--------|
| `Layer3_JcvPCA/outputs/_workbench_*` | Archive off-repo when approved |
| `Layer3_JcvPCA/outputs/671_g4_validation_001/` | Archive off-repo |
| `Layer1_motive_qc/motive_qc/outputs/` | Regeneratable |
| L2 stage indices (small CSV/MD) | Optionally commit to git for navigation |

### Legacy / history (consolidate docs, not code)

| Current scatter | Target |
|-----------------|--------|
| Root `LAYER*_*.md` audit reports | `docs/audits/` |
| `3_layers_Matser_plan_Full/` (root + L3 duplicate) | Single `docs/legacy/master_plan/` |
| L2.5 `POST_LAYER2_*.md` at layer root | `docs/legacy/layer2_5/` |
| L3 planning md at layer root | `docs/legacy/layer3/` |
| `docs/cleanup_stage_*` | Keep; indexed via `docs/CLEANUP_INDEX.md` |

### Raw / protected (never move without approval)

| Path | yaml key |
|------|----------|
| `Layer1_motive_qc/motive_qc/data/` | `raw_data.layer1` |
| `Layer2_Motive_Kinematics/data/` | `raw_data.layer2` |
| `671_test_data_des/` | `raw_data.root_test_exports` |
| `Layer2.5_Segmentation/data_description/` | `raw_data.layer2_5_descriptions` |

---

## Proposed `results/` layout (pointer-only phase)

No bulk symlinks yet — **README pointers only** (low risk):

```text
results/
├── README.md                          ← index (exists)
├── active/
│   ├── CANONICAL_BATCH.md             ← exists
│   ├── SMOKE_BATCH_671.md             ← proposed (W3 safe)
│   └── LAYER25_EXPORTS.md             ← proposed pointer to pre_jvcpca_review
├── poster/
│   └── README.md                      ← pointer to outputs/poster_final_figures/
├── reports/
│   └── README.md                      ← sidecar reports in L3 outputs
├── manuscript/
│   └── README.md                      ← placeholder
└── archive_index/
    └── EXTERNAL_ARCHIVE.md            ← ../gaga_psylo_external_archive/ map
```

**Later (optional W4+):** symlinks from `results/active/canonical_batch` → L3 batch folder — only after explicit approval and path validation.

---

## Proposed naming conventions (optional, not required now)

| Pattern | Use |
|---------|-----|
| `_archive_local/` | Inside repo: reversible staging before external move (not created yet) |
| `docs/legacy/` | Historical plans superseded by research_recovery docs |
| `docs/audits/` | One-off audit reports |
| `data_links/` | **Not recommended now** — would duplicate yaml; use `results/` pointers instead |

Avoid renaming `Layer*_` folders until a dedicated path migration batch — too many code and yaml references.

---

## What stays outside the repo

| Content | Location |
|---------|----------|
| Superseded L3 batches (5) | `../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/layer3_superseded_batches/` |
| Historical L2 outputs archive | `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` |
| Stage B cleanup bundle | `../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/` |
| Future: L3 workbench scratch, L2 Archive.zip | External archive after W3 review |

---

## What stays in repo but ignored (`.gitignore`)

Already configured for:

- All `*.parquet`, large CSVs, session output trees
- `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_*/` (includes canonical + smoke on disk)
- L2.5 export participant folders
- Poster figure binaries (PDF/PNG/SVG); tables may stay trackable

**Gap:** Untracked small files still appear in `git status` (stage indices, planning md, modified PDF). W3 addresses doc consolidation; indices optional commit.

---

## IDE / Finder ergonomics (no move required)

Until physical moves execute:

1. **Pin/bookmark** in IDE: `README_WORKING.md`, `config/paths.yaml`, `Layer3_JcvPCA/scripts/`, `docs/research_recovery/`.
2. **Collapse** in file tree: `Layer2_Motive_Kinematics/outputs/`, `Layer3_JcvPCA/outputs/`.
3. **Use** `README_WORKING.md` instead of browsing `Layer3_JcvPCA/outputs/` directly.

---

## Success criteria

After W3 moves (doc-only phase) + pointer READMEs:

- [ ] Root has ≤3 loose markdown files (README_WORKING, README, PROJECT_STATUS)
- [ ] `python scripts/check_project_paths.py` still exits 0
- [ ] Canonical + smoke batch paths unchanged on disk
- [ ] New user can find “what to run next” in under 60 seconds
- [ ] `git status` shows fewer untracked planning docs at layer roots

---

## Related docs

- [`W1_WORKSPACE_SURFACE_AUDIT.md`](W1_WORKSPACE_SURFACE_AUDIT.md)
- [`W3_WORKSPACE_SIMPLIFICATION_MOVE_PLAN.md`](W3_WORKSPACE_SIMPLIFICATION_MOVE_PLAN.md)
- [`R2_TARGET_WORKING_STRUCTURE.md`](R2_TARGET_WORKING_STRUCTURE.md) — earlier continuation structure plan
- [`results/README.md`](../../results/README.md)

---

*Design doc only — no moves executed.*
