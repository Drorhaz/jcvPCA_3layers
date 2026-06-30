# F1 + F2 Cleanup Log

**Date:** 2026-06-30  
**Authority:** [`FINAL_CLEANUP_PLAN.md`](FINAL_CLEANUP_PLAN.md) · [`F1_F2_EXECUTION_PLAN.md`](F1_F2_EXECUTION_PLAN.md)  
**F3 executed:** **No**

---

## Summary

| Field | Result |
|-------|--------|
| **F1** | **Complete** — pointers, doc moves, README link fixes |
| **F2** | **Complete** — scratch archived off-repo (~82M) |
| **F3** | **Not executed** |
| **Path check** | Exit **0** |
| **L3 `--help`** | Exit **0** |
| **Raw data touched?** | **No** |
| **Outputs deleted?** | **No** — moves only |
| **Canonical batch touched?** | **No** |
| **Smoke batch touched?** | **No** (on disk; pointer moved to `results/smoke_tests/`) |

---

## F1 — Files created

| Path | Purpose |
|------|---------|
| `results/smoke_tests/README.md` | Smoke test index |
| `results/smoke_tests/SMOKE_BATCH_671.md` | M12b pointer (from `results/active/`) |
| `results/reports/README.md` | Sidecar report index |

## F1 — Files moved (in-repo)

| From | To |
|------|-----|
| `PROJECT_STATUS.md` | `docs/PROJECT_STATUS.md` |
| `Layer3_JcvPCA/backend_readiness_report.md` | `docs/legacy/layer3/backend_readiness_report.md` |
| `results/active/SMOKE_BATCH_671.md` | `results/smoke_tests/SMOKE_BATCH_671.md` |

## F1 — Files updated (content only)

| Path | Change |
|------|--------|
| `README.md` | Legacy master plan links; Layer 3 status; reviewer guide |
| `README_WORKING.md` | F1/F2 status, smoke pointer, external archive map |
| `results/README.md` | smoke_tests/reports sections |
| `results/archive_index/EXTERNAL_ARCHIVE.md` | F2 archive paths |
| `docs/CLEANUP_INDEX.md` | PROJECT_STATUS link |

## F1 — Git-tracked navigation indices (staged for commit)

Small L2 index files under `Layer2_Motive_Kinematics/outputs/` (not bulk session data):

- `stage00_01_report_index.*` through `stage08_filtering_index.*`
- `layer2_qc_session_manifest.csv`, `layer2_qc_link_manifest.csv`, `README.md`

Also: `docs/research_recovery/M12_PRE_ANALYSIS_READINESS.md`

---

## F2 — Exact commands run

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
ARCHIVE="../gaga_psylo_external_archive/final_cleanup_2026-06-30"

mkdir -p "$ARCHIVE/layer3_workbench_scratch" \
         "$ARCHIVE/layer3_early_validation" \
         "$ARCHIVE/layer2_archive_zip" \
         "$ARCHIVE/layer1_qc_outputs"

mv Layer3_JcvPCA/outputs/_workbench_* "$ARCHIVE/layer3_workbench_scratch/"
mv Layer3_JcvPCA/outputs/671_g4_validation_001 "$ARCHIVE/layer3_early_validation/"
mv Layer2_Motive_Kinematics/Archive.zip "$ARCHIVE/layer2_archive_zip/"
mv Layer1_motive_qc/motive_qc/outputs "$ARCHIVE/layer1_qc_outputs/"

mkdir -p Layer1_motive_qc/motive_qc/outputs/runs \
         Layer1_motive_qc/motive_qc/outputs/batch_runs
```

---

## F2 — Archive destination

```
../gaga_psylo_external_archive/final_cleanup_2026-06-30/
├── layer3_workbench_scratch/     ~12M  (8 _workbench_* dirs)
├── layer3_early_validation/      ~1.7M (671_g4_validation_001)
├── layer2_archive_zip/           ~380K (Archive.zip)
└── layer1_qc_outputs/            ~68M  (outputs/ tree)
```

**Not archived:** canonical batch, smoke batch, poster figures/evidence, L2 sessions, L2.5 exports, raw data.

---

## F2 — Layer 3 outputs after cleanup

```
Layer3_JcvPCA/outputs/
├── gaga_batch_jcvpca_20260626_193319/          # canonical
├── gaga_batch_jcvpca_smoke_671_20260630_214341/ # smoke
├── layer3_jcvpca/                              # empty stub (F3 candidate)
├── movement_organization_question_report/
├── nullspace_link_stability_review/
└── poster_ready_evidence_package/
```

No `_workbench_*` directories remain.

---

## Validation results

### Path check

```bash
python scripts/check_project_paths.py
```

**Exit 0** — `Path check passed (all required paths exist).`

### Protected paths

| Check | Result |
|-------|--------|
| Canonical batch | **OK** |
| Smoke batch on disk | **OK** |
| L2.5 671 exports | **OK** |
| L2 sessions (12) | **OK** |
| Raw data paths | **OK** |

### Layer 3 help

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python run_gaga_batch_jcvpca.py --help
```

**Exit 0**

---

## Rollback instructions

### F1 doc moves

```bash
mv docs/PROJECT_STATUS.md ./PROJECT_STATUS.md
mv docs/legacy/layer3/backend_readiness_report.md Layer3_JcvPCA/backend_readiness_report.md
mv results/smoke_tests/SMOKE_BATCH_671.md results/active/SMOKE_BATCH_671.md
```

### F2 external archive

```bash
ARCHIVE=../gaga_psylo_external_archive/final_cleanup_2026-06-30

mv "$ARCHIVE/layer3_workbench_scratch/_workbench_"* Layer3_JcvPCA/outputs/
mv "$ARCHIVE/layer3_early_validation/671_g4_validation_001" Layer3_JcvPCA/outputs/
mv "$ARCHIVE/layer2_archive_zip/Archive.zip" Layer2_Motive_Kinematics/
rm -rf Layer1_motive_qc/motive_qc/outputs
mv "$ARCHIVE/layer1_qc_outputs/outputs" Layer1_motive_qc/motive_qc/outputs
```

Then: `python scripts/check_project_paths.py`

Full move log: [`FINAL_CLEANUP_MOVE_LOG.csv`](FINAL_CLEANUP_MOVE_LOG.csv)

---

## Root / top-level after F1 + F2

```
671_test_data_des
Layer1_motive_qc
Layer2.5_Segmentation
Layer2_Motive_Kinematics
Layer3_JcvPCA
README.md
README_WORKING.md
config
docs
outputs
results
scripts
src
```

**Removed from root:** `PROJECT_STATUS.md` (→ `docs/`)

---

## Recommended next step

| Priority | Action |
|----------|--------|
| 1 | **M12c** — read-only 252 QC review |
| 2 | **M12d** — full cohort batch (separate approval) |
| 3 | **F3** — only with per-item approval after verifying F2 archive |

---

*F1/F2 execution log — committed with chore message.*
