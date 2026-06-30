# R3 — Canonical Paths

**Date:** 2026-06-30  
**Registry file:** [`config/paths.yaml`](../../config/paths.yaml)  
**Convention:** Paths relative to repository root unless marked **external**.

---

## How to use this document

Each path has a **role tag**:

| Tag | Meaning |
|-----|---------|
| **input** | Upstream data consumed by pipelines |
| **generated output** | Reproducible from scripts |
| **active canonical result** | Current source of truth for analysis |
| **historical archive** | Superseded or audit-only; may be off-repo |
| **poster-only** | Publication deliverables |
| **future research output** | Target location for new work |

---

## Raw data

| Path | Role | Git | Notes |
|------|------|-----|-------|
| `Layer1_motive_qc/motive_qc/data/` | input | partial | Layer 1 QC inputs |
| `Layer2_Motive_Kinematics/data/` | input | partial | Motive CSV exports per participant |
| `Layer2.5_Segmentation/data_description/` | input | untracked | DataDescriptions sidecars |
| `671_test_data_des/` | input (review) | tracked | **Manual review** — export type unclear vs L1/L2 |

**Do not move raw data** without explicit approval.

---

## Layer 2 — active kinematics

| Path | Role | Git | Notes |
|------|------|-----|-------|
| `Layer2_Motive_Kinematics/outputs/*_Take_*/` | generated output | ignored (new) / legacy tracked | 12 sessions; 671 + 252 |
| `Layer2_Motive_Kinematics/outputs/layer2_exports/` | generated output | ignored | Parquet bundle for Layer 2.5 |
| `Layer2_Motive_Kinematics/outputs/stage*_index.*` | generated output | tracked | Pipeline indices |
| `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` | historical archive | external | **Moved R1** — audit reruns + old 671 snapshots |

---

## Layer 2.5 — pre-JcvPCA exports

| Path | Role | Git | Notes |
|------|------|-----|-------|
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | active canonical result | mixed | g4 export windows for 671/252 |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/_archive/` | historical archive | ignored | 2026-06-26 refresh snapshot |
| `Layer2.5_Segmentation/segmentation/*.xlsx` | input | tracked | Manual frame annotations |
| `Layer2.5_Segmentation/config/group4_*_manifest.csv` | input | untracked | Core link manifests |

Default discovery roots (`session_index.py`):

- Layer 1: `Layer1_motive_qc/motive_qc/outputs`
- Layer 2: `Layer2_Motive_Kinematics/outputs` (excludes `archive/` by code)

---

## Layer 3 — JcvPCA

| Path | Role | Git | Notes |
|------|------|-----|-------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | active canonical result | ignored | **Canonical batch** — 20/20 comparisons |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | active canonical result | untracked visible | Curated poster/manuscript CSVs |
| `Layer3_JcvPCA/outputs/_workbench_*` | generated output | ignored | Exploratory scratch |
| `Layer3_JcvPCA/scripts/` | source | untracked | Analysis/report generators |
| `Layer3_JcvPCA/src/layer3_jcvpca/` | source | untracked | Core library |

Batch ID in config: `gaga_batch_jcvpca_20260626_193319`

---

## Poster chain

| Path | Role | Git | Notes |
|------|------|-----|-------|
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | poster-only / active canonical | untracked | Primary CSV inputs |
| `outputs/poster_final_figures/` | poster-only | partial | CSV/MD tracked; PDF/PNG/SVG gitignored |
| `scripts/make_poster_final_figures.py` | source | tracked | 4-figure panel generator |
| `scripts/make_poster_671_figures.py` | source | tracked | 671-focused figures |

Reproduction chain:

```text
L2.5 exports → batch 193319 → evidence package → poster scripts → poster_final_figures
```

---

## Future research outputs (`results/`)

| Path | Role | Git | Notes |
|------|------|-----|-------|
| `results/active/` | future research output | TBD | Planned symlinks to canonical artifacts |
| `results/poster/` | poster-only | TBD | Optional frozen poster bundle |
| `results/manuscript/` | future research output | TBD | Manuscript tables/figures |
| `results/reports/` | future research output | ignore recommended | New analysis runs |
| `results/archive_index/` | documentation | track | External archive manifest |

Empty folders created in R2 — **no data moved yet**.

---

## External archive root

| Path | Role | Size | Contents |
|------|------|------|----------|
| `../gaga_psylo_external_archive/` | historical archive | ~24 GB | Parent for all off-repo archives |
| `.../archive_2026-06-30_cleanup_stage_B/` | historical archive | ~2 GB | Superseded L3 batches, L2.5 scratch |
| `.../layer2_outputs_archive_2026-06-30/` | historical archive | ~22 GB | Layer 2 `outputs/archive/` (R1) |

---

## Participants (canonical scope)

| ID | Role |
|----|------|
| `671` | Flagship / poster participant |
| `252` | Batch cohort participant |

Defined in `config/paths.yaml` under `participants:`.

---

## Path resolution for future automation

Recommended loader pattern (not implemented in R3):

```python
# Future: load config/paths.yaml once at CLI entry
from pathlib import Path
import yaml

def project_root() -> Path:
    return Path(__file__).resolve().parents[N]  # layer-specific

def load_paths() -> dict:
    with open(project_root() / "config" / "paths.yaml") as f:
        return yaml.safe_load(f)
```

---

*See [`R4_HARDCODED_PATHS_REVIEW.md`](R4_HARDCODED_PATHS_REVIEW.md) for migration priorities.*
