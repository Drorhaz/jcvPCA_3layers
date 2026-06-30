# P3 Symlink Migration — Execution Log

**Date:** 2026-06-30  
**Phase:** P3

## Symlinks created

| Symlink | Target |
|---------|--------|
| `results/active/canonical_batch` | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319` |
| `results/poster/final_figures` | `outputs/poster_final_figures` |
| `results/poster/evidence_package` | `Layer3_JcvPCA/outputs/poster_ready_evidence_package` |
| `results/reports/movement_organization` | `Layer3_JcvPCA/outputs/movement_organization_question_report` |
| `results/reports/nullspace_link_stability` | `Layer3_JcvPCA/outputs/nullspace_link_stability_review` |
| `results/smoke_tests/smoke_batch_671` | external archive (see below) |

## Smoke batch archive

| From | To |
|------|-----|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` | `../gaga_psylo_external_archive/final_cleanup_2026-06-30/smoke_batch_671_20260630/` |

## Config updates

- `config/paths.yaml` — layer3 sidecar keys, results symlinks, external archive final_cleanup
- `src/project_paths.py` — `_PATH_REGISTRY` extended

## Validation

```bash
python scripts/run_health_check.py
cd Layer3_JcvPCA/scripts && ../.venv/bin/python generate_final_integrated_review.py --validate-paths
cd Layer3_JcvPCA/scripts && ../.venv/bin/python run_gaga_batch_jcvpca.py --help
readlink results/active/canonical_batch
readlink results/smoke_tests/smoke_batch_671
```
