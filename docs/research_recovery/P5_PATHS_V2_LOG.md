# P5 Data/Processed Hubs — Execution Log

**Date:** 2026-06-30  
**Phase:** P5

## Symlink hubs

| Hub | Target |
|-----|--------|
| `data/raw_layer1` | `Layer1_motive_qc/motive_qc/data` |
| `data/raw_layer2` | `Layer2_Motive_Kinematics/data` |
| `data/raw_layer2_5_descriptions` | `Layer2.5_Segmentation/data_description` |
| `data/test_exports` | `671_test_data_des` |
| `processed/layer2_outputs_root` | `Layer2_Motive_Kinematics/outputs` |
| `processed/pre_jvcpca_review` | `Layer2.5_Segmentation/outputs/pre_jvcpca_review` |

## Config

- `config/paths.yaml` — `data.*` and `processed.*` sections
- `src/project_paths.py` — registry + convenience properties

## Validation

```bash
python scripts/run_health_check.py
test -L data/raw_layer2
test -L processed/pre_jvcpca_review
```
