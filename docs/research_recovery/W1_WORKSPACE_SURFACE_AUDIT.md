# W1 — Workspace Surface Audit

**Date:** 2026-06-30  
**Mode:** Read-only audit — no moves, no deletions  
**Context:** M12a validation passed; M12b 671 smoke batch passed; project is runnable but visually cluttered (~62 GB on disk in-repo)

**Disk snapshot (approximate):**

| Area | Size |
|------|------|
| Layer 2 (data + outputs) | ~54 GB |
| Layer 3 (mostly batch outputs) | ~4.5 GB |
| Layer 2.5 | ~2.0 GB |
| Layer 1 | ~1.5 GB |
| Root test export | ~232 MB |
| Poster figures | ~13 MB |
| Docs | ~8.5 MB |

---

## Classification key

| Class | Meaning |
|-------|---------|
| **A** | Daily working surface — see/use regularly |
| **B** | Active but heavy — needed to run; hide behind docs/pointers |
| **C** | Generated outputs — should not clutter daily view |
| **D** | Legacy layer folders — history/implementation detail |
| **E** | Raw / protected data — do not move without approval |
| **F** | Optional / ambiguous — manual review |

---

## Top-level inventory

| Path | Class | Role | Keep visible? | Proposed location | Risk | Path update? | Affects run cmds? | Recommendation |
|------|-------|------|---------------|-------------------|------|--------------|-------------------|----------------|
| `README.md` | A | Project overview (scientific + repo policy) | Yes | Root (keep); add `README_WORKING.md` as daily front door | Low | No | No | Keep; point daily users to `README_WORKING.md` |
| `README_WORKING.md` | A | *(to create W4)* Practical daily front door | Yes | Root | Low | No | No | Create in W4 |
| `PROJECT_STATUS.md` | A | Cleanup/continuation checkpoint | Yes | Root or `docs/` | Low | No | No | Keep at root short-term; optional move to `docs/` later |
| `config/` | A | Canonical path registry (`paths.yaml`) | Yes | Root | **High if moved** | Yes if moved | Yes | **Do not move** |
| `src/` | A | Shared `project_paths.py` loader | Yes | Root | **High if moved** | Yes if moved | Yes | **Do not move** |
| `scripts/` | A | Root health check + poster figure scripts | Yes | Root | Medium | Partial if split | Yes (poster paths in yaml) | Keep; document in `README_WORKING.md` |
| `docs/` | A | Audit, cleanup, research recovery docs | Yes | Root | Low | No | No | Keep; primary doc hub |
| `results/` | A | Lightweight results index + placeholders | Yes | Root | Low | No | No | Expand with pointer READMEs; no bulk symlinks yet |
| `Layer1_motive_qc/` | D/B | Layer 1 QC pipeline + raw data tree | Partial | Keep path; hide bulk via `.gitignore` + pointer README | Medium | Yes if renamed | Yes (L1 raw path in yaml) | Keep folder name; document as “Layer 1 — open only when re-QC needed” |
| `Layer2_Motive_Kinematics/` | D/B | Layer 2 kinematics code + 32 GB outputs + 21 GB data | Partial | Keep path; outputs already gitignored | **High** | Yes if paths change | Yes | Keep; treat `outputs/*_Take_*` as heavy generated (class C inside B) |
| `Layer2.5_Segmentation/` | A/B | Layer 2.5 export code + pre_jvcpca_review (~1.2 GB) | Partial | Keep path; exports gitignored | **High** | Yes if paths change | Yes | Daily entry for exports; code in `scripts/`, `dashboard/` |
| `Layer3_JcvPCA/` | A/B | Layer 3 JcvPCA code + 4 GB outputs | Partial | Keep path; batch dirs gitignored | **High** | Yes if paths change | Yes | Daily entry: `scripts/`, `.venv`, `outputs/` pointer |
| `outputs/` | C | Poster final figures (~13 MB, 51 files) | Partial | `results/poster/` pointer or symlink later | Low | Yes if moved | Yes (poster.final_figures in yaml) | Keep for now; register in `results/poster/` |
| `671_test_data_des/` | E | Root test Motive export (~232 MB CSV) | No | Keep path (yaml: `raw_data.root_test_exports`) | **High** | Yes if moved | Partial | **Do not move**; document as protected test export |
| `3_layers_Matser_plan_Full/` | D | Original master plan + pseudocode (116 KB) | No | `docs/legacy/master_plan/` | Low | No | No | Safe doc consolidation candidate |
| `LAYER1_RAW_MARKER_QC_AUDIT_REPORT.md` | F | Root-level audit report | No | `docs/audits/` | Low | No | No | Move to docs (safe) |
| `LAYER2_5_PROGRAM_AUDIT_REPORT.md` | F | Root-level audit report (770 lines) | No | `docs/audits/` | Low | No | No | Move to docs (safe) |
| `LAYER2_5_CRITICAL_FIXES_IMPLEMENTATION_REPORT.md` | F | Root-level implementation report | No | `docs/audits/` | Low | No | No | Move to docs (safe) |
| `.cursor/` | F | IDE metadata | No | Ignored | Low | No | No | Leave ignored |
| `.pytest_cache/` | C | Test cache | No | Ignored | Low | No | No | Leave ignored |
| `.git/` | — | Version control | Hidden | — | — | — | — | — |
| `.gitignore` | A | Output suppression rules | Yes | Root | **High if broken** | No | No | Keep; critical for clean `git status` |

---

## Major subfolder detail

### `config/`

| Path | Class | Role | Keep visible? | Proposed | Risk | Update? | Run cmds? | Recommendation |
|------|-------|------|---------------|----------|------|---------|-----------|----------------|
| `config/paths.yaml` | A | Single source of truth for all layer paths | Yes | Root | **Critical** | N/A | Yes | Never move without full R6-style migration |

### `src/`

| Path | Class | Role | Keep visible? | Proposed | Risk | Update? | Run cmds? | Recommendation |
|------|-------|------|---------------|----------|------|---------|-----------|----------------|
| `src/project_paths.py` | A | Loads `paths.yaml`; used by scripts | Yes | Root | **Critical** | N/A | Yes | Keep |

### `scripts/` (repo root)

| Path | Class | Role | Keep visible? | Proposed | Risk | Update? | Run cmds? | Recommendation |
|------|-------|------|---------------|----------|------|---------|-----------|----------------|
| `scripts/check_project_paths.py` | A | Health check — run first always | Yes | Root | Low | No | Yes | Primary validation command |
| `scripts/make_poster_final_figures.py` | B | Poster regeneration (reads canonical batch) | Partial | Root or `scripts/poster/` | Medium | yaml lists path | Yes | Keep; document “poster only” |
| `scripts/make_poster_671_figures.py` | B | 671 poster figures | Partial | Same | Medium | yaml lists path | Yes | Same |

### `docs/`

| Path | Class | Role | Keep visible? | Proposed | Risk | Update? | Run cmds? | Recommendation |
|------|-------|------|---------------|----------|------|---------|-----------|----------------|
| `docs/research_recovery/` | A | M/R batch logs, runbook, continuation plan | Yes | Keep | Low | No | No | **Primary operational doc folder** |
| `docs/cleanup_stage_A/` | D | Stage A audit artifacts | No | Keep; link from index | Low | No | No | Historical reference |
| `docs/cleanup_stage_B/` | D | Stage B move logs | No | Keep | Low | No | No | Historical reference |
| `docs/cleanup_stage_C/` | D | Stage C plans | No | Keep | Low | No | No | Historical reference |
| `docs/CLEANUP_INDEX.md` | A | Master cleanup index | Yes | Keep | Low | No | No | Cross-link from `README_WORKING.md` |
| `docs/PROJECT_AUDIT_DRAFT.md` | D | Initial 85 GB audit | No | Keep in docs | Low | No | No | Reference only |

### `results/`

| Path | Class | Role | Keep visible? | Proposed | Risk | Update? | Run cmds? | Recommendation |
|------|-------|------|---------------|----------|------|---------|-----------|----------------|
| `results/README.md` | A | Results layout index | Yes | Keep | Low | No | No | Expand with smoke batch pointer |
| `results/active/CANONICAL_BATCH.md` | A | Canonical batch pointer | Yes | Keep | Low | No | No | Add M12b smoke pointer sibling file |
| `results/active/` | A | Future symlinks to active outputs | Yes | Add pointer MD files only (W2) | Low | Maybe later | No | No physical moves yet |
| `results/archive_index/` | A | Off-repo archive registry | Yes | Populate with external paths | Low | No | No | Document external archive |
| `results/poster/`, `manuscript/`, `reports/` | A | Placeholder indexes | Partial | Add README pointers | Low | No | No | W2 target |

### `outputs/` (repo root — poster only)

| Path | Class | Role | Keep visible? | Proposed | Risk | Update? | Run cmds? | Recommendation |
|------|-------|------|---------------|----------|------|---------|-----------|----------------|
| `outputs/poster_final_figures/` | C | 51 poster PDF/PNG/SVG files | No | Stay; `results/poster/README` pointer | Low | yaml if moved | Yes (poster scripts) | Do not move until yaml + script update |

### `Layer1_motive_qc/`

| Path | Class | Role | Keep visible? | Proposed | Risk | Update? | Run cmds? | Recommendation |
|------|-------|------|---------------|----------|------|---------|-----------|----------------|
| `Layer1_motive_qc/motive_qc/` | D/B | L1 Python package, notebooks, scripts | Partial | Keep | Medium | Yes if renamed | Yes | Open when re-running L1 QC |
| `Layer1_motive_qc/motive_qc/data/` | E | Raw marker CSVs (gitignored) | No | Keep | **Critical** | yaml key | Partial | **Do not move** |
| `Layer1_motive_qc/motive_qc/outputs/` | C | QC run outputs | No | Gitignored batch_runs | Low | No | No | Regeneratable |

### `Layer2_Motive_Kinematics/`

| Path | Class | Role | Keep visible? | Proposed | Risk | Update? | Run cmds? | Recommendation |
|------|-------|------|---------------|----------|------|---------|-----------|----------------|
| `Layer2_Motive_Kinematics/src/` | A | L2 library code | Yes (via layer README) | Keep | Medium | Yes if moved | Yes | Code surface |
| `Layer2_Motive_Kinematics/scripts/` | A | L2 CLI runners | Yes | Keep | Medium | Yes | Yes | |
| `Layer2_Motive_Kinematics/tests/` | B | L2 tests | Partial | Keep | Low | No | No | |
| `Layer2_Motive_Kinematics/data/` | E | Raw/regenerated L2 input CSVs (~21 GB) | No | Keep | **Critical** | yaml | Yes | **Do not move**; gitignored |
| `Layer2_Motive_Kinematics/outputs/` | C | 12 session trees (~32 GB) + indices | No | Keep path; gitignored `*_Take_*` | **High** | yaml | Yes | Visible in Finder but not in git; external archive already holds historical |
| `Layer2_Motive_Kinematics/outputs/stage*_index.*` | A | Small navigable indices (untracked) | Partial | Could commit or move to `results/reports/` | Low | Maybe | No | Candidate to track in git for navigation |
| `Layer2_Motive_Kinematics/Archive.zip` | F | Legacy zip (~376 MB) | No | External archive | Low | No | No | Move outside repo when approved |
| `Layer2_Motive_Kinematics/.venv/` | B | L2 virtualenv | Hidden | Ignored | Low | No | Yes | Use for L2 commands only |
| `Layer2_Motive_Kinematics/docs/` | D | Layer-specific docs | No | Keep in layer | Low | No | No | |

**External (off-repo, referenced in yaml):**

`../gaga_psylo_external_archive/layer2_outputs_archive_2026-06-30/` — ~22 GB historical L2 outputs (Stage R1).

### `Layer2.5_Segmentation/`

| Path | Class | Role | Keep visible? | Proposed | Risk | Update? | Run cmds? | Recommendation |
|------|-------|------|---------------|----------|------|---------|-----------|----------------|
| `Layer2.5_Segmentation/scripts/` | A | Export builders | Yes | Keep | Medium | Yes | Yes | |
| `Layer2.5_Segmentation/dashboard/` | A | Review UI | Partial | Keep | Low | No | Partial | |
| `Layer2.5_Segmentation/config/` | A | Manifests | Yes | Keep | Medium | Yes | Yes | |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | B/C | L2.5 exports for JcvPCA (~1.2 GB) | No | Keep path | **Critical** | yaml | Yes | **Do not move**; 671+252 parquet trees gitignored |
| `Layer2.5_Segmentation/outputs/pre_jvpca_review/` | F | Typo duplicate folder name? | No | Manual review | Low | No | No | Check if empty/obsolete |
| `POST_LAYER2_SEGMENTATION_NOTEBOOK_PLAN*.md` | D | Large planning docs at layer root | No | `docs/legacy/layer2_5/` | Low | No | No | Safe doc move |
| `Layer2.5_Segmentation/notebooks/` | D | Jupyter notebooks | Partial | Keep | Low | No | Partial | |
| `Layer2.5_Segmentation/.venv/` | B | L2.5 virtualenv | Hidden | Ignored | Low | No | Yes | |

### `Layer3_JcvPCA/`

| Path | Class | Role | Keep visible? | Proposed | Risk | Update? | Run cmds? | Recommendation |
|------|-------|------|---------------|----------|------|---------|-----------|----------------|
| `Layer3_JcvPCA/scripts/` | A | Batch runner, report generators | Yes | Keep | Medium | Yes | Yes | **Primary L3 command surface** |
| `Layer3_JcvPCA/src/` | A | `layer3_jcvpca` package | Yes | Keep | Medium | Yes | Yes | |
| `Layer3_JcvPCA/.venv/` | A | L3 virtualenv (M12a/M12b validated) | Hidden | Ignored | Low | No | Yes | Always use for L3 |
| `Layer3_JcvPCA/tests/` | B | L3 tests | Partial | Keep | Low | No | No | |
| `Layer3_JcvPCA/config/` | A | L3-specific config | Yes | Keep | Medium | Maybe | Partial | |
| `Layer3_JcvPCA/docs/` | A/D | L3 scope docs + figures | Partial | Keep; trim root clutter into here | Low | No | No | |
| `Layer3_JcvPCA/README.md` | A | Layer 3 detailed readme | Yes | Keep | Low | No | No | |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | B/C | **Canonical batch (~3.6 GB)** | No | Keep path | **Critical** | yaml | Yes | **Frozen — do not move/promote overwrite** |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` | C | M12b smoke batch (~370 MB) | No | Keep path | **High** | No | No | **Do not move** until archived deliberately |
| `Layer3_JcvPCA/outputs/_workbench_*` | C | Dev/scratch workbench runs (~10 MB total) | No | External archive or `_archive_local/` | Low | No | No | Safe to archive off-repo after review |
| `Layer3_JcvPCA/outputs/671_g4_validation_001/` | C | Early validation run | No | Archive | Low | No | No | |
| `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | B | Poster CSV/MD evidence | Partial | Keep; yaml key | Medium | yaml if moved | Yes | |
| `Layer3_JcvPCA/outputs/nullspace_link_stability_review/` | C | Sidecar review outputs | No | `results/reports/` pointer | Low | yaml if moved | Partial | |
| `Layer3_JcvPCA/outputs/movement_organization_question_report/` | C | Sidecar report | No | Same | Low | yaml if moved | Partial | |
| `Layer3_JcvPCA/cursor_gaga_jcvpca_implementation_plan_with_addendum.md` | D | Planning doc at layer root | No | `docs/legacy/layer3/` | Low | No | No | Safe doc move |
| `Layer3_JcvPCA/prompt_to_build_plan.md` | D | Planning doc | No | `docs/legacy/layer3/` | Low | No | No | Safe doc move |
| `Layer3_JcvPCA/graph_enhancment_plan.md` | F | Future enhancement plan | No | `docs/legacy/layer3/` | Low | No | No | Safe doc move |
| `Layer3_JcvPCA/3_layers_Matser_plan_Full/` | D | Duplicate of root master plan folder | No | Consolidate to one location | Low | No | No | Remove duplicate after merge |
| `Layer3_JcvPCA/references/` | B | PDF references (JcvPCA paper) | Partial | Keep | Low | No | No | Modified PDF untracked — do not commit blindly |

### External archive (outside repo)

| Path | Class | Role | Keep visible? | Proposed | Risk | Update? | Run cmds? | Recommendation |
|------|-------|------|---------------|----------|------|---------|-----------|----------------|
| `../gaga_psylo_external_archive/` | D | Off-repo archives (L2 outputs, superseded L3 batches, Stage B) | Via pointer only | `results/archive_index/` README | Low | yaml already points | Partial | Document in `README_WORKING.md` |

---

## What makes the workspace feel messy (root causes)

1. **Three layer trees at root** (~62 GB) — correct for pipeline coupling but heavy in Finder/IDE file trees.
2. **Generated outputs inside layer folders** — gitignored but still visible on disk (L2 sessions, L2.5 parquet, L3 batches).
3. **Loose planning/audit markdown at root and layer roots** — not harmful but dilutes navigation.
4. **Multiple `.venv` directories** — one per layer; necessary but adds noise.
5. **Duplicate master plan** — `3_layers_Matser_plan_Full/` at root and under `Layer3_JcvPCA/`.
6. **Workbench scratch under `Layer3_JcvPCA/outputs/_workbench_*`** — small but confusing next to canonical batch.
7. **`git status` still shows untracked indices and docs** — not all heavy output is hidden from git (stage indices, planning md).

---

## Protected paths (never move in W3 “safe now”)

| Path | Reason |
|------|--------|
| `config/paths.yaml`, `src/project_paths.py` | Registry |
| `Layer1_motive_qc/motive_qc/data/` | Raw data |
| `Layer2_Motive_Kinematics/data/` | Raw/regenerated L2 inputs |
| `671_test_data_des/` | Registered test export |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | Active JcvPCA inputs |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | Canonical batch |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` | M12b smoke batch |
| All `Layer*/src/`, `Layer*/scripts/` (unless path migration project) | Runnable code |

---

## Related docs

- [`W2_TARGET_VISIBLE_STRUCTURE.md`](W2_TARGET_VISIBLE_STRUCTURE.md)
- [`W3_WORKSPACE_SIMPLIFICATION_MOVE_PLAN.md`](W3_WORKSPACE_SIMPLIFICATION_MOVE_PLAN.md)
- [`CONTINUATION_RUNBOOK.md`](CONTINUATION_RUNBOOK.md)
- [`M12A_VALIDATION_LOG.md`](M12A_VALIDATION_LOG.md)
- [`M12B_671_SMOKE_BATCH_LOG.md`](M12B_671_SMOKE_BATCH_LOG.md)

---

*Audit only — no files moved or deleted.*
