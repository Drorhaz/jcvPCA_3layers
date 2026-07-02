# G4 — Analysis Request Builder (2026-07-01)

**Mode:** Validate and export intent only — `execution.allowed` always false; no runner calls.

## Schema

See `config/analysis_request.template.yaml` and saved instances under `requests/analysis_requests/`.

## Module

`src/analysis_request.py` — build, validate, save, load.

## GUI

`Dashboard/pages/4_Analysis_Request_Builder.py`

## Tests

```bash
Layer3_JcvPCA/.venv/bin/python -m pytest tests/test_analysis_request.py -q
```
