# Sidecar reports and indices (pointer index)

Sidecar analysis reports and small navigation indices remain at their **on-disk layer paths**. This folder indexes them only — no bulk report regeneration here.

---

## Layer 3 sidecar reports (on disk)

| Report | Path |
|--------|------|
| Movement organization | `Layer3_JcvPCA/outputs/movement_organization_question_report/` |
| Nullspace link stability | `Layer3_JcvPCA/outputs/nullspace_link_stability_review/` |

**Validators (read-only):**

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python generate_movement_organization_question_report.py --validate-paths
../.venv/bin/python generate_nullspace_full_numeric_report.py --dry-run
```

---

## Canonical batch reports (inside frozen batch)

All interpretive MD reports live inside the canonical batch folder:

```
Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/
```

Examples: `FINAL_integrated_deep_review_after_p50_p60.md`, `joint_heatmap_full_numeric_report.md`, directional robustness reports.

**Pointer:** [`../active/CANONICAL_BATCH.md`](../active/CANONICAL_BATCH.md)

---

## Layer 2 stage indices (navigation)

Small CSV/MD indices under `Layer2_Motive_Kinematics/outputs/`:

- `stage00_01_report_index.*` through `stage08_filtering_index.*`
- `layer2_qc_session_manifest.csv`, `layer2_qc_link_manifest.csv`

Regenerate via Layer 2 pipeline when sessions change.

---

## Poster evidence

```
Layer3_JcvPCA/outputs/poster_ready_evidence_package/
```

**Poster figures:** [`../poster/README.md`](../poster/README.md)

---

## Deferred (requires yaml + script update)

Physical copy or symlink of sidecar reports into `results/reports/` is deferred — see [`FINAL_CLEANUP_PLAN.md`](../../docs/research_recovery/FINAL_CLEANUP_PLAN.md) Section 6.
