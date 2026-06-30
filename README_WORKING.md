# Working Guide — 3Layers JcvPCA Project

**Start here for daily work.**  
Scientific overview and git policy: [`README.md`](README.md)  
Cleanup history: [`docs/CLEANUP_INDEX.md`](docs/CLEANUP_INDEX.md)

---

## What is this project?

A three-layer pipeline from Motive marker QC → kinematic features → segmentation → **JcvPCA coordination analysis** for Gaga movement data (participants **671** and **252**).

**Current mode:** Research continuation — poster complete, canonical Layer 3 batch frozen, path registry in place, M12a validation and M12b smoke batch passed.

---

## Folders you normally need

| Purpose | Path |
|---------|------|
| **Path registry** | [`config/paths.yaml`](config/paths.yaml) |
| **Path loader** | [`src/project_paths.py`](src/project_paths.py) |
| **Health check** | [`scripts/check_project_paths.py`](scripts/check_project_paths.py) |
| **Operational docs** | [`docs/research_recovery/`](docs/research_recovery/) |
| **Legacy plans & audits** | [`docs/legacy/`](docs/legacy/) · [`docs/audits/`](docs/audits/) |
| **Results index** | [`results/`](results/) |
| **Layer 3 commands** | [`Layer3_JcvPCA/scripts/`](Layer3_JcvPCA/scripts/) |
| **Layer 3 Python env** | `Layer3_JcvPCA/.venv/bin/python` |

Open layer folders when re-running that layer:

| Layer | Code + env |
|-------|------------|
| Layer 1 QC | `Layer1_motive_qc/motive_qc/` |
| Layer 2 kinematics | `Layer2_Motive_Kinematics/` + `.venv` |
| Layer 2.5 segmentation/export | `Layer2.5_Segmentation/` + `.venv` |
| Layer 3 JcvPCA | `Layer3_JcvPCA/` + `.venv` |

---

## Do not touch (without explicit approval)

| Item | Why |
|------|-----|
| [`config/paths.yaml`](config/paths.yaml) | Breaks all path resolution |
| **Canonical batch** `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | Frozen poster-era results |
| **M12b smoke batch** `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` | Pipeline smoke test reference |
| Raw data trees (see below) | Protected capture data |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | Active JcvPCA export inputs |
| Anything under `../gaga_psylo_external_archive/` | Off-repo archives — move back only with a plan |

**Never** overwrite the canonical batch folder. New batches use a **new timestamped** `--output-dir`.

---

## Raw data and external archives

### Raw / protected (in repo, do not move)

| Data | Path |
|------|------|
| Layer 1 raw markers | `Layer1_motive_qc/motive_qc/data/` |
| Layer 2 inputs | `Layer2_Motive_Kinematics/data/` |
| Layer 2.5 descriptions | `Layer2.5_Segmentation/data_description/` |
| Root test export | `671_test_data_des/` |

Large CSVs are **gitignored** — they stay on disk locally.

### External archive (outside repo)

```
../gaga_psylo_external_archive/
├── final_cleanup_2026-06-30/              # F2 scratch archive (workbench, L1 QC, etc.)
├── layer2_outputs_archive_2026-06-30/     # Historical L2 outputs (~22 GB)
└── archive_2026-06-30_cleanup_stage_B/    # Superseded L3 batches, scratch
```

Registered in [`config/paths.yaml`](config/paths.yaml) under `external_archive.*`.  
Map: [`results/archive_index/EXTERNAL_ARCHIVE.md`](results/archive_index/EXTERNAL_ARCHIVE.md)

---

## Where results live

| Result | Path | Notes |
|--------|------|-------|
| **Canonical batch** | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | [`results/active/CANONICAL_BATCH.md`](results/active/CANONICAL_BATCH.md) |
| **M12b smoke batch (671)** | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` | [`results/smoke_tests/SMOKE_BATCH_671.md`](results/smoke_tests/SMOKE_BATCH_671.md) |
| **Poster evidence** | `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | |
| **Poster figures** | `outputs/poster_final_figures/` | [`results/poster/README.md`](results/poster/README.md) |
| **Layer 2.5 exports** | `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | Inputs for JcvPCA |
| **Layer 2 sessions** | `Layer2_Motive_Kinematics/outputs/*_Take_*` | Heavy; gitignored |

More detail: [`results/README.md`](results/README.md)

---

## Active scripts (by task)

### Always first — project health

```bash
cd /path/to/3Layers_project
python scripts/check_project_paths.py
```

Exit **0** required before exports or batches.

### Layer 3 validation (no regeneration)

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python generate_final_integrated_review.py --validate-paths
../.venv/bin/python generate_master_full_numeric_report.py --dry-run
../.venv/bin/python generate_movement_organization_question_report.py --validate-paths
```

Use **`Layer3_JcvPCA/.venv/bin/python`** — not system Python.

### Layer 3 batch (new folder only — requires approval)

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python run_gaga_batch_jcvpca.py \
  --participant 671 \
  --output-dir ../outputs/gaga_batch_jcvpca_$(date -u +%Y%m%d_%H%M%S)
```

Omit `--participant` only when intentionally running full cohort (671+252).

### Poster figures (optional regeneration)

```bash
python scripts/make_poster_final_figures.py
python scripts/make_poster_671_figures.py
```

Reads canonical batch paths from config.

---

## Is the project healthy?

```bash
python scripts/check_project_paths.py
```

Quick canonical check:

```bash
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319 && echo "canonical OK"
test -d Layer2.5_Segmentation/outputs/pre_jvcpca_review/671 && echo "671 exports OK"
```

---

## What to run next (recommended)

| Step | Status | Action |
|------|--------|--------|
| M12a validation | **Done** | [`M12A_VALIDATION_LOG.md`](docs/research_recovery/M12A_VALIDATION_LOG.md) |
| M12b 671 smoke batch | **Done** | [`M12B_671_SMOKE_BATCH_LOG.md`](docs/research_recovery/M12B_671_SMOKE_BATCH_LOG.md) |
| **W3a** | **Done** | [`W3A_SAFE_VISIBLE_CLEANUP_LOG.md`](docs/research_recovery/W3A_SAFE_VISIBLE_CLEANUP_LOG.md) |
| **F1 / F2** | **Done** | [`F1_F2_CLEANUP_LOG.md`](docs/research_recovery/F1_F2_CLEANUP_LOG.md) |
| **F3** | **Not started** | Deletion candidates only — explicit approval each item |
| **M12c** | **Next (optional)** | Read-only 252 QC — [`M12_PRE_ANALYSIS_READINESS.md`](docs/research_recovery/M12_PRE_ANALYSIS_READINESS.md) |
| **M12d** | **Not yet** | Full cohort batch after M12c |

**Suggested next command (read-only):**

```bash
python scripts/check_project_paths.py
# Then review 252 readiness:
# docs/research_recovery/M12_PRE_ANALYSIS_READINESS.md
```

---

## Full continuation runbook

Operational commands for 671/252, L2.5 export, batch promotion rules:

**[`docs/research_recovery/CONTINUATION_RUNBOOK.md`](docs/research_recovery/CONTINUATION_RUNBOOK.md)**

Also see:

- [`docs/research_recovery/MASTER_CONTINUATION_PLAN.md`](docs/research_recovery/MASTER_CONTINUATION_PLAN.md)
- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)
- [`FINAL_CLEANUP_PLAN.md`](docs/research_recovery/FINAL_CLEANUP_PLAN.md)
- Legacy master plan: [`docs/legacy/master_plan/MASTER_PLAN.md`](docs/legacy/master_plan/MASTER_PLAN.md)
- Workspace simplification: [`W1`](docs/research_recovery/W1_WORKSPACE_SURFACE_AUDIT.md) · [`FINAL_CLEANUP_PLAN`](docs/research_recovery/FINAL_CLEANUP_PLAN.md) · [`F1/F2 log`](docs/research_recovery/F1_F2_CLEANUP_LOG.md)

---

## Heavy folders (ignore in daily browsing)

These are **normal** — gitignored and/or large generated data:

- `Layer2_Motive_Kinematics/outputs/*_Take_*` (~32 GB)
- `Layer2_Motive_Kinematics/data/` (~21 GB)
- `Layer2.5_Segmentation/outputs/pre_jvcpca_review/{671,252}/`
- `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_*/` (canonical + smoke on disk)
- Workbench scratch archived to `../gaga_psylo_external_archive/final_cleanup_2026-06-30/` (F2)

---

*Daily working guide — updated 2026-06-30 after F1/F2 cleanup.*
