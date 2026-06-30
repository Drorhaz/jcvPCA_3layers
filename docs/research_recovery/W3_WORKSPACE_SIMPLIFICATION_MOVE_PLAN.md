# W3 — Workspace Simplification Move Plan

**Date:** 2026-06-30  
**Mode:** Plan only — **do not execute until explicitly approved**  
**Rollback principle:** Every move is `mv` reversible; nothing deleted

---

## Execution gates

Before any move batch:

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
python scripts/check_project_paths.py
```

After any move batch:

```bash
python scripts/check_project_paths.py
cd Layer3_JcvPCA/scripts
../.venv/bin/python generate_final_integrated_review.py --validate-paths
../.venv/bin/python run_gaga_batch_jcvpca.py --help
```

---

## Category 1 — Safe now (documentation / clutter only)

No `config/paths.yaml` changes. No raw data. No batch folders.

| # | Source | Destination | Reason | Risk | Config? | Code? | Validation | Rollback |
|---|--------|-------------|--------|------|---------|-------|------------|----------|
| 1.1 | `LAYER1_RAW_MARKER_QC_AUDIT_REPORT.md` | `docs/audits/LAYER1_RAW_MARKER_QC_AUDIT_REPORT.md` | Root clutter | Low | No | No | `check_project_paths.py` | `mv docs/audits/LAYER1_RAW_MARKER_QC_AUDIT_REPORT.md .` |
| 1.2 | `LAYER2_5_PROGRAM_AUDIT_REPORT.md` | `docs/audits/LAYER2_5_PROGRAM_AUDIT_REPORT.md` | Root clutter | Low | No | No | Same | Reverse mv |
| 1.3 | `LAYER2_5_CRITICAL_FIXES_IMPLEMENTATION_REPORT.md` | `docs/audits/LAYER2_5_CRITICAL_FIXES_IMPLEMENTATION_REPORT.md` | Root clutter | Low | No | No | Same | Reverse mv |
| 1.4 | `Layer2.5_Segmentation/POST_LAYER2_SEGMENTATION_NOTEBOOK_PLAN.md` | `docs/legacy/layer2_5/POST_LAYER2_SEGMENTATION_NOTEBOOK_PLAN.md` | Layer root clutter | Low | No | No | Same | Reverse mv |
| 1.5 | `Layer2.5_Segmentation/POST_LAYER2_SEGMENTATION_NOTEBOOK_PLAN_DECISION_SCOPE_REVISED.md` | `docs/legacy/layer2_5/POST_LAYER2_SEGMENTATION_NOTEBOOK_PLAN_DECISION_SCOPE_REVISED.md` | Same | Low | No | No | Same | Reverse mv |
| 1.6 | `Layer3_JcvPCA/cursor_gaga_jcvpca_implementation_plan_with_addendum.md` | `docs/legacy/layer3/cursor_gaga_jcvpca_implementation_plan_with_addendum.md` | Layer root clutter | Low | No | No | Same | Reverse mv |
| 1.7 | `Layer3_JcvPCA/prompt_to_build_plan.md` | `docs/legacy/layer3/prompt_to_build_plan.md` | Same | Low | No | No | Same | Reverse mv |
| 1.8 | `Layer3_JcvPCA/graph_enhancment_plan.md` | `docs/legacy/layer3/graph_enhancment_plan.md` | Same | Low | No | No | Same | Reverse mv |
| 1.9 | `Layer3_JcvPCA/3_layers_Matser_plan_Full/` | Merge into `docs/legacy/master_plan/` (dedupe vs root copy) | Duplicate master plan | Low | No | No | Visual diff root vs L3 copy | Reverse mv from backup |
| 1.10 | `3_layers_Matser_plan_Full/` | `docs/legacy/master_plan/` (after dedupe) | Single master plan location | Low | No | No | Update links in README if any | Reverse mv |
| 1.11 | *(create)* `results/active/SMOKE_BATCH_671.md` | Pointer file only | M12b navigation | Low | No | No | Read file | Delete file |
| 1.12 | *(create)* `results/poster/README.md` | Pointer to `outputs/poster_final_figures/` | Poster navigation | Low | No | No | Read file | Delete file |
| 1.13 | *(create)* `results/archive_index/EXTERNAL_ARCHIVE.md` | Map external archive | Off-repo navigation | Low | No | No | Read file | Delete file |
| 1.14 | *(create)* `README_WORKING.md` | Root daily front door | Ergonomics | Low | No | No | Human read | Delete file |

**Batch 1 prep commands (create dirs only when executing):**

```bash
mkdir -p docs/audits docs/legacy/layer2_5 docs/legacy/layer3 docs/legacy/master_plan
```

---

## Category 2 — Safe after path update

Requires `config/paths.yaml` + any hardcoded script paths updated and validated.

| # | Source | Destination | Reason | Risk | Config? | Code? | Validation | Rollback |
|---|--------|-------------|--------|------|---------|-------|------------|----------|
| 2.1 | `outputs/poster_final_figures/` | `results/poster/final_figures/` | Consolidate poster deliverables | Medium | **Yes** (`poster.final_figures`) | **Yes** (`make_poster_*.py` if hardcoded) | Path check + poster dry-run | Reverse mv + yaml revert |
| 2.2 | `Layer3_JcvPCA/outputs/poster_ready_evidence_package/` | `results/poster/evidence_package/` symlink or pointer | Clearer results layout | Medium | **Yes** (`layer3.poster_evidence_package`) | **Yes** (report scripts) | M12a validators | Reverse |
| 2.3 | `Layer3_JcvPCA/outputs/movement_organization_question_report/` | `results/reports/movement_organization/` | Sidecar organization | Medium | **Yes** (if registered) | **Yes** (report script defaults) | `--validate-paths` | Reverse |
| 2.4 | `Layer3_JcvPCA/outputs/nullspace_link_stability_review/` | `results/reports/nullspace_link_stability/` | Same | Medium | Maybe | Maybe | Report validators | Reverse |
| 2.5 | `results/active/` symlink | `results/active/canonical_batch` → L3 canonical | Shorter path for humans | Medium | Optional new yaml key | Maybe | Path check | `rm` symlink |
| 2.6 | `PROJECT_STATUS.md` | `docs/PROJECT_STATUS.md` | Root slimming | Low | No | Update README links | Read | Reverse mv |

**Do not execute 2.x until a dedicated R7-style path migration batch is approved.**

---

## Category 3 — Do not move

| Path | Reason |
|------|--------|
| `config/paths.yaml` | Registry anchor |
| `src/project_paths.py` | Loader |
| `scripts/check_project_paths.py` | Health gate location |
| `Layer1_motive_qc/motive_qc/data/` | Raw data (E) |
| `Layer2_Motive_Kinematics/data/` | Raw/regenerated inputs (E) |
| `671_test_data_des/` | Registered test export (E) |
| `Layer2.5_Segmentation/outputs/pre_jvcpca_review/` | Active JcvPCA inputs |
| `Layer2.5_Segmentation/segmentation/` | Segmentation xlsx (yaml) |
| `Layer2.5_Segmentation/config/` | Manifests |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/` | **Canonical batch — frozen** |
| `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341/` | **M12b smoke — keep until archived** |
| `Layer2_Motive_Kinematics/outputs/*_Take_*` | Active L2 sessions (regenerate/export chain) |
| All `Layer*/src/`, primary `Layer*/scripts/` | Runnable code |
| All `.venv/` directories | Environment bindings |

---

## Category 4 — Move outside repo (external archive)

Target base: `../gaga_psylo_external_archive/workspace_simplification_2026-06-30/` *(proposed new folder)*

| # | Source | Destination | Reason | Risk | Config? | Code? | Validation | Rollback |
|---|--------|-------------|--------|------|---------|-------|------------|----------|
| 4.1 | `Layer2_Motive_Kinematics/Archive.zip` | External archive | ~376 MB legacy zip | Low | No | No | Path check | `mv` back |
| 4.2 | `Layer3_JcvPCA/outputs/_workbench_*` (all) | `.../layer3_workbench_scratch/` | Dev scratch (~10 MB) | Low | No | No | Path check; batch unaffected | `mv` back |
| 4.3 | `Layer3_JcvPCA/outputs/671_g4_validation_001/` | `.../layer3_early_validation/` | Superseded pilot | Low | No | No | Path check | `mv` back |
| 4.4 | `Layer3_JcvPCA/outputs/layer3_jcvpca/` | External if empty/scratch | Minimal dir | Low | No | No | Path check | `mv` back |

**Not yet:** canonical batch, smoke batch, L2 session outputs, L2.5 exports — too active.

**External archive already holds (reference only):**

- Superseded L3 batches (5)
- Layer 2 historical outputs (~22 GB, Stage R1)

---

## Category 5 — Manual review

| Path | Question | Default action |
|------|----------|----------------|
| `Layer2.5_Segmentation/outputs/pre_jvpca_review/` | Typo duplicate of `pre_jvcpca_review`? | Inspect contents; merge or archive if empty duplicate |
| `Layer2_Motive_Kinematics/outputs/stage*_index.*` | Track in git or move to `results/reports/`? | Optional commit for navigation |
| `Layer3_JcvPCA/references/JcvPCA and JsvCRP.pdf` | Modified untracked — intentional? | Do not move; user decides commit |
| `Layer3_JcvPCA/docs/figures/` | Untracked workflow SVG | Optional commit to git or keep local |
| `Layer2_Motive_Kinematics/data/252/` | Untracked raw tree | **Do not move**; verify 252 onboarding |
| `Layer2.5_Segmentation/notebooks/` | Still used vs dashboard? | Keep until L2.5 workflow confirmed |
| Root `671_test_data_des/*_Take*.csv` | 232 MB test export | Keep; already gitignored |
| `docs/research_recovery/M12_PRE_ANALYSIS_READINESS.md` | Untracked | Commit when ready (doc only) |

---

## Recommended execution order (when approved)

### Phase W3a — Docs only (Category 1)

1. Create `docs/audits/`, `docs/legacy/*`
2. Move root audit reports (1.1–1.3)
3. Move layer planning docs (1.4–1.8)
4. Consolidate master plan (1.9–1.10) — **backup before dedupe**
5. Create pointer READMEs (1.11–1.14)
6. Run validation gate
7. Commit **documentation moves only** (explicit paths, no `git add .`)

### Phase W3b — External archive (Category 4)

1. Create external folder with dated name
2. Move workbench scratch + Archive.zip (4.1–4.4)
3. Log moves in `docs/research_recovery/W3_MOVE_LOG.csv` *(create at execution time)*
4. Run validation gate

### Phase W3c — Path migration (Category 2)

**Defer** until separate approval — requires yaml + script refactor batch.

---

## Validation checklist (after any phase)

| Check | Command | Expected |
|-------|---------|----------|
| Path registry | `python scripts/check_project_paths.py` | Exit 0 |
| Canonical batch exists | `test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319` | OK |
| Smoke batch exists | `test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341` | OK |
| L3 validators | `../.venv/bin/python generate_final_integrated_review.py --validate-paths` | Exit 0 |
| L3 runner | `../.venv/bin/python run_gaga_batch_jcvpca.py --help` | Exit 0 |
| L2.5 exports | `ls Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/` | 6 session trees |

---

## Rollback template

For any doc move:

```bash
# Example: undo audit report move
mv docs/audits/LAYER2_5_PROGRAM_AUDIT_REPORT.md ./LAYER2_5_PROGRAM_AUDIT_REPORT.md
```

For external archive move:

```bash
mv ../gaga_psylo_external_archive/workspace_simplification_2026-06-30/layer3_workbench_scratch \
   Layer3_JcvPCA/outputs/
# (adjust per moved folder)
```

For yaml migration rollback: revert `config/paths.yaml` from git + reverse physical move.

---

## Risk summary

| Phase | Risk | Breaks runs? |
|-------|------|--------------|
| W3a docs + pointers | **Low** | No |
| W3b external scratch | **Low** | No (not in yaml) |
| W3c path migration | **Medium–High** | Yes if incomplete |

---

## Related docs

- [`W1_WORKSPACE_SURFACE_AUDIT.md`](W1_WORKSPACE_SURFACE_AUDIT.md)
- [`W2_TARGET_VISIBLE_STRUCTURE.md`](W2_TARGET_VISIBLE_STRUCTURE.md)
- [`CONTINUATION_RUNBOOK.md`](CONTINUATION_RUNBOOK.md)
- [`docs/CLEANUP_INDEX.md`](../CLEANUP_INDEX.md) — prior cleanup stages A–C

---

*Move plan only — nothing executed in W stage.*
