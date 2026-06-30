# Master Research Continuation Plan

**Date:** 2026-06-30  
**Mode:** Research continuation (poster complete)  
**Purpose:** Single roadmap from current messy working tree to a stable, config-driven research project.  
**Status:** Active — execute batches **M1–M12** one at a time with explicit approval.

---

## Documentation index

| Document | Purpose |
|----------|---------|
| [R1_LAYER2_ARCHIVE_EXTERNAL_MOVE.md](R1_LAYER2_ARCHIVE_EXTERNAL_MOVE.md) | Layer 2 archive moved off-repo |
| [R2_TARGET_WORKING_STRUCTURE.md](R2_TARGET_WORKING_STRUCTURE.md) | Target folder layout |
| [R3_CANONICAL_PATHS.md](R3_CANONICAL_PATHS.md) | Path roles |
| [R4_HARDCODED_PATHS_REVIEW.md](R4_HARDCODED_PATHS_REVIEW.md) | Config migration map |
| [R5_RESEARCH_CONTINUATION_STATUS.md](R5_RESEARCH_CONTINUATION_STATUS.md) | Continuation status snapshot |
| [R6_PROJECT_PATH_LOADER.md](R6_PROJECT_PATH_LOADER.md) | Path loader design |
| [R7_PILOT_REFACTOR.md](R7_PILOT_REFACTOR.md) | Poster path refactor |
| [R7_1_EVIDENCE_SCRIPT_REFACTOR.md](R7_1_EVIDENCE_SCRIPT_REFACTOR.md) | Evidence scripts |
| [R7_2_READONLY_REPORT_REFACTOR.md](R7_2_READONLY_REPORT_REFACTOR.md) | Read-only batch reports |
| [R7_3_SAFE_REPORT_REFACTOR.md](R7_3_SAFE_REPORT_REFACTOR.md) | DR + nullspace reports |
| [../../config/paths.yaml](../../config/paths.yaml) | Machine-readable path registry |
| [../cleanup_stage_B/](../cleanup_stage_B/) | Stage B cleanup docs |
| [../cleanup_stage_C/STAGE_C0_LAYER2_ARCHIVE_REVIEW.md](../cleanup_stage_C/STAGE_C0_LAYER2_ARCHIVE_REVIEW.md) | Stage C archive review |
| [../cleanup_stage_C/STAGE_C0_LAYER2_ARCHIVE_MOVE_PLAN.md](../cleanup_stage_C/STAGE_C0_LAYER2_ARCHIVE_MOVE_PLAN.md) | Stage C move plan (reference) |

---

## 1. Current project state

### Branch and recent recovery commits

| Item | Value |
|------|-------|
| **Branch** | `main` |
| **HEAD (at M1 authoring)** | `69c797e` — refactor: load directional robustness and nullspace report paths from config |

**Recovery commit chain (newest first):**

| Hash | Message |
|------|---------|
| `69c797e` | refactor: load directional robustness and nullspace report paths from config (R7.3) |
| `fbc8e75` | refactor: load read-only Layer 3 report paths from config (R7.2) |
| `0e85781` | refactor: load evidence script paths from config registry (R7.1) |
| `e3bb1e3` | refactor: load poster script paths from config registry (R7.0) |
| `b9021e2` | feat: add config-driven project path loader (R6) |
| `ec45879` | docs: enter research continuation mode (R5) |
| `12e74cc` | docs: record external archive move |
| `393fb68` | chore: checkpoint project cleanup through stage B |

**Prior milestones:** Stage A–B cleanup, top-level archive moved to `../gaga_psylo_external_archive/`, Layer 2 archive moved off-repo (R1).

### Git status summary (live snapshot at M1 authoring)

| Category | Count | Notes |
|----------|-------|-------|
| **Total dirty entries** | **495** | Working tree not clean |
| Modified tracked (`M`) | **45** | Layer 2.5 source/UI, tracked outputs, L2 stage indices, minor L3 edits |
| Deleted tracked (`D`) | **389** | All under `Layer2_Motive_Kinematics/outputs/archive/` — moved in R1, still in Git index |
| Untracked (`??`) | **61** | L3 automation, L2.5 additions, cleanup docs, 252 raw sample |

**Tracked output file counts (still in index):**

| Tree | Tracked paths |
|------|---------------|
| `Layer2_Motive_Kinematics/outputs/**` | 775 |
| `Layer2.5_Segmentation/outputs/**` | 15 |
| `Layer3_JcvPCA/outputs/**` | 2 |
| `Layer3_JcvPCA/scripts/*.py` (committed) | 11 |

### Major remaining modified tracked files

**Layer 2.5 source / UI (future code commit — M7):**

- `Layer2.5_Segmentation/src/pre_jvcpca_review/` — 7 modules
- `Layer2.5_Segmentation/dashboard/` — 3 files
- `Layer2.5_Segmentation/notebooks/` — 2 notebooks
- `Layer2.5_Segmentation/tests/` — 5 test files

**Layer 2.5 tracked outputs (generated — untrack in M4, do not edit):**

- `Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/` — manifest/validation files
- `Layer2.5_Segmentation/outputs/session_index.csv`

**Layer 2 active indices (generated — untrack in M3):**

- 14× `Layer2_Motive_Kinematics/outputs/stage*_index.{csv,md}`

**Layer 3 minor tracked edits:**

- `Layer3_JcvPCA/README.md`, `Layer3_JcvPCA/src/layer3_jcvpca/viz.py`, PDF reference

**Git index noise (not on disk):**

- 389× `D Layer2_Motive_Kinematics/outputs/archive/**` — archive at `../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/`

### Major remaining untracked files

| Group | Examples | Role |
|-------|----------|------|
| Layer 3 automation | `run_gaga_batch_jcvpca.py`, `gaga_batch_runner.py`, 7× `analyze_*.py`, 14× `src/layer3_jcvpca/*.py`, 9× tests | Full batch pipeline not in Git (M8) |
| Layer 2.5 automation | `build_gaga_exports.py`, `gaga_batch_export.py`, manifests, 252 data_description CSVs | Export path for 252 (M7) |
| Layer 3 outputs (gitignored) | `nullspace_link_stability_review/`, `poster_ready_evidence_package/` | On disk, ignored |
| Docs | cleanup stage C, Layer3 planning docs | Documentation |
| Raw data | `Layer2_Motive_Kinematics/data/252/` | Classify before any commit |

### Ignored vs tracked generated outputs

| Location | Tracked | Gitignored | Action |
|----------|---------|------------|--------|
| L2 `outputs/archive/` | 389 deleted in index | yes | M2 — `git rm --cached` |
| L2 `outputs/*_Take_*/` | ~775 tracked | yes (B.6) | M3 — untrack |
| L2.5 `pre_jvcpca_review/` | 15 tracked | yes | M4 — untrack |
| L3 `gaga_batch_jcvpca_*/` | 2 tracked | yes | M3/M4 follow-up if needed |
| Poster / evidence | curated CSV/MD may be trackable | batch dirs ignored | Do not delete |

### Raw data and external archives

| Asset | Status |
|-------|--------|
| L1 raw | **Safe** — present; CSV gitignored |
| L2 raw (671) | **Safe** — in repo; gitignored |
| L2 raw (252) | **Untracked** — verify before staging |
| External archive | **Safe** — `../gaga_psylo_external_archive/` (~24 GB off-repo) |
| Canonical batch `193319` | **Safe** — on disk; gitignored; in `config/paths.yaml` |
| Path registry | **Safe** — `config/paths.yaml` + `src/project_paths.py` committed |

### Path refactor progress (R6–R7.3)

**Config-driven (committed):**

- Poster scripts (`scripts/make_poster_*.py`)
- Evidence scripts (`generate_poster_evidence_report.py`, `generate_poster_ready_evidence_package.py`)
- Read-only reports: integrated, master, NV, directional robustness ×3, nullspace
- Helper: `Layer3_JcvPCA/scripts/layer3_batch_report_paths.py`

**Still hard-code `gaga_batch_jcvpca_20260626_193319` (mostly untracked):**

- `generate_movement_organization_question_report.py`, `generate_pc_focus_review.py`
- `prepare_joint_heatmap_tables.py`, `update_pc_focus_interpretation_artifacts.py`
- `analyze_*` (×6), `run_pc_focus_p50_p60_sensitivity.py`
- Module-level fallbacks in committed evidence scripts (runtime override exists)

**Good patterns already:**

- `run_gaga_batch_jcvpca.py` — timestamped output dir; `--layer25-root` CLI
- `gaga_batch_runner.py` — `default_layer25_root()` hard-codes L2.5 path (wire in M10)

---

## 2. Remaining work categories (A–G)

| Cat | Name | Scope | Examples |
|-----|------|-------|----------|
| **A** | Safe documentation commits | Plans, status, cleanup logs | Master plan, stage C docs, runbook |
| **B** | Safe path-refactor commits | Read-only reports; path wiring only | M5 movement org report; M6 evidence defaults |
| **C** | Git cleanup / untracking | Index-only; no disk deletion | M2 archive; M3 L2 sessions; M4 L2.5 exports |
| **D** | Project structure stabilization | Commit source; `results/` layout | M7 L2.5 code; M8 L3 code; M11 results |
| **E** | Analysis pipeline refactor | Config defaults for runners/analyzers | M10 `gaga_batch_runner`, `analyze_*` |
| **F** | Next-analysis readiness | Exact continuation commands | M9 runbook for 671/252/L2.5/L3 |
| **G** | Deferred / risky | Moves, deletes, recomputation | M12 new analysis; raw data moves |

**Boundaries:**

- Categories A–B: no scientific logic changes, no analysis runs.
- Category C: `git rm --cached` only; never delete on-disk outputs without separate approval.
- Category G: always gated; never auto-run.

---

## 3. Execution batches (M1–M12)

Each batch below lists goal, likely files, risk, validation, commit message, and approval required.

### Batch execution protocol

**Every executed batch must end with a short batch summary** (append to batch-specific doc or report in chat):

| Field | Required content |
|-------|------------------|
| Files changed | List of paths edited on disk |
| Files staged | Exact paths passed to `git add` |
| Commit hash | If committed; otherwise "not committed" |
| Validation commands run | e.g. `check_project_paths.py`, `py_compile`, `git diff --cached` |
| Analysis run? | Yes/No |
| Raw/generated data touched? | Yes/No — specify which |
| Next recommended batch | Single batch ID |

Never use `git add .`. Never combine unrelated batches in one commit without approval.

---

### M1 — Master plan + doc hygiene

| Field | Value |
|-------|-------|
| **Goal** | Land master plan; commit documentation-only recovery/cleanup files |
| **Files** | `MASTER_CONTINUATION_PLAN.md`, stage C docs, `STAGE_B8_1_DOC_COMMIT_SUMMARY.md` |
| **Risk** | Low |
| **Scientific logic** | No |
| **Runs analysis** | No |
| **Moves/deletes** | No |
| **Validation** | `git diff --cached --name-only` — docs under `docs/` only |
| **Commit message** | `docs: add master research continuation plan` |
| **Approval** | User approved master plan direction |

**Status:** Executing as first batch.

---

### M2 — Git index: Layer 2 archive (389 deletions)

| Field | Value |
|-------|-------|
| **Goal** | Remove stale index entries for archive moved in R1 |
| **Files** | `git rm --cached -r Layer2_Motive_Kinematics/outputs/archive/` |
| **Risk** | Medium |
| **Scientific logic** | No |
| **Runs analysis** | No |
| **Moves/deletes** | Index only — verify external archive first |
| **Validation** | `test -d ../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30`; zero archive `D` in status |
| **Commit message** | `chore: stop tracking Layer 2 archive moved to external storage` |
| **Approval** | **Required** — confirm R1 external archive intact |

---

### M3 — Git index: untrack Layer 2 session outputs

| Field | Value |
|-------|-------|
| **Goal** | Align Git with `.gitignore` for ~775 tracked L2 output paths |
| **Files** | `git rm --cached` on `outputs/*_Take_*/`, `layer2_exports/`, stage indices as needed |
| **Risk** | Medium |
| **Scientific logic** | No |
| **Runs analysis** | No |
| **Moves/deletes** | Index only |
| **Validation** | `git check-ignore -v` samples; `python scripts/check_project_paths.py` |
| **Commit message** | `chore: untrack generated Layer 2 session outputs` |
| **Approval** | **Required** |

---

### M4 — Git index: untrack Layer 2.5 exports

| Field | Value |
|-------|-------|
| **Goal** | Stop tracking 15 L2.5 export paths showing as modified |
| **Files** | `git rm --cached` on ignored `pre_jvcpca_review/` paths |
| **Risk** | Medium |
| **Scientific logic** | No |
| **Runs analysis** | No |
| **Moves/deletes** | Index only |
| **Validation** | Exports readable on disk; L3 runner can find windows |
| **Commit message** | `chore: untrack Layer 2.5 pre-JcvPCA export outputs` |
| **Approval** | **Required** |

---

### M5 — Path refactor: movement organization report (R7.4)

| Field | Value |
|-------|-------|
| **Goal** | Config paths for `generate_movement_organization_question_report.py` |
| **Files** | Report script + optional helper extension |
| **Risk** | Low |
| **Scientific logic** | No — path wiring only |
| **Runs analysis** | No — `--validate-paths` / `--dry-run` only |
| **Moves/deletes** | No |
| **Validation** | `py_compile`, `check_project_paths.py` |
| **Commit message** | `refactor: load movement organization report paths from config` |
| **Approval** | Standard |

---

### M6 — Path refactor: evidence script defaults (R7.5)

| Field | Value |
|-------|-------|
| **Goal** | Remove hard-coded batch module defaults in evidence scripts |
| **Files** | `generate_poster_evidence_report.py`, `generate_poster_ready_evidence_package.py` |
| **Risk** | Low |
| **Scientific logic** | No |
| **Runs analysis** | No |
| **Validation** | `--validate-paths`; no package regeneration |
| **Commit message** | `refactor: remove hard-coded batch defaults from evidence scripts` |
| **Approval** | Standard |

---

### M7 — Commit Layer 2.5 source + tests

| Field | Value |
|-------|-------|
| **Goal** | Version-control L2.5 automation feeding Layer 3 |
| **Files** | `src/pre_jvcpca_review/**`, dashboard, notebooks, tests, manifests — **exclude** `outputs/` and unreviewed raw 252 data |
| **Risk** | Medium |
| **Scientific logic** | Review diff — export logic may change behavior |
| **Runs analysis** | No — unit tests only if lightweight |
| **Moves/deletes** | No |
| **Validation** | `pytest Layer2.5_Segmentation/tests/ -q` (if env available) |
| **Commit message** | `feat: commit Layer 2.5 pre-JcvPCA export and dashboard updates` |
| **Approval** | **Required** — explicit file list |

---

### M8 — Commit Layer 3 automation source

| Field | Value |
|-------|-------|
| **Goal** | Add untracked L3 `src/`, scripts, tests to Git |
| **Files** | ~40 files: runner, analyzers, workbench, tests |
| **Risk** | Medium |
| **Scientific logic** | Code only — no re-run |
| **Runs analysis** | No |
| **Moves/deletes** | No |
| **Validation** | `py_compile`; optional `pytest Layer3_JcvPCA/tests/ -q` |
| **Commit message** | `feat: add Layer 3 JcvPCA batch runner and analysis scripts` |
| **Approval** | **Required** — may split D2a/D2b |

---

### M9 — Continuation runbook

| Field | Value |
|-------|-------|
| **Goal** | Document exact commands for continuing research |
| **Files** | `docs/research_recovery/CONTINUATION_RUNBOOK.md`; update R5 |
| **Risk** | Low |
| **Scientific logic** | No |
| **Runs analysis** | No |
| **Moves/deletes** | No |
| **Validation** | User reviews commands |
| **Commit message** | `docs: add research continuation runbook` |
| **Approval** | User reviews accuracy |

---

### M10 — Analysis pipeline path refactor

| Field | Value |
|-------|-------|
| **Goal** | Config defaults for batch runner and `analyze_*` |
| **Files** | `gaga_batch_runner.py`, `inventory.py`, `run_gaga_batch_jcvpca.py`, analyzers, writer scripts |
| **Risk** | Medium |
| **Scientific logic** | No if path-only — stop on calculation changes |
| **Runs analysis** | No — import/`--help` only |
| **Moves/deletes** | No |
| **Validation** | `check_project_paths.py` |
| **Commit message** | `refactor: load Layer 3 analysis script paths from config` |
| **Approval** | **Required** — after M8 |

---

### M11 — Results layout (optional)

| Field | Value |
|-------|-------|
| **Goal** | Wire `results/` placeholders to canonical paths |
| **Files** | `results/**`, optional `archive_index/external_archives.yaml` |
| **Risk** | Low–medium |
| **Scientific logic** | No |
| **Runs analysis** | No |
| **Moves/deletes** | No (symlinks optional) |
| **Commit message** | `docs: wire results/ placeholders to canonical paths` |
| **Approval** | User chooses symlink vs docs-only |

---

### M12 — New analysis execution (G-gated)

| Field | Value |
|-------|-------|
| **Goal** | Run new L2 / L2.5 / L3 work (e.g. 252 cohort, new batch folder) |
| **Risk** | **High** |
| **Scientific logic** | **Yes** |
| **Runs analysis** | **Yes** |
| **Moves/deletes** | Possibly |
| **Approval** | **Explicit separate approval** after M1–M11 |

---

## 4. Recommended order

```
M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M9 → M10 → M11 → M12
```

**Rationale:**

1. Document roadmap (M1).
2. Clean Git index before large code commits (M2–M4).
3. Finish safe path refactors (M5–M6).
4. Commit automation source (M7–M8).
5. Write runbook before analysis entry-point changes (M9 before M10).
6. Optional results polish (M11).
7. New computation last (M12).

**Parallelism:** M5 and M6 may share a session as separate commits. M2–M4 must be sequential with verification between each.

---

## 5. Stop conditions

Cursor must **halt and ask** before proceeding when any of the following apply:

1. **Raw data** — move, rename, delete, or commit of `**/data/**`, `671_test_data_des/`, or 252 raw without review
2. **Generated output deletion** — any `rm` on batch, export, poster, or archive paths
3. **Recomputation** — running `analyze_*`, `run_gaga_batch_jcvpca.py`, `prepare_joint_heatmap_tables.py`, or full report regeneration
4. **Scientific logic** — thresholds, PCA/JcvPCA parameters, filtering, ranking, pooling, or interpretation beyond path display strings
5. **Large commits** — more than ~30 files staged without explicit file list approval
6. **Input vs generated ambiguity** — staging anything under `outputs/` without classification
7. **Canonical batch overwrite** — writing into `gaga_batch_jcvpca_20260626_193319/` without promotion plan
8. **`git add .`** — never permitted in this recovery workflow

---

## 6. Immediate next recommendation

**M1 complete** (`35e8222`). Bulk execution of **M2–M11** approved (M12 excluded).

Execution mode: proceed batch-by-batch automatically when validation passes and stop conditions are not triggered. Do **not** execute M12 without separate approval.

---

## 7. Bulk execution approval (M2–M11)

**Approved:** 2026-06-30 — user authorized automatic progression through M2–M11.

**Hard limits (all batches):**

- Do **not** execute M12 (new analysis).
- Do **not** run analysis, recompute JcvPCA, or regenerate reports (except `--dry-run` / `--validate-paths`).
- Do **not** move, rename, or delete raw data.
- Do **not** delete generated outputs from disk.
- Do **not** overwrite canonical batch `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/`.
- Do **not** use `git add .`.
- Do **not** change scientific logic (thresholds, PCA/JcvPCA parameters, filtering, ranking, pooling, interpretation).

**Per-batch deliverables:**

1. Execute batch per Section 3.
2. Explicit `git add` / `git rm --cached` only.
3. Run batch validation commands.
4. Commit with planned message.
5. Write summary: `docs/research_recovery/M{N}_BATCH_SUMMARY.md`

**Batch summary format (required):** batch name, files changed, files staged, commit hash, validation commands, analysis run?, raw data touched?, generated data moved/deleted from disk?, scientific logic changed?, dirty status summary, next batch or stop reason.

---

## Appendix — Completed batch summaries

| Batch | Commit | Summary doc | Status |
|-------|--------|-------------|--------|
| M1 | `35e8222` | _(session report)_ | **Complete** |
| M5 | `5f11062` | [M5_BATCH_SUMMARY.md](M5_BATCH_SUMMARY.md) | **Complete** |
| M6 | `9945eaa` | [M6_BATCH_SUMMARY.md](M6_BATCH_SUMMARY.md) | **Complete** |
| M7 | `5b804cc`, `c95441c` | [M7_BATCH_SUMMARY.md](M7_BATCH_SUMMARY.md) | **Complete** |
| M8 | `3150005` | [M8_BATCH_SUMMARY.md](M8_BATCH_SUMMARY.md) | **Complete** |
| M9 | `fbe76b2` | [M9_BATCH_SUMMARY.md](M9_BATCH_SUMMARY.md) | **Complete** |
| M10 | `3165125` | [M10_BATCH_SUMMARY.md](M10_BATCH_SUMMARY.md) | **Complete** |
| M11 | `80f4117` | [M11_BATCH_SUMMARY.md](M11_BATCH_SUMMARY.md) | **Complete** |
| M12 | — | — | **Not executed** (gated) |

---

*Master plan authored 2026-06-30. Update Git counts in Section 1 when starting each new batch.*
