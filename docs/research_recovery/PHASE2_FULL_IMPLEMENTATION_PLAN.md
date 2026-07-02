# Phase 2 — Full Workspace Implementation Plan

**Date:** 2026-06-30  
**Status:** Approved for execution — **nothing in this document has run yet**  
**Goal:** Deliver the cleanup the user actually asked for: **one runner surface**, **categorized results**, **archived clutter removed**, **clear data map**, and **optional full path migration** — without breaking the L1→L2→L2.5→L3 pipeline.

**Supersedes / extends:**

- [`FINAL_CLEANUP_PLAN.md`](FINAL_CLEANUP_PLAN.md) — F1/F2 done; F3 + W3c deferred
- [`W2_TARGET_VISIBLE_STRUCTURE.md`](W2_TARGET_VISIBLE_STRUCTURE.md) — hybrid navigation model
- [`W3_WORKSPACE_SIMPLIFICATION_MOVE_PLAN.md`](W3_WORKSPACE_SIMPLIFICATION_MOVE_PLAN.md) — move tables by category

**Already completed (do not repeat):**

| Batch | Commit / state |
|-------|----------------|
| W3a doc clutter | `38c4ea9` |
| F1 pointers + legacy docs | `e0ed01b` |
| F2 external archive (~82 MB scratch) | `e0ed01b` |
| M12a validation | `2c46a9d` |
| M12b smoke batch | log `cf01c60`; outputs on disk only |

---

## 1. End state (what “done” looks like)

### 1.1 Human experience

A new contributor opens the repo and within **60 seconds** knows:

1. **Start:** [`RUN.md`](../../RUN.md) at repo root (single command cheat sheet)
2. **Health:** `python scripts/check_project_paths.py`
3. **Data:** [`docs/DATA_MAP.md`](../DATA_MAP.md) — raw → processed → batches
4. **Results:** browse [`results/`](../../results/) — categorized indexes + symlinks to bulk data
5. **Code:** run via root wrappers in `scripts/run_*.py` (not hunt across four layer trees)

### 1.2 Target root layout (after all phases)

```text
3Layers_project/
├── RUN.md                         ← NEW: single runner (Phase P1)
├── README_WORKING.md              ← daily narrative (links to RUN.md)
├── README.md
├── config/paths.yaml              ← updated in P4/P5 only
├── src/
│   └── project_paths.py           ← extended in P4
├── scripts/
│   ├── check_project_paths.py
│   ├── run_health_check.py        ← alias/wrapper (P1)
│   ├── run_layer1_qc.py           ← wrappers (P4)
│   ├── run_layer2_session.py
│   ├── run_layer2_5_export.py
│   ├── run_layer3_batch.py
│   ├── run_layer3_validate.py
│   └── poster/                    ← moved poster scripts (P4)
├── docs/
│   ├── DATA_MAP.md                ← NEW (P2)
│   └── research_recovery/         ← execution logs per phase
├── data/                          ← NEW symlinks only in P5 (no 54 GB mv)
│   ├── raw_layer1 → Layer1_motive_qc/motive_qc/data
│   ├── raw_layer2 → Layer2_Motive_Kinematics/data
│   ├── raw_layer2_5_descriptions → Layer2.5_Segmentation/data_description
│   └── test_exports → 671_test_data_des
├── processed/                     ← NEW symlinks (P5)
│   ├── layer2_sessions → Layer2_Motive_Kinematics/outputs/*_Take_*
│   ├── layer2_exports → .../layer2_exports
│   └── pre_jvcpca_review → Layer2.5_Segmentation/outputs/pre_jvcpca_review
├── results/                       ← populated + symlinks (P2–P3)
│   ├── README.md
│   ├── active/
│   │   ├── CANONICAL_BATCH.md
│   │   └── canonical_batch → symlink (P3)
│   ├── batches/                   ← optional alias dir (P3)
│   ├── smoke_tests/
│   ├── poster/
│   │   ├── final_figures → symlink (P3)
│   │   └── evidence_package → symlink (P3)
│   ├── reports/
│   │   ├── movement_organization → symlink (P3)
│   │   └── nullspace_link_stability → symlink (P3)
│   └── archive_index/
├── outputs/                       ← legacy path kept until P5 yaml cutover
│   └── poster_final_figures/    ← physical until P3 move OR symlink back-compat
├── Layer1_motive_qc/              ← code + venv (physical; shrink visibility)
├── Layer2_Motive_Kinematics/
├── Layer2.5_Segmentation/
└── Layer3_JcvPCA/
```

**Important:** Full **physical** merge of 54 GB L2 data is **not** Phase 1–4. Phase P5 adds **`data/` and `processed/` as symlink hubs** so navigation is unified while layer runners keep working. Phase P6 (optional) is the only phase that physically moves bulk trees — requires dedicated downtime and full re-validation.

### 1.3 What we explicitly do **not** delete

| Item | Reason |
|------|--------|
| Canonical batch `gaga_batch_jcvpca_20260626_193319/` | Frozen poster-era artifact (~3.6 GB, ~2,596 PNGs inside batch) |
| Canonical batch reports (14 MD + numeric reports) | Scientific record |
| `outputs/poster_final_figures/` deliverables | Poster PDFs/PNGs |
| Raw data trees | Protected capture |
| L2 active `*_Take_*` sessions | Pipeline inputs |
| L2.5 `pre_jvcpca_review/` | JcvPCA export inputs |
| Any script referenced in RUN.md / runbook | Runnable chain |

**Plot policy:** Do not strip plots from the **canonical batch folder**. Optional F3/P2 archives target **scratch**, **smoke batch** (after sign-off), and **regeneratable** L1 QC runs — not frozen batch innards.

---

## 2. Execution overview

```text
DONE ── F1, F2, W3a, M12a, M12b
  │
  ▼
P1 ── Runner surface (RUN.md, root wrappers, git L1 cleanup)
  │
  ▼
P2 ── Results catalog + DATA_MAP + IDE hide rules
  │
  ▼
P3 ── Results symlinks + sidecar yaml keys + smoke archive (F2.5)
  │
  ▼
F3 ── Approved deletions (stubs, duplicates, archived redundancy)
  │
  ▼
P4 ── Script consolidation (root runners, no bulk data moves)
  │
  ▼
P5 ── Unified data/processed symlink hub + paths.yaml v2
  │
  ▼
P6 ── OPTIONAL physical migration (54 GB) — separate approval gate
  │
  ▼
DONE ── Section 9 acceptance criteria
```

Each phase: **plan → execute → validate → log → commit (docs + yaml + wrappers only; never bulk binaries)**.

---

## 3. Global gates (every phase)

### 3.1 Pre-flight

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
python scripts/check_project_paths.py
git status --short
```

### 3.2 Post-flight (minimum)

```bash
python scripts/check_project_paths.py
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319
test -d Layer2.5_Segmentation/outputs/pre_jvcpca_review/671
cd Layer3_JcvPCA/scripts
../.venv/bin/python generate_final_integrated_review.py --validate-paths
../.venv/bin/python run_gaga_batch_jcvpca.py --help
```

### 3.3 Post-flight (after P4+)

```bash
python scripts/run_layer3_validate.py   # new wrapper
python scripts/run_health_check.py      # must exit 0
```

### 3.4 Logging

Create/update for each phase:

| Log file | Contents |
|----------|----------|
| `docs/research_recovery/P1_RUNNER_LOG.md` | Files created, links updated |
| `docs/research_recovery/P2_RESULTS_CATALOG_LOG.md` | Index files, `.cursorignore` |
| `docs/research_recovery/P3_SYMLINK_MIGRATION_LOG.md` | Symlink targets, yaml diffs |
| `docs/research_recovery/F3_DELETION_LOG.md` | Per-path approval + restore command |
| `docs/research_recovery/P4_SCRIPT_CONSOLIDATION_LOG.md` | Wrapper → underlying script map |
| `docs/research_recovery/P5_PATHS_V2_LOG.md` | yaml before/after, symlink table |
| `docs/research_recovery/PHASE2_MOVE_LOG.csv` | Every `mv`/`ln -s`/`rm` (machine-readable) |

### 3.5 Commit policy

- Explicit `git add` paths only — **never** `git add .`
- Do not commit archived binaries moved off-repo
- Commit L1 QC deletions **only** after documenting restore path from external archive
- One commit per phase (or per sub-batch if phase is large)

---

## 4. Phase P1 — Runner surface (Tier A)

**Effort:** ~2 hours  
**Risk:** Low  
**Breaks pipeline:** No

### 4.1 Deliverables

| # | Action | Path |
|---|--------|------|
| P1.1 | Create single runner doc | `RUN.md` (repo root) |
| P1.2 | Link RUN.md from README_WORKING | edit `README_WORKING.md` |
| P1.3 | Link from results index | edit `results/README.md` |
| P1.4 | Add `scripts/run_health_check.py` | thin wrapper → `check_project_paths.py` |
| P1.5 | Resolve L1 git “deleted” noise | commit deletions **or** restore from external archive |
| P1.6 | Fix stale links in `Layer3_JcvPCA/README.md` | point to `docs/legacy/master_plan/` |

### 4.2 `RUN.md` required sections

1. **One-line project purpose**
2. **Environments** — which `.venv` for which layer (table)
3. **Health check** — copy-paste command
4. **Layer 1** — QC entry commands (from `Layer1_motive_qc/`)
5. **Layer 2** — session processing + export
6. **Layer 2.5** — `build_gaga_exports.py` with participant flags
7. **Layer 3** — batch run, validate-only, key report generators
8. **Canonical paths** — batch ID, do-not-overwrite rule
9. **Where results live** — `results/` map (link to DATA_MAP after P2)
10. **External archive** — restore one-liner

Source content: merge [`CONTINUATION_RUNBOOK.md`](CONTINUATION_RUNBOOK.md) sections 1–8 into RUN.md; keep runbook as extended reference.

### 4.3 L1 git cleanup decision tree

| Condition | Action |
|-----------|--------|
| L1 outputs archived in `../gaga_psylo_external_archive/final_cleanup_2026-06-30/layer1_qc_outputs/` | `git add` deletions + note in `P1_RUNNER_LOG.md` |
| User wants files back in repo | `mv` from external archive → original paths; do not commit binaries |

### 4.4 Validation

Path check exit 0; human read of RUN.md — every command copy-pastes without editing paths.

### 4.5 Commit

```text
docs: add RUN.md and root health wrapper (P1)
```

---

## 5. Phase P2 — Results catalog + data map (Tier A + B)

**Effort:** ~3 hours  
**Risk:** Low  
**Breaks pipeline:** No

### 5.1 Populate `results/` indexes (markdown only)

| File | Points to |
|------|-----------|
| `results/active/LAYER25_EXPORTS.md` | `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` |
| `results/reports/CANONICAL_BATCH_REPORTS.md` | Top 14 MD in canonical batch |
| `results/reports/MOVEMENT_ORGANIZATION.md` | `Layer3_JcvPCA/outputs/movement_organization_question_report/` |
| `results/reports/NULLSPACE_LINK_STABILITY.md` | `Layer3_JcvPCA/outputs/nullspace_link_stability_review/` |
| `results/reports/POSTER_EVIDENCE.md` | `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` |
| `results/poster/FIGURE_MANIFEST.md` | List files in `outputs/poster_final_figures/` |
| `results/manuscript/README.md` | Placeholder + links to poster + canonical review |

Update `results/reports/README.md` as table-of-contents for all above.

### 5.2 Create `docs/DATA_MAP.md`

Structured map:

| Stage | Physical path | Size (approx.) | yaml key | Regeneratable? |
|-------|---------------|----------------|----------|----------------|
| L1 raw | `Layer1_motive_qc/motive_qc/data/` | — | `raw_data.layer1` | No |
| L2 raw | `Layer2_Motive_Kinematics/data/` | ~21 GB | `raw_data.layer2` | Partial |
| L2 sessions | `Layer2_Motive_Kinematics/outputs/*_Take_*` | ~32 GB | `layer2.active_session_glob` | Yes |
| L2.5 exports | `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | ~1.2 GB | `layer2_5.pre_jvcpca_review` | Yes |
| Canonical batch | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | ~3.6 GB | `layer3.canonical_batch` | Yes (new timestamp) |
| Smoke batch | `.../gaga_batch_jcvpca_smoke_671_20260630_214341/` | ~370 MB | *(add in P3)* | Yes |
| Poster figures | `outputs/poster_final_figures/` | ~13 MB | `poster.final_figures` | Yes |

Include Mermaid flow: Raw → L2 sessions → L2.5 parquet → L3 batch → reports/poster.

### 5.3 IDE / clutter hiding

Create or extend `.cursorignore` at repo root:

```gitignore
**/.venv/
**/__pycache__/
**/.pytest_cache/
**/.ruff_cache/
Layer2_Motive_Kinematics/outputs/*_Take_*/
Layer3_JcvPCA/outputs/gaga_batch_jcvpca_*/plots/
Layer3_JcvPCA/outputs/gaga_batch_jcvpca_*/**/plots/
```

Do **not** hide canonical batch reports or `results/`.

### 5.4 Untracked doc commits (if still pending)

- `docs/research_recovery/M12_PRE_ANALYSIS_READINESS.md`
- L2 `stage*_index.*` navigation files (if user wants them in git)

### 5.5 Validation

All new markdown links resolve; path check exit 0.

### 5.6 Commit

```text
docs: catalog results indexes and DATA_MAP (P2)
```

---

## 6. Phase P3 — Results symlinks + yaml sidecars (Tier B + W3c partial)

**Effort:** ~4 hours  
**Risk:** Medium  
**Breaks pipeline:** Only if yaml/script defaults updated incorrectly

### 6.1 Strategy

Use **symlinks** from `results/` → existing physical paths first. Update `config/paths.yaml` to prefer `results/` paths for **human-facing keys** while keeping **legacy keys** as aliases until P5.

### 6.2 Symlink table

Execute from repo root (`ln -sfn` relative targets):

| Symlink | Target |
|---------|--------|
| `results/active/canonical_batch` | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319` |
| `results/smoke_tests/smoke_batch_671` | `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341` |
| `results/poster/final_figures` | `outputs/poster_final_figures` |
| `results/poster/evidence_package` | `Layer3_JcvPCA/outputs/poster_ready_evidence_package` |
| `results/reports/movement_organization` | `Layer3_JcvPCA/outputs/movement_organization_question_report` |
| `results/reports/nullspace_link_stability` | `Layer3_JcvPCA/outputs/nullspace_link_stability_review` |

**Alternative (lower risk):** keep physical files in place; only add symlinks without moving. Defer physical `mv` of poster figures until scripts confirmed updated.

### 6.3 `config/paths.yaml` additions (P3)

Add under `results:` and `layer3:`:

```yaml
layer3:
  smoke_batch: "Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341"
  movement_organization_report: "Layer3_JcvPCA/outputs/movement_organization_question_report"
  nullspace_link_stability_report: "Layer3_JcvPCA/outputs/nullspace_link_stability_review"

results:
  canonical_batch_symlink: "results/active/canonical_batch"
  smoke_batch_symlink: "results/smoke_tests/smoke_batch_671"
  poster_figures_symlink: "results/poster/final_figures"
```

Extend `_PATH_REGISTRY` in `src/project_paths.py` for new keys (optional requirement level).

### 6.4 Script updates (minimal)

| Script | Change |
|--------|--------|
| `scripts/make_poster_final_figures.py` | Load output dir from `project_paths.poster_final_figures` (already should) |
| `Layer3_JcvPCA/scripts/generate_movement_organization_question_report.py` | Default output via yaml key if hardcoded |
| `Layer3_JcvPCA/scripts/generate_poster_ready_evidence_package.py` | Same |
| `scripts/check_project_paths.py` | Verify symlinks resolve |

Grep before editing:

```bash
rg -l "poster_final_figures|poster_ready_evidence|movement_organization|nullspace_link" --glob "*.py"
```

### 6.5 F2.5 — Smoke batch external archive (optional sub-batch)

**Approval required.** After M12b reference period:

| Source | Destination |
|--------|-------------|
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` | `../gaga_psylo_external_archive/final_cleanup_2026-06-30/smoke_batch_671_20260630/` |

Leave pointer: update `results/smoke_tests/SMOKE_BATCH_671.md` + broken symlink → external path note.

Regenerate command documented in log:

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python run_gaga_batch_jcvpca.py --participants 671 --output-dir ../outputs/gaga_batch_jcvpca_smoke_671_<NEW_TS>
```

### 6.6 Validation

- Path check exit 0
- Symlinks: `readlink results/active/canonical_batch` → canonical batch
- L3 `--validate-paths` exit 0
- Poster script `--help` or dry-run if available

### 6.7 Commit

```text
chore: add results symlinks and extend path registry (P3)
```

---

## 7. Phase F3 — Approved deletions

**Effort:** ~1 hour  
**Risk:** Low–medium (per item)  
**Breaks pipeline:** No if limited to stubs

### 7.1 Approved deletion candidates

| ID | Path | Precondition | Restore |
|----|------|--------------|---------|
| F3.1 | `Layer3_JcvPCA/outputs/layer3_jcvpca/` | Empty stub (4 KB) | N/A |
| F3.2 | `Layer2.5_Segmentation/outputs/pre_jvpca_review/` | Confirm typo duplicate vs `pre_jvcpca_review` | From backup if non-empty |
| F3.3 | Redundant L1 QC run folders | Only if copy exists in external archive | `final_cleanup_2026-06-30/layer1_qc_outputs/` |
| F3.4 | `__pycache__`, `.pytest_cache` under layers | Safe | Regenerated |

**Never F3:** canonical batch, smoke batch (until archived in P3.5), sidecar reports, poster figures, raw data, L2 sessions.

### 7.2 Process

1. Record approval in `F3_DELETION_LOG.md` (path, date, approver, restore command)
2. Delete one path at a time
3. Run validation gate
4. Commit log only:

```text
docs: record F3 approved deletions
```

---

## 8. Phase P4 — Script consolidation (Tier C lite)

**Effort:** ~1 day  
**Risk:** Medium  
**Breaks pipeline:** If wrapper invokes wrong venv or cwd

### 8.1 Principle

**Do not move layer `src/` packages yet.** Add root **wrappers** that:

1. `cd` to correct layer or set `PYTHONPATH`
2. Invoke the correct `.venv/bin/python`
3. Forward CLI args unchanged

### 8.2 Wrapper map

| Root wrapper | Invokes | venv |
|--------------|---------|------|
| `scripts/run_health_check.py` | `check_project_paths.py` | system or none |
| `scripts/run_layer1_qc.py` | `Layer1_motive_qc/motive_batch_qc.py` or documented entry | L1 `.venv` |
| `scripts/run_layer2_session.py` | L2 stage runner (document primary script in RUN.md) | L2 `.venv` |
| `scripts/run_layer2_5_export.py` | `Layer2.5_Segmentation/scripts/build_gaga_exports.py` | L2.5 `.venv` |
| `scripts/run_layer3_batch.py` | `run_gaga_batch_jcvpca.py` | L3 `.venv` |
| `scripts/run_layer3_validate.py` | `generate_final_integrated_review.py --validate-paths` + dry-runs | L3 `.venv` |
| `scripts/poster/make_poster_final_figures.py` | move from `scripts/make_poster_*.py` | system + L3 for data |

Implementation pattern:

```python
#!/usr/bin/env python3
"""Run Layer 3 batch with repo-root cwd and Layer3 venv."""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
venv_py = ROOT / "Layer3_JcvPCA" / ".venv" / "bin" / "python"
script = ROOT / "Layer3_JcvPCA" / "scripts" / "run_gaga_batch_jcvpca.py"
sys.exit(subprocess.call([str(venv_py), str(script), *sys.argv[1:]], cwd=ROOT))
```

### 8.3 `RUN.md` update

Replace deep paths with `python scripts/run_layer3_batch.py ...` as primary interface. Keep layer paths in “advanced / debugging” subsection.

### 8.4 Optional: `scripts/README.md`

Table: wrapper → underlying script → when to use.

### 8.5 Validation

Each wrapper `--help` or validate-only mode exit 0.

### 8.6 Commit

```text
feat: add root script runners for all layers (P4)
```

---

## 9. Phase P5 — Unified `data/` + `processed/` hub (Tier C)

**Effort:** ~4 hours (+ yaml testing)  
**Risk:** Medium  
**Breaks pipeline:** No if old paths remain as symlinks **to** new hub OR hub symlinks **from** old paths (choose one direction)

### 9.1 Recommended approach: hub symlinks **to** existing layer paths

Avoid moving 54 GB. Create:

```bash
mkdir -p data processed
ln -sfn ../Layer1_motive_qc/motive_qc/data data/raw_layer1
ln -sfn ../Layer2_Motive_Kinematics/data data/raw_layer2
ln -sfn ../Layer2.5_Segmentation/data_description data/raw_layer2_5_descriptions
ln -sfn ../671_test_data_des data/test_exports
ln -sfn ../Layer2_Motive_Kinematics/outputs processed/layer2_outputs_root
ln -sfn ../Layer2.5_Segmentation/outputs/pre_jvcpca_review processed/pre_jvcpca_review
```

Document in `docs/DATA_MAP.md` “navigation hub” section.

### 9.2 `config/paths.yaml` v2 (additive)

Add top-level keys (keep legacy keys pointing to same targets):

```yaml
data:
  raw_layer1: "data/raw_layer1"
  raw_layer2: "data/raw_layer2"
  raw_layer2_5_descriptions: "data/raw_layer2_5_descriptions"
  test_exports: "data/test_exports"

processed:
  layer2_outputs_root: "processed/layer2_outputs_root"
  pre_jvcpca_review: "processed/pre_jvcpca_review"
```

Mark `raw_data.*` and `layer2_5.pre_jvcpca_review` as **deprecated aliases** in yaml comments; update `project_paths.py` with new convenience properties.

### 9.3 Layer README headers

Add one line at top of each `Layer*/README.md`:

> **Navigation:** prefer [`docs/DATA_MAP.md`](../docs/DATA_MAP.md) and [`RUN.md`](../RUN.md). This folder remains the runnable code location.

### 9.4 Validation

Path check validates both legacy and v2 keys resolve to existing data.

### 9.5 Commit

```text
chore: add data/processed navigation hubs and paths.yaml v2 (P5)
```

---

## 10. Phase P6 — OPTIONAL physical bulk migration

**Effort:** Multi-day  
**Risk:** **High**  
**Approval:** Separate written sign-off — **do not start without it**

### 10.1 Scope (only if user explicitly wants layer folders gone)

Physical moves:

| From | To |
|------|-----|
| `Layer2_Motive_Kinematics/data/` | `data/raw_layer2/` (real dir) |
| `Layer2_Motive_Kinematics/outputs/` | `processed/layer2/` |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | `processed/pre_jvcpca_review/` |
| `outputs/poster_final_figures/` | `results/poster/final_figures/` (real dir) |

Leave **compatibility symlinks** at old paths until all scripts migrated.

### 10.2 Code migration checklist

- [ ] Update every hardcoded path in Layer 2/2.5/3 Python (grep `Layer2_Motive`, `pre_jvcpca`, `outputs/`)
- [ ] Update Layer 2 configs under `Layer2_Motive_Kinematics/configs/`
- [ ] Update L2.5 manifests under `Layer2.5_Segmentation/config/`
- [ ] Update dashboard paths in `Layer2.5_Segmentation/dashboard/`
- [ ] Re-run full M12a validation suite
- [ ] Re-run M12b-equivalent smoke batch to new output path
- [ ] Update external archive docs

### 10.3 Rollback

Keep `PHASE2_MOVE_LOG.csv` with inverse `mv` commands. Do not delete source until smoke pass on new paths.

---

## 11. Source code merge (explicitly deferred past P6)

**User asked to merge `src/`** — full merge means:

```
src/
├── project_paths.py
├── layer1/          # from Layer1_motive_qc/motive_qc/motive_qc/
├── layer2/          # from Layer2_Motive_Kinematics/src/layer2_motive/
├── layer2_5/        # from Layer2.5_Segmentation/src/
└── layer3/          # from Layer3_JcvPCA/src/layer3_jcvpca/
```

**Why deferred:** Each layer is an installable package with its own `pyproject.toml` / `.venv`. Merging requires:

1. Unified `pyproject.toml` at root **or** monorepo with editable installs
2. Import path changes across tests and dashboards
3. Single venv strategy (currently 4 venvs)

**Recommendation:** P4 wrappers give 80% of “one runner” benefit. Schedule **P7 monorepo** only after P6 stable.

---

## 12. Plot and output cleanup policy

| Output class | Action | Phase |
|--------------|--------|-------|
| `_workbench_*` | Already archived F2 | Done |
| `671_g4_validation_001/` | Already archived F2 | Done |
| L1 QC `outputs/runs/*` | Archived F2; F3 delete redundant copies | F3 |
| Smoke batch plots (~74 PNG) | Archive with smoke folder | P3.5 |
| Canonical batch plots (~2,596 PNG) | **Keep** inside frozen batch | — |
| Sidecar reports (MD/CSV) | Index + symlink under `results/reports/` | P2–P3 |
| Untracked L3 figures (`docs/figures/`) | Commit to git OR document as local-only | P2 optional |
| Regeneratable batch outputs | Document regen in DATA_MAP; no delete | — |

---

## 13. Updated acceptance criteria (project “clean”)

| # | Criterion | Phase |
|---|-----------|-------|
| 1 | `RUN.md` exists; README_WORKING points to it | P1 |
| 2 | `python scripts/run_health_check.py` exit 0 | P1 |
| 3 | `docs/DATA_MAP.md` complete with sizes + yaml keys | P2 |
| 4 | `results/reports/` has per-artifact index files | P2 |
| 5 | `.cursorignore` hides session/plot bulk from IDE | P2 |
| 6 | Symlinks under `results/` resolve to canonical batch + poster | P3 |
| 7 | `paths.yaml` documents smoke batch + sidecar reports | P3 |
| 8 | F3 stubs removed; deletion log complete | F3 |
| 9 | Root wrappers exist for L1–L3 + validate | P4 |
| 10 | `data/` + `processed/` hubs exist | P5 |
| 11 | Path check + L3 validators pass | All |
| 12 | No `_workbench_*` under L3 outputs | Done (F2) |
| 13 | Git status: no unexplained deleted L1 files | P1 |
| 14 | `PHASE2_MOVE_LOG.csv` complete | All |

**Optional (P6):** legacy layer data paths are symlinks only; bulk lives under `data/` and `processed/`.

---

## 14. Recommended execution schedule

| Day | Phase | Owner action |
|-----|-------|--------------|
| 1 | P1 + P2 | Review RUN.md wording |
| 2 | P3 | Approve symlink table |
| 2 | F3 | Approve each deletion ID |
| 3 | P4 | Test one wrapper per layer |
| 4 | P5 | Review paths.yaml v2 |
| — | P6 | **Separate project** — only if physical merge required |

Parallel safe: **M12c** (252 QC read-only) during P1–P2.

---

## 15. Risk matrix

| Phase | Risk | Mitigation |
|-------|------|------------|
| P1 | Low | Docs only |
| P2 | Low | Docs + cursorignore |
| P3 | Medium | Symlinks before physical mv; validate scripts |
| F3 | Medium | One path at a time; archive first |
| P4 | Medium | Wrappers don’t move code; test `--help` |
| P5 | Medium | Hub symlinks only; legacy keys retained |
| P6 | **High** | Separate gate; compatibility symlinks; full M12 rerun |

---

## 16. Quick start for executor

**Next command when approved:**

```bash
# Start Phase P1
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
python scripts/check_project_paths.py
# Then create RUN.md per Section 4.2
```

**User approval checklist before execution:**

- [ ] Approve P1–P5 sequential execution
- [ ] Approve F3 deletion IDs (F3.1–F3.4)
- [ ] Approve P3.5 smoke batch archive (yes/no)
- [ ] Decline or approve P6 physical migration
- [ ] Decline or approve P7 monorepo src merge

---

## Related docs

| Doc | Role |
|-----|------|
| [`FINAL_CLEANUP_PLAN.md`](FINAL_CLEANUP_PLAN.md) | F1/F2/F3 original batches |
| [`CONTINUATION_RUNBOOK.md`](CONTINUATION_RUNBOOK.md) | Source for RUN.md commands |
| [`README_WORKING.md`](../../README_WORKING.md) | Daily narrative |
| [`config/paths.yaml`](../../config/paths.yaml) | Path registry |
| [`results/README.md`](../../results/README.md) | Results index |

---

*Implementation plan — execute phases in order after user approval checklist (Section 16).*
