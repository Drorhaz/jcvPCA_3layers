# R4 — Hard-Coded Paths Review

**Date:** 2026-06-30  
**Scope:** Active source/scripts (`.py`) and key docs — cleanup docs excluded from priority ranking  
**Goal:** Identify paths to migrate to `config/paths.yaml` for scalable JcvPCA automation

---

## Summary

| Pattern | Active code hits | Runtime risk if path changes | Config migration priority |
|---------|------------------|------------------------------|---------------------------|
| `gaga_batch_jcvpca_20260626_193319` | **22** `.py` files | High | **P0** |
| `poster_ready_evidence_package` | **4** `.py` files | Medium | **P1** |
| `outputs/poster_final_figures` | **2** `.py` files | Low (poster frozen) | **P2** |
| `pre_jvcpca_review` (path strings) | **6** `.py` files | High for new batches | **P0** |
| `Layer2_Motive_Kinematics/outputs` | **2** `.py` (defaults) | Medium | **P1** |
| `Layer2_Motive_Kinematics/outputs/archive` | **0** active code | None (moved R1) | **P3** docs only |
| `Layer3_JcvPCA/outputs` (generic) | **20+** scripts | Medium | **P1** |

---

## P0 — Canonical batch `gaga_batch_jcvpca_20260626_193319`

| File | Reference | Purpose | Risk | Hard-code now? | Use paths.yaml? | Priority |
|------|-----------|---------|------|----------------|-----------------|----------|
| `Layer3_JcvPCA/scripts/generate_poster_ready_evidence_package.py` | `BATCH = ROOT / "outputs" / "gaga_batch_jcvpca_20260626_193319"` | Build evidence package from batch | High | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/analyze_directional_robustness_t1_t2.py` | `BATCH = ...` | Directional robustness analysis | High | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/analyze_directional_robustness_t1_t3.py` | same | same | High | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/analyze_directional_robustness_t2_t3.py` | same | same | High | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/generate_final_integrated_review.py` | `ROOT = .../gaga_batch_193319` | Integrated review MD | High | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/generate_master_full_numeric_report.py` | `ROOT = ...` | Master numeric report | High | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/generate_nullspace_full_numeric_report.py` | `BATCH = ...` | Nullspace report | Medium | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/analyze_nullspace_link_stability.py` | `BATCH = ...` | Nullspace analysis | Medium | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/analyze_natural_variability_deep_dive.py` | `BATCH = ...` | NV analysis | Medium | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/analyze_link_contribution_distribution.py` | path join | Link contribution | Medium | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/analyze_timepoint_link_contribution.py` | path join | Timepoint analysis | Medium | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/prepare_joint_heatmap_tables.py` | `ROOT = ...` | Heatmap prep | Medium | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/generate_pc_focus_review.py` | `root = ...` | PC focus review | Medium | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/update_pc_focus_interpretation_artifacts.py` | `BATCH = ...` | PC focus update | Medium | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/run_pc_focus_p50_p60_sensitivity.py` | path join | Sensitivity | Medium | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/generate_directional_robustness_*_full_numeric_report.py` (×3) | `ROOT = ...` | DR reports | Medium | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/generate_natural_variability_full_numeric_report.py` | `ROOT = ...` | NV report | Medium | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/generate_movement_organization_question_report.py` | `BATCH = ...` | Movement org report | Medium | yes | **yes** | P0 |
| `scripts/make_poster_final_figures.py` | `SEARCH_DIRS[1]` | Poster figure D CSVs | High | yes | **yes** | P0 |
| `scripts/make_poster_671_figures.py` | JRW audit path under batch | Poster fig 1 check | High | yes | **yes** | P0 |
| `Layer3_JcvPCA/scripts/generate_poster_evidence_report.py` | string in MD template | Doc generation | Low | yes | **yes** | P1 |

**Note:** `run_gaga_batch_jcvpca.py` uses **timestamped** output dir by default — good pattern. Post-hoc scripts hard-code `193319`.

---

## P0 — Layer 2.5 `pre_jvcpca_review`

| File | Reference | Purpose | Risk | Hard-code now? | Use paths.yaml? | Priority |
|------|-----------|---------|------|----------------|-----------------|----------|
| `Layer3_JcvPCA/src/layer3_jcvpca/gaga_batch_runner.py` | `default_layer25_root()` → `.../pre_jvcpca_review` | Batch runner input root | **High** | yes | **yes** | P0 |
| `Layer3_JcvPCA/src/layer3_jcvpca/inventory.py` | same pattern | Export inventory | High | yes | **yes** | P0 |
| `Layer2.5_Segmentation/src/pre_jvcpca_review/app_controller.py` | `project_root / "outputs" / "pre_jvcpca_review"` | Review controller default | Medium | yes | **yes** | P0 |
| `Layer3_JcvPCA/tests/test_comparable_links.py` | hard-coded test path | Test fixture | Low | yes | yes | P2 |
| `Layer3_JcvPCA/tests/test_dataset_builder.py` | hard-coded test path | Test fixture | Low | yes | yes | P2 |
| `Layer3_JcvPCA/tests/test_workbench_preflight.py` | hard-coded test path | Test fixture | Low | yes | yes | P2 |

**Good pattern already:** `run_gaga_batch_jcvpca.py --layer25-root` CLI override.

---

## P1 — Poster evidence package

| File | Reference | Purpose | Risk | Hard-code now? | Use paths.yaml? | Priority |
|------|-----------|---------|------|----------------|-----------------|----------|
| `scripts/make_poster_final_figures.py` | `SEARCH_DIRS[0]` poster_ready_evidence_package | Primary CSV search | Medium | yes | **yes** | P1 |
| `Layer3_JcvPCA/scripts/generate_poster_ready_evidence_package.py` | `OUT = .../poster_ready_evidence_package` | Writer | Medium | yes | **yes** | P1 |
| `Layer3_JcvPCA/scripts/generate_movement_organization_question_report.py` | `PKG = .../poster_ready_evidence_package` | Report inputs | Low | yes | **yes** | P1 |
| `Layer3_JcvPCA/scripts/generate_poster_evidence_report.py` | string reference | Doc template | Low | yes | **yes** | P2 |

---

## P1 — Layer 2 active outputs

| File | Reference | Purpose | Risk | Hard-code now? | Use paths.yaml? | Priority |
|------|-----------|---------|------|----------------|-----------------|----------|
| `Layer2.5_Segmentation/src/pre_jvcpca_review/session_index.py` | `DEFAULT_LAYER2_ROOT = .../Layer2_Motive_Kinematics/outputs` | Session discovery | Medium | yes | **yes** | P1 |
| `Layer2.5_Segmentation/tests/test_layer2_5_critical_fixes.py` | string `"Layer2_Motive_Kinematics/outputs"` | Test | Low | yes | yes | P2 |

**Archive exclusion (good):** `session_index.scan_layer2_sessions()` skips paths with `archive` in parents — safe after R1 move.

---

## P2 — Poster output directory

| File | Reference | Purpose | Risk | Hard-code now? | Use paths.yaml? | Priority |
|------|-----------|---------|------|----------------|-----------------|----------|
| `scripts/make_poster_final_figures.py` | `OUT_DIR = outputs/poster_final_figures` | Write target | Low | yes | **yes** | P2 |
| `scripts/make_poster_671_figures.py` | imports from final figures script | Same OUT_DIR | Low | yes | **yes** | P2 |

Poster is complete — low urgency unless regenerating figures.

---

## P2 — Layer 3 workbench demo paths (671-specific exports)

| File | Reference | Purpose | Risk | Hard-code now? | Use paths.yaml? | Priority |
|------|-----------|---------|------|----------------|-----------------|----------|
| `Layer3_JcvPCA/src/layer3_jcvpca/app_controller.py` | Hard-coded parquet paths for 671 windows | Workbench demo | Medium | yes | **yes** | P2 |

Example keys: `671_T1_P1_R1_g4_s14280_e21000`, etc.

---

## P3 — Layer 2 archive (no active runtime dependency)

| Location | Reference | Purpose | Risk | Hard-code now? | Use paths.yaml? | Priority |
|----------|-----------|---------|------|----------------|-----------------|----------|
| Cleanup docs (Stages A–C) | `outputs/archive/` | Documentation | None | N/A | optional | P3 |
| `Layer2_Motive_Kinematics/docs/LAYER2_KINEMATIC_CHAIN_QC_AUDIT_2026-06-23.md` | `outputs/audit_rerun_*` | Audit report (paths now external) | Low | N/A | update doc paths | P3 |

**No `.py` runtime reads** `Layer2_Motive_Kinematics/outputs/archive` after R1 move.

---

## P3 — Generic `Layer3_JcvPCA/outputs`

Most Layer 3 scripts use:

```python
ROOT = Path(__file__).resolve().parents[1] / "outputs" / "gaga_batch_jcvpca_20260626_193319"
```

Refactor target:

```python
from project_paths import layer3_canonical_batch  # future helper reading config/paths.yaml
```

---

## Recommended refactor order (future coding stage)

1. **Shared path loader** — `Layer3_JcvPCA/src/layer3_jcvpca/project_paths.py` (or root `config/load_paths.py`) reading `config/paths.yaml`.
2. **Batch scripts** — replace `BATCH = .../193319` constants (20 files).
3. **Batch runner defaults** — wire `default_layer25_root()` to YAML.
4. **Poster scripts** — read search dirs from config (optional; poster frozen).
5. **Tests** — fixture paths via config or env override.
6. **Documentation** — update hard-coded paths in MD to reference config keys.

---

## Scripts with good patterns (keep / extend)

| File | Pattern |
|------|---------|
| `Layer3_JcvPCA/scripts/run_gaga_batch_jcvpca.py` | CLI `--layer25-root`, `--output-dir` |
| `Layer2.5_Segmentation/scripts/build_gaga_exports.py` | CLI `--output-root` |
| `session_index.py` | Computed `DEFAULT_*_ROOT` from project root (move to YAML) |

---

*No code changes in R4. See [`R5_RESEARCH_CONTINUATION_STATUS.md`](R5_RESEARCH_CONTINUATION_STATUS.md) for next steps.*
