# P6 Physical Migration — Execution Log

**Date:** 2026-06-30  
**Phase:** P6a–P6d

## Physical moves

| From | To | Compat symlink at old path |
|------|-----|----------------------------|
| `Layer2_Motive_Kinematics/data/` | `data/raw_layer2/` | `Layer2_Motive_Kinematics/data` → `../data/raw_layer2` |
| `Layer2_Motive_Kinematics/outputs/` | `processed/layer2/` | `Layer2_Motive_Kinematics/outputs` → `../processed/layer2` |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | `processed/pre_jvcpca_review/` | `Layer2.5_Segmentation/outputs/pre_jvcpca_review` → `../../processed/pre_jvcpca_review` |
| `outputs/poster_final_figures/` | `results/poster/final_figures/` | `outputs/poster_final_figures` → `../results/poster/final_figures` |

## Config (paths.yaml v3)

Primary keys now point at physical `data/`, `processed/`, and `results/poster/final_figures`. Legacy layer paths remain as compatibility symlinks.

## Code (P6c)

| File | Change |
|------|--------|
| `scripts/make_poster_final_figures.py` | Removed hardcoded batch/out paths; uses `configure_poster_paths()` + yaml |
| `src/project_paths.py` | Added `processed.layer2` registry + property |
| `.gitignore` | P6 paths for `data/raw_layer2`, `processed/layer2`, poster at `results/` |

L3 report scripts already use `layer3_batch_report_paths.resolve_batch_report_paths()` (project_paths).

## Validation

```bash
python scripts/run_health_check.py
python scripts/run_layer3_validate.py
python scripts/run_layer3_batch.py --help
python scripts/make_poster_final_figures.py --help
```

## Rollback (inverse)

See `PHASE2_MOVE_LOG.csv` P6 rows. Reverse physical `mv` only after removing compat symlinks.
