# R7.2 — Read-Only Layer 3 Report Path Refactor

**Date:** 2026-06-30  
**Prerequisite commit:** `0e85781` — refactor: load evidence script paths from config registry  
**Scope:** Read-only batch report generators only — no `analyze_*`, batch runners, or artifact updaters.

---

## Scripts inspected

All Layer 3 scripts matching `gaga_batch_jcvpca_20260626_193319` in [`R4_HARDCODED_PATHS_REVIEW.md`](R4_HARDCODED_PATHS_REVIEW.md) were reviewed.

| Script | Role | R7.2 action |
|--------|------|-------------|
| `generate_final_integrated_review.py` | Read batch CSVs → integrated MD | **Refactored** |
| `generate_master_full_numeric_report.py` | Read batch CSVs → master numeric MD | **Refactored** |
| `generate_natural_variability_full_numeric_report.py` | Read NV sidecar CSVs → numeric MD | **Refactored** |
| `generate_pc_focus_review.py` | Report; imports `analyze_link_contribution_distribution` | **Skipped** — coupling to analysis module |
| `generate_nullspace_full_numeric_report.py` | Report from `outputs/nullspace_link_stability_review/` | **Skipped** — separate review dir + `analyze_nullspace_link_stability.py` dependency |
| `generate_directional_robustness_*_full_numeric_report.py` (×4) | Read DR sidecar CSVs | **Deferred** — same pattern; next batch |
| `generate_movement_organization_question_report.py` | Reads batch + poster package | **Deferred** |
| `prepare_joint_heatmap_tables.py` | Derives/writes heatmap tables | **Skipped** — writes derived outputs |
| `update_pc_focus_interpretation_artifacts.py` | Updates interpretation artifacts | **Skipped** — mutates batch artifacts |
| `analyze_*` (×6+) | Recompute analysis CSVs | **Skipped** — heavy analysis |
| `run_gaga_batch_jcvpca.py` | Full batch runner | **Skipped** — batch generation |
| `run_pc_focus_p50_p60_sensitivity.py` | Sensitivity recompute | **Skipped** — compute script |

---

## Scripts refactored

| File | Output (unchanged) |
|------|---------------------|
| `Layer3_JcvPCA/scripts/layer3_batch_report_paths.py` | **New** shared helper |
| `Layer3_JcvPCA/scripts/generate_final_integrated_review.py` | `FINAL_integrated_deep_review_after_p50_p60.md` |
| `Layer3_JcvPCA/scripts/generate_master_full_numeric_report.py` | `Gaga_JcvPCA_MASTER_full_numeric_report.md` |
| `Layer3_JcvPCA/scripts/generate_natural_variability_full_numeric_report.py` | `natural_variability_FULL_NUMERIC_REPORT.md` |

---

## Hard-coded paths removed

| Before | After |
|--------|-------|
| `Path(__file__).parents[1] / "outputs" / "gaga_batch_jcvpca_20260626_193319"` | `resolve_batch_report_paths().root` ← `layer3.canonical_batch` |
| Markdown header `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` (integrated review) | `` `{BATCH_DISPLAY}/` `` from config |
| Implicit fixed batch folder name | `BATCH_ID` from `layer3.canonical_batch_id` (available for future template use) |

Report content, calculations, and output filenames are unchanged.

---

## How paths are resolved

1. **`layer3_batch_report_paths.py`** inserts repo `src/` and calls `load_project_paths()`.
2. **`resolve_batch_report_paths()`** returns `BatchReportPaths(root, batch_id, batch_display, config_path)`.
3. Each report script sets module globals `ROOT`, `OUT`, `BATCH_ID`, `BATCH_DISPLAY` at import (if batch exists) and re-resolves in `main()` after CLI parsing.
4. Shared CLI via **`parse_batch_report_cli()`**:
   - `--config`
   - `--batch-dir`
   - `--validate-paths` — check batch root + required input CSVs; no MD write
   - `--dry-run` — print batch root and output path only

### Required input checks (`--validate-paths`)

| Script | Required inputs |
|--------|-----------------|
| Integrated review | `REQUIRED` list (33 batch artifacts) |
| Master numeric report | `MASTER_REQUIRED` from `BATCH_ARTIFACTS` (29 CSVs) |
| NV full numeric report | `NV_REPORT_REQUIRED` (6 NV sidecar CSVs from prior `analyze_natural_variability_deep_dive.py`) |

Missing batch root → `FileNotFoundError` with config path in message.

---

## Tests run

| Command | Result |
|---------|--------|
| `python scripts/check_project_paths.py` | **Exit 0** |
| `python3 -m py_compile` on 4 refactored/helper files | **Pass** |
| `--validate-paths` / `--dry-run` on refactored scripts | **Not run** — system Python lacks `pandas`/`scipy` (use Layer 3 venv) |
| Full report regeneration | **Not run** |

Example (Layer 3 venv, from `Layer3_JcvPCA/scripts/`):

```bash
python generate_final_integrated_review.py --validate-paths
python generate_master_full_numeric_report.py --dry-run
python generate_natural_variability_full_numeric_report.py --validate-paths
```

---

## Outputs regenerated?

**No.** No markdown reports were rewritten.

---

## Scientific logic changed?

**No.** Aggregation, interpretation text, thresholds, and report structure are unchanged. Only path resolution and CLI preflight were added.

---

## Remaining hard-coded paths

| Category | Examples | Next step |
|----------|----------|-----------|
| Directional robustness report generators (×4) | `ROOT = .../193319` | R7.3 — same helper |
| `generate_pc_focus_review.py` | Hard-coded root + import from `analyze_*` | R7.3 after decoupling or path-only pass |
| `generate_nullspace_full_numeric_report.py` | `BATCH` + external `REVIEW` dir | R7.3 with review-path config key |
| `generate_movement_organization_question_report.py` | Batch + poster package | R7.3 |
| All `analyze_*` scripts | `BATCH = ...` | R8+ — wire defaults only after reports done |
| `gaga_batch_runner.py` / `inventory.py` | Layer 2.5 default roots | R8 — library defaults |

---

## Recommended next stage (R7.3)

1. Refactor **`generate_directional_robustness_full_numeric_report.py`** and the three comparison-specific DR report scripts using `layer3_batch_report_paths.py`.
2. Refactor **`generate_pc_focus_review.py`** (path only; keep `analyze_link_contribution_distribution` import).
3. Add optional **`layer3.review_output_roots`** keys to `config/paths.yaml` for null-space review folders when refactoring `generate_nullspace_full_numeric_report.py`.

---

## Files changed (R7.2)

- `Layer3_JcvPCA/scripts/layer3_batch_report_paths.py` (new)
- `Layer3_JcvPCA/scripts/generate_final_integrated_review.py` (modified)
- `Layer3_JcvPCA/scripts/generate_master_full_numeric_report.py` (modified)
- `Layer3_JcvPCA/scripts/generate_natural_variability_full_numeric_report.py` (modified)
- `docs/research_recovery/R7_2_READONLY_REPORT_REFACTOR.md` (this file)
- `docs/research_recovery/R7_2_COMMIT_PLAN.md`

---

*No commit in R7.2. See [`R7_2_COMMIT_PLAN.md`](R7_2_COMMIT_PLAN.md).*
