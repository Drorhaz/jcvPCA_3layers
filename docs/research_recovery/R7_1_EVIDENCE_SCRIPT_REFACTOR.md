# R7.1 — Evidence Script Path Refactor

**Date:** 2026-06-30  
**Prerequisite commit:** `e3bb1e3` — refactor: load poster script paths from config registry  
**Scope:** Two Layer 3 evidence/report scripts — no batch-analysis runners, no CSV regeneration.

---

## Script location note

Preferred targets were named under `scripts/` in the plan, but the actual files live at:

| Planned name | Actual path |
|--------------|-------------|
| `generate_poster_evidence_report.py` | `Layer3_JcvPCA/scripts/generate_poster_evidence_report.py` |
| `generate_poster_ready_evidence_package.py` | `Layer3_JcvPCA/scripts/generate_poster_ready_evidence_package.py` |

Both were refactored in place.

---

## Scripts refactored

| Script | Role | Risk |
|--------|------|------|
| `Layer3_JcvPCA/scripts/generate_poster_evidence_report.py` | Markdown reports from existing evidence CSVs | Low — read CSVs, write `.md` only when run without `--validate-paths` |
| `Layer3_JcvPCA/scripts/generate_poster_ready_evidence_package.py` | Build evidence CSV package from canonical batch | Medium if run fully — **not executed** in R7.1; path wiring only |

**Not refactored (deferred):** `generate_final_integrated_review.py`, directional-robustness scripts, `run_gaga_batch_jcvpca.py`, Layer 2.5 defaults, core `layer3_jcvpca` library.

---

## Hard-coded paths removed

### `generate_poster_evidence_report.py`

| Before | After |
|--------|-------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` in master index template | `BATCH_DISPLAY` from `layer3.canonical_batch` (repo-relative) |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` in master index | `EVIDENCE_DISPLAY` from `layer3.poster_evidence_package` |
| `gaga_batch_jcvpca_20260626_193319` in report header | `BATCH_ID` from `layer3.canonical_batch_id` |
| Implicit assumption that paths are fixed strings | `configure_evidence_report_paths()` validates batch + evidence dirs exist |

### `generate_poster_ready_evidence_package.py`

| Before | After |
|--------|-------|
| `ROOT = Path(__file__).parents[1]` (Layer 3 subproject only) | `_REPO_ROOT` via `load_project_paths().project_root` for config |
| `BATCH = ROOT / "outputs" / "gaga_batch_jcvpca_20260626_193319"` | `paths.layer3.canonical_batch` |
| `OUT = ROOT / "outputs" / "poster_ready_evidence_package"` | `paths.layer3.poster_evidence_package` |

All `BATCH / ...` read logic unchanged — only the `BATCH` root is config-driven.

---

## How paths are resolved

1. Insert repo `src/` on `sys.path` and import `load_project_paths`.
2. **`configure_evidence_package_paths()`** (package builder):
   - Input: `layer3.canonical_batch` (must exist)
   - Output: `layer3.poster_evidence_package` (created on run; not required at import)
3. **`configure_evidence_report_paths()`** (report generator):
   - Requires existing batch **and** evidence package directories
   - Sets display strings for markdown templates from resolved paths
4. **`generate_reports()`** re-syncs report path globals from `(batch, out)` passed by the package builder.

### CLI flags added

**`generate_poster_evidence_report.py`**

| Flag | Purpose |
|------|---------|
| `--config` | Alternate `paths.yaml` |
| `--batch-dir` | Override canonical batch |
| `--evidence-dir` | Override evidence package (input CSV root) |
| `--validate-paths` | Check paths only; **no markdown regeneration** |

**`generate_poster_ready_evidence_package.py`**

| Flag | Purpose |
|------|---------|
| `--config` | Alternate `paths.yaml` |
| `--batch-dir` | Override canonical batch |
| `--evidence-dir` | Override evidence output directory |
| `--dry-run` | Print planned output paths; **no CSV/MD writes** |

Default behavior without flags matches pre-R7.1 canonical locations on this machine.

---

## Tests run

| Command | Result |
|---------|--------|
| `python scripts/check_project_paths.py` | **Exit 0** |
| `python3 -m py_compile Layer3_JcvPCA/scripts/generate_poster_evidence_report.py` | **Pass** |
| `python3 -m py_compile Layer3_JcvPCA/scripts/generate_poster_ready_evidence_package.py` | **Pass** |
| `generate_poster_evidence_report.py --validate-paths` | **Not run** — system Python lacks `pandas` |
| `generate_poster_ready_evidence_package.py --dry-run` | **Not run** — system Python lacks `numpy` |
| Full evidence package rebuild | **Not run** |
| Markdown report regeneration | **Not run** |

Run `--validate-paths` / `--dry-run` inside the Layer 3 environment (`Layer3_JcvPCA` venv with `numpy`, `pandas`, `scipy`).

---

## Outputs regenerated?

**No.** No CSVs or markdown reports were rewritten.

---

## Scientific logic changed?

**No.** Calculations, filtering, thresholds, aggregations, and report narrative content logic are unchanged. Only path resolution, CLI plumbing, and template path strings were updated.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Import-time `configure_*()` requires batch (and evidence for report module) on disk | Clear `FileNotFoundError` with config path |
| Report module import fails if evidence package missing | Expected; build package first or use `--validate-paths` only when dirs exist |
| Duplicate configure helpers in two scripts | Acceptable for R7.1; optional extract to shared module in R7.2 |
| System Python missing Layer 3 deps | Document; use project venv for runtime tests |

---

## Remaining hard-coded paths (next targets)

| Location | Pattern | Priority |
|----------|---------|----------|
| ~20 Layer 3 `generate_*` / `analyze_*` scripts | `BATCH = .../gaga_batch_jcvpca_20260626_193319` | P0 — R7.2+ |
| `layer3_jcvpca/gaga_batch_runner.py` | `default_layer25_root()` | P0 |
| `layer3_jcvpca/inventory.py` | pre_jvcpca_review default | P0 |
| Root poster scripts | Already refactored (R7) | Done |
| Evidence scripts | Refactored (R7.1) | Done |

---

## Recommended next step (R7.2)

Refactor read-only report generators that only consume batch outputs, e.g.:

- `generate_final_integrated_review.py`
- `generate_master_full_numeric_report.py`

One script at a time; same `--config` / `--batch-dir` pattern.

---

*No commit in R7.1. See [`R7_1_COMMIT_PLAN.md`](R7_1_COMMIT_PLAN.md).*
