# R6 — Project Path Loader

**Date:** 2026-06-30  
**Prerequisite commit:** `ec458793` — docs: enter research continuation mode  
**Scope:** Small reusable path loader only — no script refactor, no analysis runs.

---

## Files created

| File | Purpose |
|------|---------|
| [`src/project_paths.py`](../../src/project_paths.py) | Load `config/paths.yaml`, resolve paths, validate existence |
| [`src/__init__.py`](../../src/__init__.py) | Marks root `src/` as importable |
| [`scripts/check_project_paths.py`](../../scripts/check_project_paths.py) | CLI validation of canonical paths |
| [`docs/research_recovery/R6_PROJECT_PATH_LOADER.md`](R6_PROJECT_PATH_LOADER.md) | This document |
| [`docs/research_recovery/R6_COMMIT_PLAN.md`](R6_COMMIT_PLAN.md) | Explicit staging plan (not committed yet) |

### Module location choice

There was **no existing root `src/` package** (Layer code lives under `Layer*/src/`). R6 adds a **repository-root `src/`** for cross-layer utilities that should not depend on Layer 2/2.5/3 packages.

---

## How to run the path check

From repository root:

```bash
python scripts/check_project_paths.py
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | All **required** paths exist |
| `1` | One or more **required** paths missing |
| `2` | Reserved for fatal loader errors (config missing, parse failure) |

**Run result (2026-06-30):** exit `0` — all required paths present on this machine.

---

## YAML loading

| Mode | When | Notes |
|------|------|-------|
| **PyYAML** (preferred) | `import yaml` succeeds | Same dependency as `Layer3_JcvPCA/pyproject.toml` |
| **Minimal fallback** | PyYAML not installed | Parses the nested subset used by `config/paths.yaml` only |

System Python on this machine used the **minimal fallback** (Homebrew PEP 668 blocks global `pip install`). Layer 3 venvs with `pyyaml>=6.0` will use PyYAML automatically.

---

## Required paths

These must exist or `check_project_paths.py` exits nonzero:

| Key | Resolved role |
|-----|----------------|
| `raw_data.layer1` | Layer 1 QC raw inputs |
| `raw_data.layer2` | Layer 2 Motive CSV inputs |
| `raw_data.layer2_5_descriptions` | DataDescriptions sidecars |
| `layer2.active_outputs` | Active Layer 2 session output root |
| `layer2_5.pre_jvcpca_review` | Layer 2.5 export windows (Layer 3 input) |
| `layer2_5.segmentation_xlsx` | Manual segmentation annotations |
| `layer2_5.config_manifests` | Layer 2.5 config / manifests |
| `layer3.outputs_root` | Layer 3 outputs directory |
| `layer3.canonical_batch` | Canonical batch `gaga_batch_jcvpca_20260626_193319` |
| `layer3.scripts` | Layer 3 analysis scripts |
| `layer3.src` | Layer 3 library source |

---

## Optional paths (warnings only)

Missing optional paths print warnings but do **not** fail the check:

| Key | Notes |
|-----|-------|
| `raw_data.root_test_exports` | Under manual review (`671_test_data_des/`) |
| `layer2.layer2_exports` | Parquet bundle |
| `layer2.active_session_glob` | Glob — warns if zero `*_Take_*` matches |
| `layer2.stage_indices` | Glob — warns if no index files |
| `layer2.historical_archive_external` | Off-repo Layer 2 archive (R1) |
| `layer2_5.pre_jvcpca_archive_snapshot` | Historical snapshot under `_archive/` |
| `layer3.poster_evidence_package` | Poster CSV inputs |
| `poster.final_figures` | Final poster PDF/PNG/SVG |
| `results.*` | Placeholder research folders |
| `external_archive.*` | Off-repo cleanup + Layer 2 archives |

---

## Missing paths (this run)

**None** — all required and optional registry paths resolved and existed on disk at validation time.

---

## How future scripts should use the loader

### Basic usage

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # adjust depth per script location
sys.path.insert(0, str(ROOT / "src"))

from project_paths import load_project_paths

paths = load_project_paths()
batch_dir = paths.layer3_canonical_batch
batch_id = paths.layer3_canonical_batch_id
l25_root = paths.layer2_5_pre_jvcpca_review

# Fail fast with a clear message:
paths.require_existing("layer3.canonical_batch")
```

### Dot-key access

```python
paths.get("layer3.canonical_batch")
paths.get_str("layer3.canonical_batch_id")
```

### Validation in scripts / CI

```python
result = paths.validate()
if not result.ok:
    for issue in result.errors:
        raise FileNotFoundError(f"{issue.dotted_key}: {issue.resolved}")
```

### What not to do yet

- Do **not** replace all 22 hard-coded `193319` references in one pass (see R4 review).
- Do **not** import Layer 3 modules from `project_paths.py` (keeps loader lightweight).

---

## Recommended next refactor stage (R7)

1. **Pilot refactor (2–3 scripts):** `scripts/make_poster_final_figures.py`, `Layer3_JcvPCA/scripts/run_gaga_batch_jcvpca.py` — replace hard-coded batch paths with `load_project_paths()`.
2. **CLI override:** Add optional `--config` / env `THREELAYERS_PATHS_CONFIG` for alternate batches (new timestamped runs).
3. **R8 symlinks:** Point `results/active/` at canonical batch / poster paths via documented symlinks.
4. **R10 git hygiene:** `git rm --cached` for legacy tracked outputs after path loader is adopted.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Minimal YAML parser drift if `paths.yaml` grows complex | Prefer PyYAML in dev venvs; extend parser only for simple nested keys |
| External archive paths missing on another machine | Marked optional; warnings only |
| `sys.path` insertion in each script | Later: optional root `pyproject.toml` package `project_paths` |

---

## What was not done (by design)

- No broad script refactor
- No analysis runs
- No file moves or deletions
- No git commit (see [`R6_COMMIT_PLAN.md`](R6_COMMIT_PLAN.md))
