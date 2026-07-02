# G2 — Read-only GUI (2026-07-01)

**Mode:** Read-only — no runner rewiring, config editing, analysis execution, or runtime behavior changes.

## Views

| Page | File |
|------|------|
| Home | `Dashboard/status_dashboard.py` |
| Project Overview | `Dashboard/pages/0_Project_Overview.py` |
| Data Readiness | `Dashboard/pages/1_Data_Readiness.py` |
| Config / Thresholds | `Dashboard/pages/7_Config_Thresholds.py` |

Launch: `./Dashboard/run_dashboard.sh` or `python scripts/run_dashboard.py`

## Backend modules (pure Python, testable)

- `src/project_status.py` — paths + manifests + pipeline summary
- `src/readiness.py` — readiness matrix + threshold legend
- `src/comparability.py` — science-hash comparability banners
- `src/recommend.py` — read-only gate recommendations

## Tests

```bash
Layer3_JcvPCA/.venv/bin/python -m pytest tests/test_project_status.py tests/test_readiness.py tests/test_comparability.py tests/test_recommend.py tests/test_analysis_config.py -q
```
