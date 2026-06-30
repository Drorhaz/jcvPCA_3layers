# F1 + F2 Execution Plan

**Date:** 2026-06-30  
**Authority:** [`FINAL_CLEANUP_PLAN.md`](FINAL_CLEANUP_PLAN.md)  
**Not in scope:** F3 deletions, smoke batch physical move, raw data, canonical batch, L2 sessions, L2.5 exports

---

## Pre-flight validation

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
python scripts/check_project_paths.py
```

---

## Batch F1 — Safe internal organization

| # | Source | Destination | Reason | Risk | Validation | Rollback |
|---|--------|-------------|--------|------|------------|----------|
| F1.1 | *(create)* | `results/smoke_tests/README.md` | Smoke-test index | Low | Read file | `rm` file |
| F1.2 | *(create)* | `results/smoke_tests/SMOKE_BATCH_671.md` | Move pointer from `results/active/` | Low | Read file | `mv` back to active |
| F1.3 | *(create)* | `results/reports/README.md` | Sidecar report index | Low | Read file | `rm` file |
| F1.4 | `PROJECT_STATUS.md` | `docs/PROJECT_STATUS.md` | Root slimming | Low | Path check | `mv docs/PROJECT_STATUS.md .` |
| F1.5 | `Layer3_JcvPCA/backend_readiness_report.md` | `docs/legacy/layer3/backend_readiness_report.md` | Layer root clutter | Low | Path check | Reverse `mv` |
| F1.6 | `docs/research_recovery/M12_PRE_ANALYSIS_READINESS.md` | Git track (no move) | Operational doc | Low | — | — |
| F1.7 | `Layer2_Motive_Kinematics/outputs/stage*_index.*` + QC manifests + README | Git track (no move) | L2 navigation indices | Low | — | — |
| F1.8 | `README.md` | Update links to `docs/legacy/` | Stale paths post-W3a | Low | Manual read | `git checkout README.md` |
| F1.9 | `README_WORKING.md` | F1/F2 status + link fixes | Daily guide | Low | Manual read | `git checkout README_WORKING.md` |
| F1.10 | `results/README.md` | Add smoke_tests/reports sections | Results hub | Low | Read file | `git checkout` |
| F1.11 | `docs/CLEANUP_INDEX.md` | Fix PROJECT_STATUS link | Doc consistency | Low | Read file | `git checkout` |
| F1.12 | `results/archive_index/EXTERNAL_ARCHIVE.md` | Add F2 archive path (post-F2) | Archive map | Low | Read file | `git checkout` |

---

## Batch F2 — External archive move

**Archive base:** `../gaga_psylo_external_archive/final_cleanup_2026-06-30/`

| # | Source | Destination | Reason | Risk | Validation | Rollback |
|---|--------|-------------|--------|------|------------|----------|
| F2.1 | `Layer3_JcvPCA/outputs/_workbench_*` (8 dirs) | `.../layer3_workbench_scratch/` | Dev scratch; not in yaml | Low | Path check + L3 help | `mv .../_workbench_* Layer3_JcvPCA/outputs/` |
| F2.2 | `Layer3_JcvPCA/outputs/671_g4_validation_001/` | `.../layer3_early_validation/` | Superseded pilot | Low | Path check | `mv .../671_g4_validation_001 Layer3_JcvPCA/outputs/` |
| F2.3 | `Layer2_Motive_Kinematics/Archive.zip` | `.../layer2_archive_zip/Archive.zip` | Legacy zip | Low | Path check | `mv .../Archive.zip Layer2_Motive_Kinematics/` |
| F2.4 | `Layer1_motive_qc/motive_qc/outputs/` (full tree) | `.../layer1_qc_outputs/` | Regeneratable QC (~68M) | Medium | Path check | `mv .../layer1_qc_outputs Layer1_motive_qc/motive_qc/outputs` |

**Explicitly NOT moving:** canonical batch, smoke batch, poster figures/evidence, L2 sessions, L2.5 exports, raw data.

**Post F2.4:** recreate empty `Layer1_motive_qc/motive_qc/outputs/runs/` and `batch_runs/` for future L1 runs.

---

## Post-execution validation

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
python scripts/check_project_paths.py
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341
test -d Layer2.5_Segmentation/outputs/pre_jvcpca_review/671
cd Layer3_JcvPCA/scripts
../.venv/bin/python run_gaga_batch_jcvpca.py --help
```

**Expected:** exit 0; protected paths exist; no `_workbench_*` under L3 outputs.

---

## Move log

Recorded in [`FINAL_CLEANUP_MOVE_LOG.csv`](FINAL_CLEANUP_MOVE_LOG.csv) at F2 execution.

---

*Execution plan — proceed to F1 then F2.*
