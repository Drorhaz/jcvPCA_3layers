# R2 — Target Working Structure

**Date:** 2026-06-30  
**Mode:** Research continuation (post-poster)  
**Action:** Folders created; **no active data migrated yet**

---

## Design principles

1. **Layer folders stay authoritative for now** — Layer 1/2/2.5/3 code and their primary outputs remain in place to avoid breaking paths.
2. **Heavy history lives outside the repo** — under `../gaga_psylo_external_archive/`.
3. **`results/` is the future home** for curated research outputs, symlinks, and indexes — not a wholesale data move today.
4. **`config/paths.yaml`** becomes the single path registry for automation (wired in a later coding stage).

---

## Proposed folder tree

```text
3Layers_project/
├── config/
│   └── paths.yaml                 # canonical path registry (R3)
├── docs/
│   ├── research_recovery/         # post-poster recovery & structure docs
│   └── cleanup_stage_{A,B,C}/     # historical cleanup audit trail
├── results/                       # NEW — curated research-facing outputs
│   ├── active/                    # symlinks / pointers to current canonical artifacts
│   ├── poster/                    # frozen poster deliverables (optional copy/link)
│   ├── manuscript/                # manuscript tables/figures drafts
│   ├── reports/                   # ad-hoc analysis reports (future runs)
│   └── archive_index/             # JSON/MD indexes of external archives
├── scripts/                       # root-level utilities (poster scripts)
├── Layer1_motive_qc/              # unchanged — QC pipeline
├── Layer2_Motive_Kinematics/      # unchanged — kinematics pipeline
│   └── outputs/                   # active sessions only (archive moved out)
├── Layer2.5_Segmentation/         # unchanged — export/review pipeline
├── Layer3_JcvPCA/                 # unchanged — JcvPCA batch + scripts
├── outputs/
│   └── poster_final_figures/      # keep here for now (committed CSV/MD)
└── (no top-level archive/)        # moved to external archive in B.10

../gaga_psylo_external_archive/      # OUTSIDE REPO
├── archive_2026-06-30_cleanup_stage_B/
└── layer2_outputs_archive_2026-06-30/
```

---

## Purpose of each new folder

| Folder | Purpose | Populate now? |
|--------|---------|---------------|
| `config/` | Machine-readable path registry for automation | **Yes** — `paths.yaml` |
| `docs/research_recovery/` | Research-mode docs (moves, paths, hard-coded review) | **Yes** |
| `results/active/` | Shortcuts to canonical batch, L2.5 exports, evidence package | **Later** — symlinks in R6+ |
| `results/poster/` | Optional frozen poster bundle separate from dev tree | **Later** |
| `results/manuscript/` | Non-poster publication artifacts | **Later** |
| `results/reports/` | New analysis outputs (post-poster research) | **As generated** |
| `results/archive_index/` | Manifest of external archive locations + restore commands | **R6+** |

---

## What should be tracked in Git

| Track | Examples |
|-------|----------|
| **Yes** | `config/paths.yaml`, `docs/`, source code, tests, small CSV/MD captions, segmentation xlsx |
| **Optional** | Poster plot tables in `outputs/poster_final_figures/*.csv` |
| **No (gitignore)** | Batch outputs, session trees, parquets, large CSVs, PDF/PNG/SVG figures, external archives |
| **Never** | Raw Motive CSVs at full scale, `.venv/`, generated batch folders |

Current `.gitignore` (Stage B.6) already covers most generated outputs.

---

## What should live outside the repo

| Location | Contents | Size (approx) |
|----------|----------|---------------|
| `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` | Layer 2 historical archive | ~22 GB |
| `../gaga_psylo_external_archive/archive_2026-06-30_cleanup_stage_B/` | Superseded L3 batches + L2.5 scratch | ~2 GB |
| Future external backups | Optional full project snapshots | TBD |

---

## What stays in current Layer folders (for now)

| Path | Why keep in place |
|------|-------------------|
| `Layer2_Motive_Kinematics/outputs/*_Take_*` | Active pipeline input; Layer 2.5 discovery |
| `Layer2_Motive_Kinematics/outputs/layer2_exports/` | Layer 2.5 ingestion |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | Layer 3 batch input |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | Canonical scientific results |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | Poster + manuscript CSV source |
| `outputs/poster_final_figures/` | Committed poster audit artifacts |

Moving these into `results/` is a **later migration** after path config is wired into scripts.

---

## What can be migrated later (safe phases)

| Phase | Action | Risk |
|-------|--------|------|
| **R6** | Symlinks in `results/active/` → canonical paths | Low |
| **R7** | `results/archive_index/external_archives.yaml` | Low |
| **R8** | Copy poster bundle to `results/poster/` | Low |
| **R9** | New batch outputs → `results/reports/<run_id>/` via config | Medium — needs code |
| **R10** | Git untrack legacy output files (`git rm --cached`) | Low for disk; medium for collaborators |

---

## Gitignore additions to consider (later, not applied in R2)

```gitignore
# results/generated/   — if large ad-hoc outputs land under results/reports/
# results/active/*.parquet  — symlinks OK; don't track targets
```

No `.gitignore` changes in R2.

---

*Structure created 2026-06-30. Empty `results/*` subfolders are placeholders only.*
