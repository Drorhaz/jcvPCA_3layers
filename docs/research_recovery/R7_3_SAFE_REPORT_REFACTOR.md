# R7.3 — Safe Layer 3 Report Path Refactor (Directional Robustness + Nullspace)

**Date:** 2026-06-30  
**Prerequisite commit:** `fbc8e75` — refactor: load read-only Layer 3 report paths from config  
**Scope:** Read-only report generators for directional robustness and nullspace review CSVs — no `analyze_*`, batch runners, or artifact updaters.

---

## Scripts inspected

All Layer 3 scripts listed in [`R4_HARDCODED_PATHS_REVIEW.md`](R4_HARDCODED_PATHS_REVIEW.md) and deferred in [`R7_2_READONLY_REPORT_REFACTOR.md`](R7_2_READONLY_REPORT_REFACTOR.md) were re-reviewed.

| Script | Role | R7.3 action |
|--------|------|-------------|
| `generate_directional_robustness_full_numeric_report.py` | T1 vs T3 DR numeric MD from batch sidecars | **Refactored** |
| `generate_directional_robustness_t1_t2_full_numeric_report.py` | T1 vs T2 DR numeric MD | **Refactored** |
| `generate_directional_robustness_t2_t3_full_numeric_report.py` | T2 vs T3 DR numeric MD | **Refactored** |
| `generate_nullspace_full_numeric_report.py` | Nullspace numeric MD from `nullspace_link_stability_review/` | **Refactored** |
| `generate_movement_organization_question_report.py` | Batch + poster package report | **Skipped** — reads poster package; deferred to R7.4 |
| `generate_pc_focus_review.py` | PC focus report | **Skipped** — imports `analyze_link_contribution_distribution` |
| `prepare_joint_heatmap_tables.py` | Derives heatmap tables + writes `joint_heatmap_full_numeric_report.md` | **Skipped** — writes derived batch artifacts (R7.2) |
| `analyze_directional_robustness_*.py` (×3) | Recompute DR CSVs | **Skipped** — heavy analysis |
| `analyze_nullspace_link_stability.py` | Recompute nullspace review CSVs | **Skipped** — heavy analysis |
| `prepare_joint_heatmap_tables.py` | Derives heatmap tables | **Skipped** — writes derived outputs |
| `update_pc_focus_interpretation_artifacts.py` | Updates batch artifacts | **Skipped** — mutates canonical batch |
| `run_gaga_batch_jcvpca.py` | Full batch runner | **Skipped** — batch generation |
| R7.2 scripts (integrated, master, NV) | Already on config | **No change** — committed in `fbc8e75` |

---

## Scripts refactored

| File | Input root | Output (unchanged) |
|------|------------|-------------------|
| `Layer3_JcvPCA/scripts/layer3_batch_report_paths.py` | — | **Extended** — optional `input_root` for preflight |
| `generate_directional_robustness_full_numeric_report.py` | Canonical batch | `directional_robustness_t1_t3_FULL_NUMERIC_REPORT.md` |
| `generate_directional_robustness_t1_t2_full_numeric_report.py` | Canonical batch | `directional_robustness_t1_t2_FULL_NUMERIC_REPORT.md` |
| `generate_directional_robustness_t2_t3_full_numeric_report.py` | Canonical batch | `directional_robustness_t2_t3_FULL_NUMERIC_REPORT.md` |
| `generate_nullspace_full_numeric_report.py` | `Layer3_JcvPCA/outputs/nullspace_link_stability_review/` | `nullspace_FULL_NUMERIC_REPORT.md` |

---

## Scripts skipped and why

| Script | Reason |
|--------|--------|
| `analyze_directional_robustness_*` | Recomputes sidecar CSVs — heavy analysis, out of R7.3 scope |
| `analyze_nullspace_link_stability.py` | Recomputes nullspace review folder — heavy analysis |
| `generate_movement_organization_question_report.py` | Cross-reads poster evidence package — needs poster path helper |
| `generate_pc_focus_review.py` | Runtime import of analysis module |
| `prepare_joint_heatmap_tables.py` | Writes heatmap tables + numeric MD | **Skipped** — mutates/writes batch artifacts |
| Batch generation / artifact mutators | Same exclusions as R7.2 |

---

## Hard-coded paths removed

| Before | After |
|--------|-------|
| `Path(__file__).parents[1] / "outputs" / "gaga_batch_jcvpca_20260626_193319"` | `resolve_batch_report_paths().root` ← `layer3.canonical_batch` |
| `ROOT / "outputs" / "nullspace_link_stability_review"` (nullspace only) | `{batch.parent} / "nullspace_link_stability_review"` with existence check |
| Markdown / JSON `Layer3_JcvPCA/outputs/{batch_name}/` strings | `` `{BATCH_DISPLAY}/` `` or `` `{REVIEW_DISPLAY}/` `` from config-relative display paths |

Report calculations, thresholds, filtering, ranking, and output filenames are unchanged.

---

## How paths are resolved

1. **Batch reports (directional robustness ×3)** reuse R7.2 helper unchanged except display strings:
   - `resolve_batch_report_paths()` → `ROOT`, `BATCH_ID`, `BATCH_DISPLAY`
   - Output MD written under `ROOT`
   - `--validate-paths` checks required sidecar CSVs (and T1–T3 review `.md`) under `ROOT`

2. **Nullspace report** adds `configure_nullspace_report_paths()`:
   - Batch display/id from `resolve_batch_report_paths()`
   - Review folder: `paths.root.parent / "nullspace_link_stability_review"` (sibling of batch under `Layer3_JcvPCA/outputs/`)
   - `REVIEW_DISPLAY` via `display_repo_path(review, project_root)`
   - `--validate-paths` uses `run_path_preflight(..., input_root=REVIEW)` so CSV checks target the review folder, not the batch root

3. **Shared CLI** (all four scripts): `--config`, `--batch-dir`, `--validate-paths`, `--dry-run`

### Required input checks (`--validate-paths`)

| Script | Required inputs |
|--------|-----------------|
| DR T1 vs T3 | `DR_T1_T3_REQUIRED` — 3 CSVs + `directional_robustness_t1_t3_review.md` |
| DR T1 vs T2 | `DR_T1_T2_REQUIRED` — CSVs from `INPUTS` only (optional T3 sidecars unchanged) |
| DR T2 vs T3 | `DR_T2_T3_REQUIRED` — CSVs from `INPUTS` only |
| Nullspace | `NULLSPACE_REQUIRED` — 8 review CSVs under `nullspace_link_stability_review/` |

Missing batch or review folder → `FileNotFoundError` with config path in message.

---

## Tests run

| Command | Result |
|---------|--------|
| `python scripts/check_project_paths.py` | **Exit 0** |
| `python3 -m py_compile` on helper + 4 refactored scripts | **Exit 0** |
| `--validate-paths` / `--dry-run` on refactored scripts | **Not run** — system Python lacks Layer 3 deps (`numpy`, `pandas`); safe to run from Layer 3 env when available |

---

## Outputs regenerated

**No.** No full numeric reports were regenerated. Validation was limited to path registry check and syntax compile.

---

## Scientific logic changed

**No.** Path wiring, CLI preflight, and display-path strings only.

---

## Remaining hard-coded paths (Layer 3 report/analysis scripts)

| Category | Examples | Next stage |
|----------|----------|------------|
| `analyze_*` defaults | `analyze_directional_robustness_*.py`, `analyze_nullspace_link_stability.py` | R8+ — analysis path refactor (separate from read-only reports) |
| PC focus chain | `generate_pc_focus_review.py`, `update_pc_focus_interpretation_artifacts.py` | R7.4+ after decoupling or shared helper |
| Movement org report | `generate_movement_organization_question_report.py` | R7.4 — poster package + batch |
| Joint heatmap pipeline | `prepare_joint_heatmap_tables.py` | Out of scope — writer, not read-only |
| Batch runner | `run_gaga_batch_jcvpca.py` | Out of scope — timestamped outputs by design |
| Master/NV templates | Some R7.2 scripts still embed `Layer3_JcvPCA/outputs/{ROOT.name}` in body text | Optional cosmetic follow-up |

---

## Recommended next stage (R7.4)

1. Refactor `generate_movement_organization_question_report.py` with batch + `layer3.poster_evidence_package` from config.
2. Evaluate `generate_pc_focus_review.py` — extract read path config without pulling analysis imports at module level.
3. Defer all `analyze_*` path defaults until a dedicated analysis-path stage (R8).
