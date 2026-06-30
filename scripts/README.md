# Root script runners

Run pipeline entry points from repository root. Each wrapper forwards CLI args to the underlying script using the correct layer `.venv`.

| Wrapper | Underlying | venv | cwd |
|---------|------------|------|-----|
| [`run_health_check.py`](run_health_check.py) | `check_project_paths.py` | system | repo root |
| [`run_layer1_qc.py`](run_layer1_qc.py) | `Layer1_motive_qc/motive_qc/motive_batch_qc.py` | L1 | `motive_qc/` |
| [`run_layer2_session.py`](run_layer2_session.py) | `python -m layer2_motive.cli` | L2 | `Layer2_Motive_Kinematics/` |
| [`run_layer2_5_export.py`](run_layer2_5_export.py) | `Layer2.5_Segmentation/scripts/build_gaga_exports.py` | L2.5 | `Layer2.5_Segmentation/` |
| [`run_layer3_batch.py`](run_layer3_batch.py) | `Layer3_JcvPCA/scripts/run_gaga_batch_jcvpca.py` | L3 | repo root |
| [`run_layer3_validate.py`](run_layer3_validate.py) | L3 report validators (read-only) | L3 | `Layer3_JcvPCA/scripts/` |

## Examples

```bash
python scripts/run_health_check.py
python scripts/run_layer1_qc.py --config config.yaml --discover
python scripts/run_layer2_session.py --help
python scripts/run_layer2_5_export.py --help
python scripts/run_layer3_batch.py --help
python scripts/run_layer3_validate.py
```

Poster scripts remain at repo root: `make_poster_final_figures.py`, `make_poster_671_figures.py`.

See [`RUN.md`](../RUN.md) for the full command reference.
