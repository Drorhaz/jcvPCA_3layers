# Layer 2.5 JcvPCA export inputs

**Physical path:** `Layer2.5_Segmentation/outputs/pre_jvcpca_review/`  
**Config key:** `layer2_5.pre_jvcpca_review`

## Participants

| Participant | Path | Role |
|-------------|------|------|
| 671 | `pre_jvcpca_review/671/` | In canonical batch; flagship |
| 252 | `pre_jvcpca_review/252/` | Batch cohort; onboarding |

## Check exports

```bash
ls Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/
ls Layer2.5_Segmentation/outputs/pre_jvcpca_review/252/
```

## Regenerate

```bash
cd Layer2.5_Segmentation
.venv/bin/python scripts/build_gaga_exports.py --help
```

252 manifest: `Layer2.5_Segmentation/config/group4_core_16link_within_252_feature_manifest.csv`

**Do not delete** existing export folders without explicit approval.
