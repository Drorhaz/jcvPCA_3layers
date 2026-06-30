# Movement organization sidecar report

**Physical path:** `Layer3_JcvPCA/outputs/movement_organization_question_report/`  
**Symlink (P3):** [`movement_organization`](movement_organization)

## Files

| File | Type |
|------|------|
| `gaga_movement_organization_question_report.md` | Main report |
| `movement_organization_question_metrics.csv` | Metrics table |

## Validate

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python generate_movement_organization_question_report.py --validate-paths
```

## Regenerate

Approve before running without `--dry-run` — overwrites sidecar MD/CSV outside canonical batch.
