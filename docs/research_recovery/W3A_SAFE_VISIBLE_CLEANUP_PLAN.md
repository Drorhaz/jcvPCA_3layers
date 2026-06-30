# W3a — Safe Visible Cleanup Plan

**Date:** 2026-06-30  
**Scope:** Category 1 from [`W3_WORKSPACE_SIMPLIFICATION_MOVE_PLAN.md`](W3_WORKSPACE_SIMPLIFICATION_MOVE_PLAN.md) only  
**Not in scope:** W3b (external archive), W3c (path yaml moves), raw data, outputs, batches, source code

---

## Pre-move validation

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
python scripts/check_project_paths.py
```

**Expected:** exit 0

---

## Moves to execute

### A — Root audit reports → `docs/audits/`

| # | Source | Destination | Reason | Risk | Rollback |
|---|--------|-------------|--------|------|----------|
| A1 | `LAYER1_RAW_MARKER_QC_AUDIT_REPORT.md` | `docs/audits/LAYER1_RAW_MARKER_QC_AUDIT_REPORT.md` | Root clutter | Low | `mv docs/audits/LAYER1_RAW_MARKER_QC_AUDIT_REPORT.md .` |
| A2 | `LAYER2_5_PROGRAM_AUDIT_REPORT.md` | `docs/audits/LAYER2_5_PROGRAM_AUDIT_REPORT.md` | Root clutter | Low | `mv docs/audits/LAYER2_5_PROGRAM_AUDIT_REPORT.md .` |
| A3 | `LAYER2_5_CRITICAL_FIXES_IMPLEMENTATION_REPORT.md` | `docs/audits/LAYER2_5_CRITICAL_FIXES_IMPLEMENTATION_REPORT.md` | Root clutter | Low | `mv docs/audits/LAYER2_5_CRITICAL_FIXES_IMPLEMENTATION_REPORT.md .` |

### B — Layer 2.5 planning → `docs/legacy/layer2_5/`

| # | Source | Destination | Reason | Risk | Rollback |
|---|--------|-------------|--------|------|----------|
| B1 | `Layer2.5_Segmentation/POST_LAYER2_SEGMENTATION_NOTEBOOK_PLAN.md` | `docs/legacy/layer2_5/POST_LAYER2_SEGMENTATION_NOTEBOOK_PLAN.md` | Layer root clutter | Low | Reverse `mv` |
| B2 | `Layer2.5_Segmentation/POST_LAYER2_SEGMENTATION_NOTEBOOK_PLAN_DECISION_SCOPE_REVISED.md` | `docs/legacy/layer2_5/POST_LAYER2_SEGMENTATION_NOTEBOOK_PLAN_DECISION_SCOPE_REVISED.md` | Same | Low | Reverse `mv` |

### C — Layer 3 planning → `docs/legacy/layer3/`

| # | Source | Destination | Reason | Risk | Rollback |
|---|--------|-------------|--------|------|----------|
| C1 | `Layer3_JcvPCA/cursor_gaga_jcvpca_implementation_plan_with_addendum.md` | `docs/legacy/layer3/cursor_gaga_jcvpca_implementation_plan_with_addendum.md` | Layer root clutter | Low | Reverse `mv` |
| C2 | `Layer3_JcvPCA/prompt_to_build_plan.md` | `docs/legacy/layer3/prompt_to_build_plan.md` | Same | Low | Reverse `mv` |
| C3 | `Layer3_JcvPCA/graph_enhancment_plan.md` | `docs/legacy/layer3/graph_enhancment_plan.md` | Same | Low | Reverse `mv` |

### D — Master plan consolidation → `docs/legacy/master_plan/`

| # | Source | Destination | Reason | Risk | Rollback |
|---|--------|-------------|--------|------|----------|
| D1 | `3_layers_Matser_plan_Full/*` | `docs/legacy/master_plan/` (flatten) | Single master plan location | Low | `mv docs/legacy/master_plan/* 3_layers_Matser_plan_Full/` after `mkdir` |
| D2 | `Layer3_JcvPCA/3_layers_Matser_plan_Full/LAYER3_JCVPCA_PSEUDOCODE.md` | `docs/legacy/master_plan/LAYER3_JCVPCA_PSEUDOCODE.md` | L3-only unique file | Low | Reverse `mv` |
| D3 | `Layer3_JcvPCA/3_layers_Matser_plan_Full/jvcPCA_elborated_implmentationPlan_w_movementTaskGroups.html` | `docs/legacy/master_plan/jvcPCA_elborated_implmentationPlan_w_movementTaskGroups.html` | L3-only unique file | Low | Reverse `mv` |
| D4 | `Layer3_JcvPCA/3_layers_Matser_plan_Full/` (remainder) | `docs/legacy/master_plan/layer3_jcvpca_subcopy/` | Preserve duplicate copies; no delete | Low | `mv docs/legacy/master_plan/layer3_jcvpca_subcopy Layer3_JcvPCA/3_layers_Matser_plan_Full` |

**Note:** `prompt_to_build_plan.md` references root master plan paths; file moves to legacy with content unchanged (historical doc).

### E — Pointer README files (create only)

| # | Path | Purpose | Risk | Rollback |
|---|------|---------|------|----------|
| E1 | `results/active/SMOKE_BATCH_671.md` | M12b smoke batch pointer | Low | `rm results/active/SMOKE_BATCH_671.md` |
| E2 | `results/poster/README.md` | Poster figures pointer | Low | `rm results/poster/README.md` |
| E3 | `results/archive_index/EXTERNAL_ARCHIVE.md` | External archive map | Low | `rm results/archive_index/EXTERNAL_ARCHIVE.md` |
| E4 | `docs/legacy/README.md` | Index of legacy doc locations | Low | `rm docs/legacy/README.md` |

### F — Update daily guide

| # | File | Change | Risk |
|---|------|--------|------|
| F1 | `README_WORKING.md` | Add legacy/audit doc paths; mark W3a complete | Low |

---

## Explicitly not moving (W3a guardrails)

- Raw data (`Layer*/data/`, `671_test_data_des/`)
- Layer 2 active outputs (`Layer2_Motive_Kinematics/outputs/*_Take_*`)
- Layer 2.5 `pre_jvcpca_review/`
- Canonical batch `gaga_batch_jcvpca_20260626_193319`
- M12b smoke batch `gaga_batch_jcvpca_smoke_671_20260630_214341`
- Source code, scripts, config, venvs
- `Layer3_JcvPCA/backend_readiness_report.md` (layer doc; not root clutter — manual review)

---

## Post-move validation

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project
python scripts/check_project_paths.py
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319
test -d Layer3_JcvPCA/outputs/gaga_batch_jcvpca_smoke_671_20260630_214341
test -d Layer2.5_Segmentation/outputs/pre_jvcpca_review/671
```

**Expected:** path check exit 0; all three directories exist.

---

## Full rollback (reverse order)

```bash
cd /Users/drorhazan/Desktop/gaga_psilo/projects/3Layers_project

# Master plan
mv docs/legacy/master_plan/layer3_jcvpca_subcopy Layer3_JcvPCA/3_layers_Matser_plan_Full
mv docs/legacy/master_plan/jvcPCA_elborated_implmentationPlan_w_movementTaskGroups.html Layer3_JcvPCA/3_layers_Matser_plan_Full/ 2>/dev/null || true
mv docs/legacy/master_plan/LAYER3_JCVPCA_PSEUDOCODE.md Layer3_JcvPCA/3_layers_Matser_plan_Full/ 2>/dev/null || true
mkdir -p 3_layers_Matser_plan_Full
mv docs/legacy/master_plan/MASTER_PLAN.md docs/legacy/master_plan/MASTER_PLAN_V5_1_CURSOR_SCOPE_ADDENDUM.md docs/legacy/master_plan/gaga_task_part1_movement_groups.md docs/legacy/master_plan/layer1-* docs/legacy/master_plan/layer2* docs/legacy/master_plan/layer3* 3_layers_Matser_plan_Full/ 2>/dev/null || true

# Layer 3 legacy
mv docs/legacy/layer3/* Layer3_JcvPCA/

# Layer 2.5 legacy
mv docs/legacy/layer2_5/* Layer2.5_Segmentation/

# Audits
mv docs/audits/LAYER*.md .

# Pointer files: delete if created
rm -f results/active/SMOKE_BATCH_671.md results/poster/README.md results/archive_index/EXTERNAL_ARCHIVE.md docs/legacy/README.md
```

---

*Plan created immediately before W3a execution.*
