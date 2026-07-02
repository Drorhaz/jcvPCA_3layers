# G5 — Dry-run execution planning log

**Phase:** G5 (PROGRAM_GUI_OPTIMIZATION_PLAN.md)  
**Status:** Complete  
**Date:** 2026-07-01  

## Scope delivered

G5 adds a **read-only execution planning layer** that translates validated `analysis_request.yaml` files into reviewable dry-run plans. No Layer 3 analysis runs; no runner rewiring; no config mutation; no canonical batch writes.

## Files created

| File | Role |
|------|------|
| `src/execution_plan.py` | Request-to-runner translation, preflight, output/repro specs |
| `Dashboard/pages/5_Execution_Plan.py` | Full dry-run preview GUI |
| `tests/test_execution_plan.py` | Unit tests |
| `docs/research_recovery/G5_EXECUTION_PLAN_LOG.md` | This log |

## Files modified

| File | Change |
|------|--------|
| `Dashboard/pages/4_Analysis_Request_Builder.py` | G5 dry-run preview panel + link to page 5 |

## Dry-run plan schema (version 1)

Top-level keys in `execution_plan.yaml`:

- `version`, `execution_plan_version` (`G5`), `plan_id`, `created_at`
- `source_request_id`, `source_request_path`, `source_request_status`, `plan_status`
- `execution` — `{ allowed: false, blocker_count, warning_count, note }`
- `preflight` — `{ blockers[], warnings[], advisory_notes[] }` (each item: level, code, message, source, field)
- `runner_translation` — mapped Layer 3 concepts (see below)
- `output_plan` — proposed batch layout, artifact classes, canonical guard
- `reproducibility_package` — future `_config_snapshot/` specification (not written to batches)

Saved under `requests/execution_plans/` on explicit user save only.

## Request → Layer 3 runner translation

1. Parse `analysis_request.yaml` → `AnalysisRequestInput` via `parse_request_to_input()`.
2. Resolve **blocks** from `selection.blocks` (fallback: `gaga_batch_runner.BLOCK_EXERCISES`).
3. Filter **comparison specs** to request `comparisons[]` IDs present in `build_comparison_specs()`.
4. Build **requested jobs** via `build_comparison_plan(participant, blocks, filtered_specs)`:
   - `comparison_key` = `{participant}_{block}_{comparison_id}`
   - Output dirs: `comparisons/{key}`, `plots/{participant}/{block}/{comparison_id}`
5. Map **PC focus spaces**: `all` → `all`, `functional` → `functional_p2`, `null_space` → `null_space_p2` (p=2).
6. Propose batch ID: `gaga_batch_jcvpca_<UTC_YYYYMMDD_HHMMSS>` under `layer3.outputs_root`.
7. Document **compatibility gaps** where current runner behavior differs (runs all comparisons, fixed PC focus, no request YAML input).

## Preflight checks

| Check | Level |
|-------|-------|
| Request status blocked | Blocker |
| Request status not validated/ready | Warning |
| `science_hash` mismatch vs current registry | Blocker |
| Missing request `science_hash` | Warning |
| `display_hash` mismatch | Warning |
| Re-run G4 `validate_analysis_request()` (errors/warnings/advisory) | Mapped |
| Resolved segment `matrix_path` / `manifest_path` exist | Blocker if missing |
| Central `layer25_export_manifest.csv` exists | Blocker if missing |
| Proposed batch path/id equals canonical | Blocker |
| G5 no-execution advisory | Advisory |

## Reproducibility metadata (future `_config_snapshot/`)

Would copy/generate at guarded execution time (G6+):

- `analysis_request.yaml`, `execution_plan.yaml`
- `analysis_params.yaml`, `qc_rules.yaml`, `segment_selection.yaml`, `gui_settings.yaml`
- `config_hash.json` (science + display hashes, match flags)
- `runner_metadata.json` (entrypoint, module, batch ID convention)
- `source_manifest_references.json` (L2.5 manifest, attempts, session index, segment count)

**Not written:** canonical batch path or existing batch directories.

## GUI

- **Page 5 — Execution Plan:** load saved request or builder session → build plan → blockers/warnings/jobs/outputs/repro spec → download/save plan YAML.
- **Page 4 — Builder:** compact G5 preview (blockers, job count, proposed batch ID) + link to page 5.

Both pages show `execution.allowed=false`.

## Runtime behavior

**No change** to `gaga_batch_runner.py`, batch scripts, or analysis pipelines. G5 imports runner helpers read-only for mapping.

## Verification

```bash
Layer3_JcvPCA/.venv/bin/python -m pytest tests/test_execution_plan.py tests/test_analysis_request.py -q
python scripts/run_health_check.py
```
