# R7 — Pilot Path Refactor

**Date:** 2026-06-30  
**Prerequisite commit:** `b9021e2` — feat: add config-driven project path loader  
**Scope:** Two poster scripts only — no batch runners, no analysis logic changes.

---

## Scripts refactored

| Script | Role | Risk |
|--------|------|------|
| [`scripts/make_poster_final_figures.py`](../../scripts/make_poster_final_figures.py) | Main poster figures A–D + combined panel | Low — reads CSVs, writes figures |
| [`scripts/make_poster_671_figures.py`](../../scripts/make_poster_671_figures.py) | Participant 671 supplementary figures | Low — imports shared path config from above |

**Not refactored (deferred):** Layer 3 batch/report generators (`generate_*`, `analyze_*`, `run_gaga_batch_jcvpca.py`), `generate_poster_ready_evidence_package.py`, Layer 2.5 defaults.

---

## Hard-coded paths removed

### `make_poster_final_figures.py`

| Before | After |
|--------|-------|
| `PROJECT_ROOT / "outputs" / "poster_final_figures"` | `paths.poster_final_figures` via `configure_poster_paths()` |
| `.../poster_ready_evidence_package` in `SEARCH_DIRS[0]` | `paths.poster_evidence_package` |
| `.../gaga_batch_jcvpca_20260626_193319` in `SEARCH_DIRS[1]` | `paths.layer3_canonical_batch` |
| `.../Layer3_JcvPCA/outputs` in `SEARCH_DIRS[2]` | `paths.get("layer3.outputs_root")` |
| Hard-coded fallbacks in module constants | Defaults only until `configure_poster_paths()` runs |

### `make_poster_671_figures.py`

| Before | After |
|--------|-------|
| `PROJECT_ROOT / "Layer3_JcvPCA" / "outputs" / "gaga_batch_jcvpca_20260626_193319"` in `_assess_pp_conversion()` | `CANONICAL_BATCH_DIR` (from shared config) |

---

## How paths are now loaded

1. **`src/project_paths.py`** reads [`config/paths.yaml`](../../config/paths.yaml).
2. **`configure_poster_paths()`** (in `make_poster_final_figures.py`) sets module globals:
   - `PROJECT_ROOT`
   - `OUT_DIR` ← `poster.final_figures`
   - `CANONICAL_BATCH_DIR` ← `layer3.canonical_batch`
   - `SEARCH_DIRS` ← evidence package, batch, L3 outputs root, `outputs/`, project root
3. **Import-time default:** `configure_poster_paths()` runs once at module load (same paths as before on this machine).
4. **`main()`** re-calls `configure_poster_paths()` after parsing CLI overrides.

### CLI overrides (new, optional)

Both poster scripts share `parse_poster_path_args()`:

| Flag | Config key overridden |
|------|------------------------|
| `--config PATH` | Alternate `paths.yaml` |
| `--batch-dir PATH` | `layer3.canonical_batch` |
| `--evidence-dir PATH` | `layer3.poster_evidence_package` |
| `--out-dir PATH` | `poster.final_figures` |

Missing required input dirs raise `FileNotFoundError` with config path in the message.

---

## Tests run

| Command | Result |
|---------|--------|
| `python scripts/check_project_paths.py` | **Exit 0** — all required registry paths exist |
| `python -c` path resolution smoke test | **Pass** — batch/evidence/out match former hard-coded locations |
| `python scripts/make_poster_final_figures.py --help` | **Not run** — system Python lacks `numpy` (poster env needs Layer 3 deps) |
| `python scripts/make_poster_671_figures.py --help` | **Not run** — same dependency constraint |
| Full figure regeneration | **Not run** — poster frozen; would overwrite PNG/PDF/SVG |

---

## Outputs regenerated?

**No.** No poster figures or CSV tables were rewritten.

---

## Behavior changes

| Area | Change |
|------|--------|
| Scientific calculations / plotting | **None** |
| CSV search order | **Unchanged** (evidence → batch → L3 outputs → outputs → root) |
| Default paths on this machine | **Equivalent** to pre-R7 hard-coded values |
| CLI | **Added** optional path overrides (backward compatible) |
| Startup | Fails fast with clear error if evidence package or batch dir missing |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Import-time `configure_poster_paths()` fails on incomplete checkout | Clear error lists missing dirs + config path |
| `make_poster_671` imports full `make_poster_final_figures` module | Acceptable for pilot; split shared path module in R7.1 if needed |
| `--help` still requires numpy/matplotlib import chain | Document; use `check_project_paths.py` for env-free validation |
| Other scripts still hard-code `193319` | R7.1+ per R4 priority list |

---

## Recommended next scripts (R7.1)

Priority order for incremental refactor:

1. **`Layer3_JcvPCA/scripts/generate_poster_evidence_report.py`** — MD template strings only; low compute
2. **`Layer3_JcvPCA/scripts/generate_poster_ready_evidence_package.py`** — writer; medium (runs CSV aggregation but not full JcvPCA)
3. **`scripts/make_poster_*`** — already done in R7
4. **`Layer3_JcvPCA/scripts/run_gaga_batch_jcvpca.py`** — already has good CLI; wire defaults to `paths.yaml` only
5. **Report generators** (`generate_final_integrated_review.py`, directional robustness scripts) — batch read-only, one `BATCH =` constant each

Optional structural follow-up:

- Extract `scripts/poster_paths.py` (shared configure/argparse) to avoid importing matplotlib when 671 script loads path config only.

---

## Files changed (R7)

- `scripts/make_poster_final_figures.py` (modified)
- `scripts/make_poster_671_figures.py` (modified)
- `docs/research_recovery/R7_PILOT_REFACTOR.md` (this file)
- `docs/research_recovery/R7_COMMIT_PLAN.md` (staging plan)

No changes to `src/project_paths.py`, `config/paths.yaml`, or analysis libraries.

---

*No commit in R7. See [`R7_COMMIT_PLAN.md`](R7_COMMIT_PLAN.md).*
