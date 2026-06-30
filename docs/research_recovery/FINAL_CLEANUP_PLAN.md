# Final Cleanup Plan — Research-Ready Directory Structure

**Date:** 2026-06-30  
**Mode:** Planning only — **no moves, no deletions, no source edits, no analysis**  
**Status:** Project is runnable (M12a pass, M12b smoke pass, W3a doc clutter committed `38c4ea9`)

**Related docs:**

- [`W1_WORKSPACE_SURFACE_AUDIT.md`](W1_WORKSPACE_SURFACE_AUDIT.md)
- [`W2_TARGET_VISIBLE_STRUCTURE.md`](W2_TARGET_VISIBLE_STRUCTURE.md)
- [`W3_WORKSPACE_SIMPLIFICATION_MOVE_PLAN.md`](W3_WORKSPACE_SIMPLIFICATION_MOVE_PLAN.md)
- [`W3A_SAFE_VISIBLE_CLEANUP_LOG.md`](W3A_SAFE_VISIBLE_CLEANUP_LOG.md)
- [`M12A_VALIDATION_LOG.md`](M12A_VALIDATION_LOG.md)
- [`M12B_671_SMOKE_BATCH_LOG.md`](M12B_671_SMOKE_BATCH_LOG.md)
- [`CONTINUATION_RUNBOOK.md`](CONTINUATION_RUNBOOK.md)
- [`README_WORKING.md`](../../README_WORKING.md)
- [`config/paths.yaml`](../../config/paths.yaml)

---

## Executive summary

The repo is **~62 GB on disk** but only a small fraction is needed for daily continuation work. Layer folders must stay where code expects them; cleanup finishes by:

1. **Navigation** — populate `results/` with pointers (F1)
2. **External archive** — move scratch/heavy reproducible outputs off-repo (F2)
3. **Approved deletion only** — remove archived stubs/duplicates after explicit sign-off (F3)

**Disk snapshot (2026-06-30):**

| Area | Size | Role |
|------|------|------|
| Layer 2 (data + outputs) | ~54 GB | Active sessions + raw inputs |
| Layer 3 outputs | ~4.5 GB | Canonical batch + smoke + scratch |
| Layer 2.5 | ~2.0 GB | L2.5 exports (~1.2 GB in `pre_jvcpca_review`) |
| Layer 1 | ~1.5 GB | QC code + outputs |
| Root test export | ~232 MB | `671_test_data_des/` |
| Poster figures | ~13 MB | `outputs/poster_final_figures/` |
| Docs | ~9 MB | Plans, recovery logs, legacy |

---

## Classification key (used throughout)

| Code | Meaning |
|------|---------|
| **A** | Keep active — needed for current work |
| **B** | Keep but hide behind `results/` pointers or docs |
| **C** | Move to clean internal folder (`results/`, `docs/legacy/`) |
| **D** | Move to external archive |
| **E** | Delete candidate (F3 only, after archive + approval) |
| **F** | Manual review required |
| **G** | Never touch without explicit migration project |

---

## 1. Minimum structure needed to continue analysis

### Design principle: hybrid layout

**Do not flatten** layer trees into new `data/` / `processed/` roots without updating [`config/paths.yaml`](../../config/paths.yaml) and all scripts. Instead:

- **Physical paths** stay layer-coupled (runnable today)
- **Human navigation** uses `results/` + [`README_WORKING.md`](../../README_WORKING.md)

```text
3Layers_project/                          ← control panel
├── README_WORKING.md                     ← daily front door
├── README.md                             ← scientific overview
├── PROJECT_STATUS.md                     ← checkpoint (F1 → docs/)
├── config/paths.yaml                     ← single path registry
├── src/project_paths.py                  ← yaml loader
├── scripts/                              ← health check + poster scripts
├── docs/                                 ← all documentation
│   ├── research_recovery/                ← runbook, M/R/W logs, THIS PLAN
│   ├── legacy/                           ← historical plans (W3a)
│   └── audits/                           ← audit reports (W3a)
├── results/                              ← lightweight indexes (not bulk data)
│   ├── active/                           ← canonical batch pointer
│   ├── smoke_tests/                      ← F1: smoke batch pointers
│   ├── poster/                           ← poster deliverable index
│   ├── reports/                          ← sidecar report index
│   └── archive_index/                    ← off-repo map
├── outputs/poster_final_figures/         ← poster PDFs/PNGs (yaml-registered)
├── Layer1_motive_qc/                     ← L1 code + raw QC data
├── Layer2_Motive_Kinematics/             ← L2 code + data + session outputs
├── Layer2.5_Segmentation/                ← L2.5 code + pre_jvcpca exports
├── Layer3_JcvPCA/                        ← L3 code + batches + sidecars
└── 671_test_data_des/                    ← registered test export (raw)

../gaga_psylo_external_archive/           ← off-repo historical bulk
```

### What belongs in each folder

| Path | Belongs here | yaml key (if any) |
|------|--------------|-------------------|
| [`config/`](../../config/) | `paths.yaml` only | — |
| [`src/`](../../src/) | `project_paths.py` | — |
| [`scripts/`](../../scripts/) | `check_project_paths.py`, `make_poster_*.py` | `poster.scripts` |
| [`docs/research_recovery/`](.) | Runbook, batch logs, cleanup plans | — |
| [`docs/legacy/`](../../docs/legacy/) | Master plan, layer planning docs | — |
| [`docs/audits/`](../../docs/audits/) | Layer audit reports | — |
| [`results/active/`](../../results/active/) | `CANONICAL_BATCH.md` | `results.active` |
| [`results/smoke_tests/`](../../results/smoke_tests/) *(F1)* | Smoke batch pointer + log links | *(optional future key)* |
| [`results/poster/`](../../results/poster/) | Poster README; future symlink to figures | `results.poster` |
| [`results/reports/`](../../results/reports/) | Sidecar report index READMEs | `results.reports` |
| [`results/archive_index/`](../../results/archive_index/) | External archive map | `results.archive_index` |
| **Raw data** | `Layer1_motive_qc/motive_qc/data/`, `Layer2_Motive_Kinematics/data/`, `671_test_data_des/`, `Layer2.5_Segmentation/data_description/` | `raw_data.*` |
| **Processed for JcvPCA** | `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | `layer2_5.pre_jvcpca_review` |
| **Active L2 sessions** | `Layer2_Motive_Kinematics/outputs/*_Take_*/` (12 trees, ~32 GB) | `layer2.active_session_glob` |
| **Canonical batch** | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` (~3.6 GB) | `layer3.canonical_batch` |
| **Smoke batch** | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` (~370 MB) | — |
| **Layer code** | Each `Layer*/src/`, `Layer*/scripts/`, `Layer*/tests/`, `.venv/` | `layer3.scripts`, etc. |
| **External archive** | `../gaga_psylo_external_archive/` | `external_archive.*` |

---

## 2. What must stay exactly where it is (G — never touch)

These paths are **hard guardrails**. Moving any of them requires a dedicated path-migration batch (former W3c) with yaml + script updates and full M12a-style validation.

| Path | Reason | yaml key |
|------|--------|----------|
| [`config/paths.yaml`](../../config/paths.yaml) | Single registry for all layers | all keys |
| [`src/project_paths.py`](../../src/project_paths.py) | Loads yaml; used by poster + report scripts | — |
| [`scripts/check_project_paths.py`](../../scripts/check_project_paths.py) | Health gate — run first always | — |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | JcvPCA input parquet (~1.2 GB) | `layer2_5.pre_jvcpca_review` |
| `Layer2.5_Segmentation/config/` | Feature manifests | `layer2_5.config_manifests` |
| `Layer2.5_Segmentation/segmentation/` | Segmentation xlsx | `layer2_5.segmentation_xlsx` |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | **Frozen canonical batch** (~3.6 GB, ~596 PNG plots, 14 top-level MD reports) | `layer3.canonical_batch` |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` | M12b pipeline proof (~370 MB) — no move until F2 approved | — |
| `Layer3_JcvPCA/scripts/` + `src/` + `.venv/` | Batch runner, validators, package | `layer3.scripts`, `layer3.src` |
| `Layer2.5_Segmentation/scripts/` | Export builders | — |
| `Layer2_Motive_Kinematics/outputs/*_Take_*/` | 12 active session trees (~32 GB) | `layer2.active_session_glob` |
| `Layer2_Motive_Kinematics/outputs/layer2_exports/` | L2 export bundle (~1 GB) | `layer2.layer2_exports` |
| `Layer2_Motive_Kinematics/data/` | Raw/regenerated L2 inputs (~21 GB) | `raw_data.layer2` |
| `Layer1_motive_qc/motive_qc/data/` | Raw marker CSVs | `raw_data.layer1` |
| `671_test_data_des/` | Test Motive export (~232 MB) | `raw_data.root_test_exports` |
| `outputs/poster_final_figures/` | Poster deliverables (49 files, ~13 MB) | `poster.final_figures` |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | Poster evidence CSV/MD | `layer3.poster_evidence_package` |

**Validation command (always):**

```bash
cd /path/to/3Layers_project
python scripts/check_project_paths.py
```

---

## 3. Visible clutter still on disk

### 3.1 Root (post-W3a)

| Path | Class | Notes |
|------|-------|-------|
| `README.md`, `README_WORKING.md` | A | Keep |
| `PROJECT_STATUS.md` | C | F1 → `docs/PROJECT_STATUS.md` |
| `671_test_data_des/` | G | Raw test export; gitignored CSV |
| `outputs/poster_final_figures/` | A/B | Active; 49 files; pointer in `results/poster/` |

**W3a already removed from root:** audit reports, `3_layers_Matser_plan_Full/` → [`docs/legacy/master_plan/`](../../docs/legacy/master_plan/)

### 3.2 Layer 3 outputs (`Layer3_JcvPCA/outputs/` — ~4.5 GB)

| Path | Size | Class | Action |
|------|------|-------|--------|
| `gaga_batch_jcvpca_20260626_193319/` | 3.6G | G | Never move/delete |
| `gaga_batch_jcvpca_smoke_671_20260630_214341/` | 370M | A → D | Keep until M12d; F2 optional |
| `_workbench_comparability/` | 28K | D | F2 external archive |
| `_workbench_dataset_preview/` | 6.9M | D | F2 |
| `_workbench_full/` | 1.6M | D | F2 |
| `_workbench_inventory_preview/` | 20K | D | F2 |
| `_workbench_phase6/` | 1.0M | D | F2 |
| `_workbench_phase7/` | 1.2M | D | F2 |
| `_workbench_phase9/` | 1.3M | D | F2 |
| `_workbench_preflight/` | 32K | D | F2 |
| **All `_workbench_*` combined** | ~12M, 190 files | D | F2 |
| `671_g4_validation_001/` | 1.7M | D | F2 — superseded pilot |
| `layer3_jcvpca/` | 4K | E | F3 empty stub after F2 |
| `poster_ready_evidence_package/` | 908K | A | Keep |
| `nullspace_link_stability_review/` | 872K | B | F1 pointer in `results/reports/` |
| `movement_organization_question_report/` | 20K | B | F1 pointer |

### 3.3 Layer 2 outputs (`Layer2_Motive_Kinematics/outputs/` — ~32 GB)

| Path | Class | Action |
|------|-------|--------|
| 12 `*_Take_*` session trees (671×6, 252×6) | G | Active pipeline chain |
| `layer2_exports/` (~1 GB) | G | yaml-registered |
| `stage*_index.csv` + `.md` (16 files, untracked) | F → A | F1: commit for navigation or index in `results/reports/` |
| `layer2_qc_*_manifest.csv` (untracked) | F | F1 commit or index |
| `Archive.zip` (~380K) | D | F2 external archive |

Historical L2 bulk already off-repo: `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` (~22 GB, Stage R1).

### 3.4 Layer 2.5 outputs

| Path | Size | Class | Action |
|------|------|-------|--------|
| `pre_jvcpca_review/` | 1.2G | G | JcvPCA inputs — never move |
| `pre_jvpca_review/` | 4K | F | Typo folder; manifest stub only — confirm duplicate |
| `session_index.csv` | small | A | Keep |

### 3.5 Layer 1 outputs

| Path | Size | Class | Action |
|------|------|-------|--------|
| `motive_qc/outputs/runs/` | ~68M, 31 run dirs | D/E | Many duplicate 671 runs; F2 archive then F3 selective delete |
| `motive_qc/outputs/batch_runs/` | part of 68M | D | F2 |

### 3.6 Docs / git noise (untracked or modified)

| Path | Class | Action |
|------|-------|--------|
| `docs/research_recovery/M12_PRE_ANALYSIS_READINESS.md` | A | F1 commit |
| `Layer3_JcvPCA/docs/PHASE2_SCOPE.md` | F | Manual review — commit or legacy |
| `Layer3_JcvPCA/docs/figures/jcvpca_workflow/` | F | Manual review — commit or keep local |
| `Layer3_JcvPCA/references/JcvPCA and JsvCRP.pdf` (modified) | F | User decides; never auto-delete |
| `Layer3_JcvPCA/backend_readiness_report.md` | C | F1 → `docs/legacy/layer3/` |

### 3.7 Layer-level clutter

| Path | Class | Action |
|------|-------|--------|
| `Layer2.5_Segmentation/notebooks/` (2 ipynb) | F | Keep — L2.5 workflow |
| `Layer2_Motive_Kinematics/docs/` (~23 files) | C | F1 legacy index pointer |
| `Layer3_JcvPCA/references/` | A | Keep PDFs |
| `.cursor/`, `.pytest_cache/`, `.DS_Store` | — | Gitignored; no action |

### 3.8 Stale links (not clutter on disk, but confusing)

| File | Issue | F1 fix |
|------|-------|--------|
| [`README.md`](../../README.md) | Links to old `3_layers_Matser_plan_Full/` | Point to `docs/legacy/master_plan/` |
| [`Layer3_JcvPCA/README.md`](../../Layer3_JcvPCA/README.md) | References old master plan paths | Update doc links only |

---

## 4. Deletion candidates (F3 only — not executed)

**Rule:** Nothing in this section is deleted until: (1) archived in F2 if applicable, (2) listed in an approved F3 checklist, (3) user explicitly approves each path.

### 4.1 Low-risk deletion candidates (after F2 archive)

| Path | Why safe | Reproducible? | Gitignored? | Already archived? | Risk | Rollback | Approval |
|------|----------|---------------|-------------|-------------------|------|----------|----------|
| `Layer3_JcvPCA/outputs/layer3_jcvpca/` | Empty stub (4K) | N/A | Yes | Optional F2 | Low | Restore from F2 or ignore | Yes |
| `Layer2.5_Segmentation/outputs/pre_jvpca_review/` | Typo duplicate; 4K manifest stub | Yes (regenerate manifest) | Yes | N/A | Low | Copy manifest back | Yes — **confirm duplicate first** |
| Redundant L1 QC runs in `motive_qc/outputs/runs/` (keep 1×671 + 1×252 exemplar per need) | Duplicate smoke/debug runs | Yes — re-run L1 notebook | Yes | F2 full tree | Medium | Restore from F2 | Yes — per-run list |
| `.DS_Store` in any tracked path | OS metadata | N/A | Yes | N/A | Low | Recreate | Optional |

### 4.2 Not deletion candidates

| Path | Reason |
|------|--------|
| Canonical batch `193319/` | Frozen poster-era results; all plots/CSVs/reports |
| Smoke batch (until M12d + F2 archive) | M12b pipeline reference |
| Poster figures / evidence package | Active deliverables |
| L2 session outputs | Required for L2.5 re-export |
| L2.5 `pre_jvcpca_review/` | JcvPCA inputs |
| All raw data | Immutable |
| All source/scripts/tests | Runnable code |
| External archive copies | Recovery source for F3 |

### 4.3 Never delete (explicit deny list)

- `config/paths.yaml`, `src/project_paths.py`
- Any path in Section 2 (G table)
- Anything not listed in Section 4.1 with F2 backup verified
- Bulk `rm -rf` on any `Layer*/outputs/` glob

---

## 5. External archive candidates (F2)

**Target base (proposed):**

```
../gaga_psylo_external_archive/final_cleanup_2026-06-30/
├── layer3_workbench_scratch/
├── layer3_early_validation/
├── layer2_archive_zip/
├── layer1_qc_outputs/
└── layer3_smoke_batch_671/          ← optional, post-M12d only
```

**Move log (create at F2 execution):** `docs/research_recovery/FINAL_CLEANUP_MOVE_LOG.csv`

| # | Current path | Destination | Size | Reason | Risk | Gitignored? |
|---|--------------|-------------|------|--------|------|-------------|
| F2.1 | `Layer3_JcvPCA/outputs/_workbench_*` (8 dirs) | `.../layer3_workbench_scratch/` | ~12M | Dev/demo scratch; not in yaml | Low | Yes |
| F2.2 | `Layer3_JcvPCA/outputs/671_g4_validation_001/` | `.../layer3_early_validation/` | 1.7M | Superseded pilot ([`Layer3_JcvPCA/README.md`](../../Layer3_JcvPCA/README.md)) | Low | Yes |
| F2.3 | `Layer2_Motive_Kinematics/Archive.zip` | `.../layer2_archive_zip/` | 380K | Legacy zip | Low | Yes (`*.zip`) |
| F2.4 | `Layer1_motive_qc/motive_qc/outputs/` (full tree) | `.../layer1_qc_outputs/` | ~68M | Regeneratable QC runs/plots | Medium | Yes |
| F2.5 | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` | `.../layer3_smoke_batch_671/` | 370M | **Defer** until M12d validates full cohort | Medium | Yes |

### F2 — not external archive

- Canonical batch `193319`
- L2 `*_Take_*` sessions, `layer2_exports`
- L2.5 `pre_jvcpca_review`
- Poster figures, poster evidence
- Any raw data

### F2 validation (after each move batch)

```bash
cd /path/to/3Layers_project
python scripts/check_project_paths.py
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319
test -d Layer2.5_Segmentation/outputs/pre_jvcpca_review/671
cd Layer3_JcvPCA/scripts
../.venv/bin/python generate_final_integrated_review.py --validate-paths
../.venv/bin/python run_gaga_batch_jcvpca.py --help
```

**Expected:** all exit 0; canonical + exports still on disk.

### F2 rollback template

```bash
ARCHIVE=../gaga_psylo_external_archive/final_cleanup_2026-06-30

# Example: restore workbench scratch
mv "$ARCHIVE/layer3_workbench_scratch/_workbench_"* Layer3_JcvPCA/outputs/

# Example: restore early validation
mv "$ARCHIVE/layer3_early_validation/671_g4_validation_001" Layer3_JcvPCA/outputs/
```

Then re-run validation block above.

---

## 6. Internal organization moves (F1)

**No physical moves of yaml-registered output trees in F1** — pointers and docs only.

| # | Source | Destination | Reason | yaml update? | Code update? | Validation |
|---|--------|-------------|--------|--------------|--------------|------------|
| F1.1 | *(create)* | `results/smoke_tests/README.md` | Dedicated smoke-test index | No | No | Read file |
| F1.2 | `results/active/SMOKE_BATCH_671.md` | Keep + cross-link from `results/smoke_tests/` | Clarify active vs smoke | No | No | Read file |
| F1.3 | *(create)* | `results/reports/README.md` | Index sidecar reports | No | No | Read file |
| F1.4 | `PROJECT_STATUS.md` | `docs/PROJECT_STATUS.md` | Root slimming | No | Update README links | Path check |
| F1.5 | `Layer3_JcvPCA/backend_readiness_report.md` | `docs/legacy/layer3/backend_readiness_report.md` | Layer root clutter | No | No | Path check |
| F1.6 | `docs/research_recovery/M12_PRE_ANALYSIS_READINESS.md` | Commit to git | Operational readiness doc | No | No | — |
| F1.7 | `Layer2_Motive_Kinematics/outputs/stage*_index.*` | Git commit (navigation) | Small indices for L2 browsing | No | No | — |
| F1.8 | [`README.md`](../../README.md) | Update links to `docs/legacy/master_plan/` | Fix stale paths post-W3a | No | No | Manual read |
| F1.9 | [`README_WORKING.md`](../../README_WORKING.md) | Add F1/F2/F3 next steps | Daily guide | No | No | Manual read |
| F1.10 | [`results/README.md`](../../results/README.md) | Add smoke_tests + reports sections | Results hub | No | No | — |

### Deferred (post-F1 — requires yaml + script refactor)

| Source | Destination | yaml? | Code? |
|--------|-------------|-------|-------|
| `outputs/poster_final_figures/` | `results/poster/final_figures/` | **Yes** `poster.final_figures` | **Yes** `make_poster_*.py` |
| Sidecar report dirs | `results/reports/*` physical copy | Maybe | **Yes** report script defaults |
| Symlink `results/active/canonical_batch` → L3 batch | Shorter human path | Optional | Maybe |

---

## 7. Script inventory

### 7.1 Required daily commands

| Script | Path | Command |
|--------|------|---------|
| Path check | [`scripts/check_project_paths.py`](../../scripts/check_project_paths.py) | `python scripts/check_project_paths.py` |
| L3 batch help | `Layer3_JcvPCA/scripts/run_gaga_batch_jcvpca.py` | `../.venv/bin/python run_gaga_batch_jcvpca.py --help` |
| Integrated review validate | `Layer3_JcvPCA/scripts/generate_final_integrated_review.py` | `--validate-paths` |
| Master report dry-run | `Layer3_JcvPCA/scripts/generate_master_full_numeric_report.py` | `--dry-run` |

**Python env for L3:** `Layer3_JcvPCA/.venv/bin/python` (not system Python — see [`M12A_VALIDATION_LOG.md`](M12A_VALIDATION_LOG.md))

### 7.2 Root scripts (`scripts/`)

| Script | Class | Notes |
|--------|-------|-------|
| `check_project_paths.py` | **Required daily** | Health gate |
| `make_poster_final_figures.py` | Poster / one-off | Reads canonical batch via config |
| `make_poster_671_figures.py` | Poster / one-off | 671-specific figures |

### 7.3 Layer 2 scripts (`Layer2_Motive_Kinematics/scripts/`)

| Script | Class |
|--------|-------|
| `export_layer2_sessions.py` | **Active pipeline** |
| `generate_pre_stage07_gate.py` | Active pipeline |
| `stage05_sign_flip_diagnostic.py` | Diagnostic — keep |
| `analyze_stage07_jump_duration.py` | Diagnostic — manual review |

### 7.4 Layer 2.5 scripts (`Layer2.5_Segmentation/scripts/`)

| Script | Class |
|--------|-------|
| `build_gaga_exports.py` | **Active pipeline** |
| `build_pre_jvcpca_review.py` | **Active pipeline** |
| `validate_pilot_export.py` | **Active pipeline** |
| `validate_segmentation_inputs.py` | Active pipeline |
| `review_segmentation_window.py` | Active pipeline |
| `inspect_jvcpca_parquet.py` | Diagnostic — keep |
| `build_pilot_safety_report.py` | Report — manual review |

### 7.5 Layer 3 scripts (`Layer3_JcvPCA/scripts/` — 24 files)

| Script | Class |
|--------|-------|
| `run_gaga_batch_jcvpca.py` | **Required / active pipeline** |
| `layer3_batch_report_paths.py` | **Active pipeline** (shared helper) |
| `generate_final_integrated_review.py` | **Report — validate daily** |
| `generate_master_full_numeric_report.py` | **Report — dry-run daily** |
| `generate_movement_organization_question_report.py` | Report — validate |
| `generate_directional_robustness_full_numeric_report.py` | Report generation |
| `generate_directional_robustness_t1_t2_full_numeric_report.py` | Report generation |
| `generate_directional_robustness_t2_t3_full_numeric_report.py` | Report generation |
| `generate_natural_variability_full_numeric_report.py` | Report generation |
| `generate_nullspace_full_numeric_report.py` | Report generation |
| `generate_pc_focus_review.py` | Report generation |
| `generate_poster_evidence_report.py` | Poster chain |
| `generate_poster_ready_evidence_package.py` | Poster chain |
| `analyze_directional_robustness_t1_t2.py` | Analysis — on demand |
| `analyze_directional_robustness_t1_t3.py` | Analysis — on demand |
| `analyze_directional_robustness_t2_t3.py` | Analysis — on demand |
| `analyze_natural_variability_deep_dive.py` | Analysis — on demand |
| `analyze_nullspace_link_stability.py` | Analysis — on demand |
| `analyze_link_contribution_distribution.py` | Analysis — on demand |
| `analyze_timepoint_link_contribution.py` | Analysis — on demand |
| `prepare_joint_heatmap_tables.py` | Analysis — on demand |
| `run_pc_focus_p50_p60_sensitivity.py` | Poster-era sensitivity — keep, not daily |
| `update_pc_focus_interpretation_artifacts.py` | Poster-era — manual review |
| `run_layer3_jcvpca.py` | Legacy single-config runner — secondary path |

### 7.6 Layer 1 scripts

| Script | Class |
|--------|-------|
| `motive_qc/scripts/build_modules.py` | L1 pipeline |
| `motive_qc/scripts/split_motive_qc.py` | L1 pipeline |
| `motive_batch_qc.py`, `motive_raw_qc.py` | L1 entry points |

### 7.7 Script delete/archive candidates

**None approved for F3.** All scripts above remain until explicit per-script review. Do not delete scripts without confirming no runbook reference.

---

## 8. Figure and plot inventory

| Category | Location | Count (approx.) | Class | Action |
|----------|----------|-----------------|-------|--------|
| **Canonical poster/final figures** | `outputs/poster_final_figures/` | 49 files (~13 MB) | A | Keep; indexed in `results/poster/` |
| **Canonical batch plots** | `.../193319/plots/` | ~596 PNG | G | Inside frozen batch — never separate |
| **Smoke batch plots** | `.../smoke_671.../plots/` | ~74 PNG | A → D | F2 optional after M12d |
| **Poster evidence tables** | `poster_ready_evidence_package/` | CSV/MD | A | Keep |
| **Workbench exploratory** | `_workbench_*/` | mixed PNG/CSV | D | F2 archive |
| **L1 QC plots** | `motive_qc/outputs/runs/*/plots/` | per run | D/E | F2 then selective F3 |
| **Regeneratable batch plots** | Any `gaga_batch_jcvpca_*` | — | — | Reproduce via `run_gaga_batch_jcvpca.py` |

### Poster figure sample (root `outputs/poster_final_figures/`)

- `figure_A_longitudinal_shift_vs_NV.{pdf,png,svg}`
- `figure_B_functional_vs_nullspace_family.{pdf,png,svg}`
- `figure_A_plot_table.csv`, `data_validation_report.md`, etc.

### Canonical batch top-level reports (14 MD in `193319/`)

Includes: `FINAL_integrated_deep_review_after_p50_p60.md`, `joint_heatmap_full_numeric_report.md`, `directional_robustness_t1_t3_FULL_NUMERIC_REPORT.md`, `batch_summary.md`, etc. — **G, never delete.**

---

## 9. Final execution plan — three batches only

### Batch F1 — Safe internal organization

**Scope:** Docs, pointer READMEs, README link fixes, commit readiness docs. **No** bulk output moves. **No** raw data. **No** canonical/smoke batch moves.

| Item | Risk |
|------|------|
| All Section 6 F1 rows | Low |

**Exact folders affected:**

- `results/smoke_tests/` *(new)*
- `results/reports/` *(new README)*
- `docs/PROJECT_STATUS.md` *(move from root)*
- `docs/legacy/layer3/backend_readiness_report.md` *(move)*
- `docs/research_recovery/M12_PRE_ANALYSIS_READINESS.md` *(commit)*
- `README.md`, `README_WORKING.md`, `results/README.md` *(doc edits only)*

**Validation:**

```bash
python scripts/check_project_paths.py
```

**Rollback:** reverse `mv` for any moved doc; revert README edits from git.

**Commit message:** `docs: organize results pointers and legacy docs (F1)`

**Stop conditions:**

- Any staged path under `Layer*/outputs` bulk trees
- Any raw data path staged
- Path check exit non-zero after changes

---

### Batch F2 — External archive move

**Scope:** Move scratch/heavy reproducible outputs to `../gaga_psylo_external_archive/final_cleanup_2026-06-30/`. **No deletion.**

| Item | Risk |
|------|------|
| F2.1–F2.4 (workbench, pilot validation, Archive.zip, L1 QC outputs) | Low–medium |
| F2.5 smoke batch | **Defer** — medium; requires explicit approval |

**Exact folders affected (default F2):**

```
Layer3_JcvPCA/outputs/_workbench_comparability
Layer3_JcvPCA/outputs/_workbench_dataset_preview
Layer3_JcvPCA/outputs/_workbench_full
Layer3_JcvPCA/outputs/_workbench_inventory_preview
Layer3_JcvPCA/outputs/_workbench_phase6
Layer3_JcvPCA/outputs/_workbench_phase7
Layer3_JcvPCA/outputs/_workbench_phase9
Layer3_JcvPCA/outputs/_workbench_preflight
Layer3_JcvPCA/outputs/671_g4_validation_001
Layer2_Motive_Kinematics/Archive.zip
Layer1_motive_qc/motive_qc/outputs/
```

**Validation:**

```bash
python scripts/check_project_paths.py
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319
test -d Layer2.5_Segmentation/outputs/pre_jvcpca_review/671
cd Layer3_JcvPCA/scripts
../.venv/bin/python generate_final_integrated_review.py --validate-paths
../.venv/bin/python run_gaga_batch_jcvpca.py --help
```

**Rollback:** `mv` from external archive back to original paths (see Section 5).

**Commit message:** `docs: log F2 external archive moves` (+ `FINAL_CLEANUP_MOVE_LOG.csv` only — not archived binaries)

**Stop conditions:**

- Path check fails
- Canonical batch, smoke batch (if not approved), or L2.5 exports missing
- L3 validators fail

---

### Batch F3 — Deletion candidates (explicit approval per item)

**Scope:** Only paths in Section 4.1, each individually approved, each verified archived in F2 where applicable. **Never bulk delete.**

| Item | Risk |
|------|------|
| `layer3_jcvpca/` stub | Low |
| `pre_jvpca_review/` typo folder | Low (after duplicate confirm) |
| Selected redundant L1 QC runs | Medium |

**Validation:**

```bash
python scripts/check_project_paths.py
# Document regenerate command for any deleted reproducible artifact
```

**Rollback:** restore from `../gaga_psylo_external_archive/final_cleanup_2026-06-30/` only.

**Commit message:** `docs: record F3 approved deletions`

**Stop conditions:**

- Item not in Section 4.1
- No F2 archive copy when required
- User approval not recorded in `FINAL_CLEANUP_DELETION_LOG.md` *(create at F3 execution)*
- Any attempt to delete G-table paths (Section 2)

---

## 10. Clean project acceptance criteria

Cleanup is **finished** only when all of the following are true:

| # | Criterion |
|---|-----------|
| 1 | **Root readable** — only layer dirs, `config/`, `src/`, `scripts/`, `docs/`, `results/`, `outputs/`, `README.md`, `README_WORKING.md`, `671_test_data_des/` (and optionally `docs/PROJECT_STATUS.md` moved) |
| 2 | **`results/` populated** — `active/`, `smoke_tests/`, `poster/`, `reports/`, `archive_index/` each have README pointers |
| 3 | **No workbench clutter** — zero `_workbench_*` under `Layer3_JcvPCA/outputs/` (archived in F2 or deleted in F3 after archive) |
| 4 | **Raw data protected** — all `raw_data.*` paths unchanged and documented in `README_WORKING.md` |
| 5 | **Processed data documented** — `pre_jvcpca_review/` path clear in `results/` + runbook |
| 6 | **Canonical batch documented** — `results/active/CANONICAL_BATCH.md` accurate; batch on disk intact |
| 7 | **Smoke batch documented or archived** — `results/smoke_tests/` + M12b log; on disk or external with pointer |
| 8 | **Path check passes** — `python scripts/check_project_paths.py` exit 0 |
| 9 | **L3 validators pass** — `--validate-paths` / `--dry-run` exit 0 with venv Python |
| 10 | **Move log complete** — `FINAL_CLEANUP_MOVE_LOG.csv` records every F2 move |
| 11 | **No analysis loss** — poster figures, evidence package, canonical batch reports/plots still reachable |
| 12 | **`README_WORKING.md` actionable** — states next command (M12c / M12d / F-batch) |

---

## Recommended execution order

```text
DONE ── W3a (doc clutter, commit 38c4ea9)
  │
  ▼
F1 ── pointers, legacy doc moves, README fixes, commit readiness docs
  │
  ▼
M12c ── 252 QC read-only (optional, parallel)
  │
  ▼
M12d ── full cohort batch (separate approval)
  │
  ▼
F2 ── external archive (workbench, pilot, L1 outputs, optional smoke)
  │
  ▼
F3 ── approved deletions only (stubs, duplicates, archived redundancy)
  │
  ▼
DONE ── acceptance criteria Section 10
```

---

## Quick reference — where to look

| I need… | Go here |
|---------|---------|
| What to run next | [`README_WORKING.md`](../../README_WORKING.md) |
| Full commands | [`CONTINUATION_RUNBOOK.md`](CONTINUATION_RUNBOOK.md) |
| Path registry | [`config/paths.yaml`](../../config/paths.yaml) |
| Health check | `python scripts/check_project_paths.py` |
| Canonical batch | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` |
| Smoke batch | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` |
| L2.5 exports | `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` |
| External archive | [`results/archive_index/EXTERNAL_ARCHIVE.md`](../../results/archive_index/EXTERNAL_ARCHIVE.md) |
| Legacy plans | [`docs/legacy/master_plan/MASTER_PLAN.md`](../../docs/legacy/master_plan/MASTER_PLAN.md) |

---

*Planning document only. No moves, deletions, source edits, or analysis executed. Execute F1/F2/F3 only with explicit approval per batch.*
