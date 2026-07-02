# G3 — Joint / Link QC recommendations (2026-07-01)

**Mode:** Read-only advisory layer on G2 — no runner rewiring, no config edits, no analysis execution.

## Modules

| Module | Role |
|--------|------|
| `src/inclusion_recommendations.py` | P-phase inclusion verdicts from G2 readiness |
| `src/comparison_readiness.py` | Cross-timepoint comparison validity |
| `src/joint_link_qc.py` | Link / body-region caution from window + L2 artifacts |
| `src/body_regions.py` | Coarse body-region tagging |
| `src/recommend.py` | Extended gate + comparison recommendations |

## GUI

- `Dashboard/pages/3_Joint_Link_QC.py` — inclusion, link/body-region, comparison tabs
- Panels added to `0_Project_Overview.py` and `1_Data_Readiness.py`

## Verdict vocabulary (advisory)

`ready` · `caution` · `not_recommended` · `blocked` · `insufficient_data` · `missing`

Link-level: `usable` · `caution` · `not_recommended`

## Tests

```bash
Layer3_JcvPCA/.venv/bin/python -m pytest \
  tests/test_inclusion_recommendations.py \
  tests/test_comparison_readiness.py \
  tests/test_joint_link_qc.py \
  tests/test_recommend.py -q
```
