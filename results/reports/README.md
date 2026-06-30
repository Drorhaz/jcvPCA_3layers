# Sidecar reports and indices

Table of contents for all categorized report indexes. Physical files stay at layer paths until P3 symlinks.

---

## Index files (this folder)

| Index | Topic |
|-------|-------|
| [`CANONICAL_BATCH_REPORTS.md`](CANONICAL_BATCH_REPORTS.md) | 14 MD reports inside frozen batch `193319` |
| [`MOVEMENT_ORGANIZATION.md`](MOVEMENT_ORGANIZATION.md) | Movement organization sidecar |
| [`NULLSPACE_LINK_STABILITY.md`](NULLSPACE_LINK_STABILITY.md) | Nullspace link stability sidecar |
| [`POSTER_EVIDENCE.md`](POSTER_EVIDENCE.md) | Poster-ready evidence CSV package |

## Symlinks (after P3)

| Symlink | Target |
|---------|--------|
| `movement_organization/` | `Layer3_JcvPCA/outputs/movement_organization_question_report/` |
| `nullspace_link_stability/` | `Layer3_JcvPCA/outputs/nullspace_link_stability_review/` |

## Related indexes

| Location | Content |
|----------|-----------|
| [`../active/CANONICAL_BATCH.md`](../active/CANONICAL_BATCH.md) | Canonical batch pointer |
| [`../active/LAYER25_EXPORTS.md`](../active/LAYER25_EXPORTS.md) | L2.5 export inputs |
| [`../poster/FIGURE_MANIFEST.md`](../poster/FIGURE_MANIFEST.md) | Poster figures A–D |
| [`../poster/evidence_package/`](../poster/evidence_package) | Poster evidence (symlink P3) |

## Layer 2 stage indices

Small CSV/MD under `Layer2_Motive_Kinematics/outputs/`:

- `stage00_01_report_index.*` through `stage08_filtering_index.*`
- `layer2_qc_session_manifest.csv`, `layer2_qc_link_manifest.csv`

## Validators

```bash
cd Layer3_JcvPCA/scripts
../.venv/bin/python generate_movement_organization_question_report.py --validate-paths
../.venv/bin/python generate_nullspace_full_numeric_report.py --dry-run
../.venv/bin/python generate_final_integrated_review.py --validate-paths
```
