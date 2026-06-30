# Poster Final Figures - Data Validation Report

**Final status: PASS**

Descriptive within-participant analysis; participants not pooled.

## Files used

- `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/comparisons/671_B_L1_T1_vs_T2/run/link_level_jrw_rss.csv` -> `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/comparisons/671_B_L1_T1_vs_T2/run/link_level_jrw_rss.csv`
- `longitudinal_delta_nv_ratio_by_link.csv` -> `Layer3_JcvPCA/outputs/poster_ready_evidence_package/longitudinal_delta_nv_ratio_by_link.csv`
- `natural_variability_scalar_poster_table.csv` -> `Layer3_JcvPCA/outputs/poster_ready_evidence_package/natural_variability_scalar_poster_table.csv`
- `body_region_anatomical_family_summary.csv` -> `Layer3_JcvPCA/outputs/poster_ready_evidence_package/body_region_anatomical_family_summary.csv`
- `nullspace_top7_links_all_contexts.csv` -> `Layer3_JcvPCA/outputs/poster_ready_evidence_package/nullspace_top7_links_all_contexts.csv`
- `nullspace_noise_vs_structure_diagnostic.csv` -> `Layer3_JcvPCA/outputs/poster_ready_evidence_package/nullspace_noise_vs_structure_diagnostic.csv`
- `body_region_anatomical_family_summary.csv` -> `Layer3_JcvPCA/outputs/poster_ready_evidence_package/body_region_anatomical_family_summary.csv`

## Column checks

| Table | Required columns | Missing |
| --- | --- | --- |
| Fig1 JRW audit | 3 checked | none |
| Fig1 | 11 checked | none |
| Fig2 | 6 checked | none |
| Fig3 family | 9 checked | none |
| Fig3 PC counts | 5 checked | none |
| Fig3 ratio | 7 checked | none |
| Fig4 | 8 checked | none |

## Row counts after filtering

| Subset | Rows |
| --- | --- |
| Fig1 T1_vs_T2 top links | 7 |
| Fig1 T1_vs_T3 top links | 7 |
| Fig2 timepoints | 3 |
| Fig3 family rows | 10 |
| Fig3 ratio timepoints | 3 |
| Fig4 family rows | 40 |

## Structural / sanity checks

| Figure | Check | Pass | Detail |
| --- | --- | --- | --- |
| Fig1 | NV_T1 denominator > 0 | YES | min NV_T1 = 0.00266 |
| Fig1 | delta_to_NV_T1_ratio = |delta| / NV_T1 | YES | max |recomputed - stored| = 0.0000 |
| Fig1 | outside-NV flag agrees with ratio>1 | YES | 0 rows disagree |
| Fig1 dist | T1_vs_T2 sum |delta| > 0 | YES | sum = 0.15606 |
| Fig1 dist | T1_vs_T3 sum |delta| > 0 | YES | sum = 0.16522 |
| Fig1 dist | T1_vs_T2 only in summary | YES | comparisons=['T1_vs_T2', 'T1_vs_T3'] |
| Fig1 dist | T1_vs_T3 only in summary | YES | comparisons=['T1_vs_T2', 'T1_vs_T3'] |
| Fig3 | functional_p50 family shares sum to 1 | YES | sum = 1.0000 |
| Fig3 | null_space_after_p50 family shares sum to 1 | YES | sum = 1.0000 |
| Fig3 | null/all ratios > 0 | YES | all plotted p50/p60 ratios positive |
| Fig4 | T1_vs_T2 functional_p50 shares sum to 1 | YES | sum = 1.0000 |
| Fig4 | T1_vs_T2 null_space_after_p50 shares sum to 1 | YES | sum = 1.0000 |
| Fig4 | T1_vs_T2 functional_p60 shares sum to 1 | YES | sum = 1.0000 |
| Fig4 | T1_vs_T2 null_space_after_p60 shares sum to 1 | YES | sum = 1.0000 |
| Fig4 | T1_vs_T3 functional_p50 shares sum to 1 | YES | sum = 1.0000 |
| Fig4 | T1_vs_T3 null_space_after_p50 shares sum to 1 | YES | sum = 1.0000 |
| Fig4 | T1_vs_T3 functional_p60 shares sum to 1 | YES | sum = 1.0000 |
| Fig4 | T1_vs_T3 null_space_after_p60 shares sum to 1 | YES | sum = 1.0000 |

## Expected-vs-actual value checks

| Figure | Item | Expected | Actual | Tol | Match |
| --- | --- | --- | --- | --- | --- |
| Fig1 | T1_vs_T2 RFArm_to_RHand signed | 0.039 | 0.039 | 0.001 | YES |
| Fig1 | T1_vs_T2 RFArm_to_RHand xNV | 3.619 | 3.619 | 0.01 | YES |
| Fig1 | T1_vs_T3 RFArm_to_RHand signed | 0.0417 | 0.0417 | 0.001 | YES |
| Fig1 | T1_vs_T2 RUArm_to_RFArm xNV | 8.717 | 8.7172 | 0.01 | YES |
| Fig1 dist | T1_vs_T2 Gini | 0.4755 | 0.4755 | 0.001 | YES |
| Fig1 dist | T1_vs_T3 Gini | 0.474 | 0.474 | 0.001 | YES |
| Fig1 dist | T1_vs_T2 Top-3 share | 0.5425 | 0.5425 | 0.001 | YES |
| Fig1 dist | T1_vs_T3 Top-3 share | 0.5448 | 0.5448 | 0.001 | YES |
| Fig2 | T1 mean_abs_delta | 0.012492 | 0.0125 | 0.0001 | YES |
| Fig2 | T1 gini | 0.536613 | 0.5366 | 0.0001 | YES |
| Fig2 | T2 mean_abs_delta | 0.01562 | 0.0156 | 0.0001 | YES |
| Fig2 | T2 gini | 0.563372 | 0.5634 | 0.0001 | YES |
| Fig2 | T3 mean_abs_delta | 0.01097 | 0.011 | 0.0001 | YES |
| Fig2 | T3 gini | 0.459186 | 0.4592 | 0.0001 | YES |
| Fig3 | 671 functional distal_upper_limb | 0.3545 | 0.3545 | 0.001 | YES |
| Fig3 | 671 functional shoulder_chain | 0.2633 | 0.2633 | 0.001 | YES |
| Fig3 | 671 null-space lower_limb | 0.344 | 0.344 | 0.001 | YES |
| Fig3 | 671 functional PCs | 3 | 3.0 | 0.5 | YES |
| Fig3 | 671 null-space PCs | 6 | 6.0 | 0.5 | YES |
| Fig3 | T1 null/all p50 | 1.475976 | 1.476 | 0.01 | YES |
| Fig3 | T1 null/all p60 | 1.895384 | 1.8954 | 0.01 | YES |
| Fig3 | T2 null/all p50 | 2.476922 | 2.4769 | 0.01 | YES |
| Fig3 | T2 null/all p60 | 2.476922 | 2.4769 | 0.01 | YES |
| Fig3 | T3 null/all p50 | 3.348045 | 3.348 | 0.01 | YES |
| Fig3 | T3 null/all p60 | 4.765013 | 4.765 | 0.01 | YES |
| Fig4 | T1_vs_T2 func p50 distal_upper_limb | 0.3545 | 0.3545 | 0.001 | YES |
| Fig4 | T1_vs_T2 null p50 lower_limb | 0.344 | 0.344 | 0.001 | YES |
| Fig4 | T1_vs_T2 null p60 lower_limb | 0.3191 | 0.3191 | 0.001 | YES |
| Fig4 | T1_vs_T3 null p50 shoulder_chain | 0.3191 | 0.3191 | 0.001 | YES |

Value checks matched: 29/29

## Notes (informational)

- Fig1 percentage-point conversion: NOT possible. Per-condition link JRW (RSS of PCA loadings) sums to ~2.46 per PC, not 1.0; JcvPCA link Δ is a raw B−A JRW difference, not a change in normalized link share. Multiplying by 100 would not yield valid percentage points of contribution.
- Fig1 T1_vs_T2 links shown: RFArm_to_RHand, RUArm_to_RFArm, LThigh_to_LShin, LShin_to_LFoot, RThigh_to_RShin, LShoulder_to_LUArm, RShin_to_RFoot
- Fig1 T1_vs_T3 links shown: RFArm_to_RHand, LThigh_to_LShin, LUArm_to_LFArm, RUArm_to_RFArm, RThigh_to_RShin, RShin_to_RFoot, LFArm_to_LHand
- Fig1 distribution T1_vs_T2: Gini=0.475, Top-3 share=54.2% (n=14 links; T1-referenced contrast only).
- Fig1 distribution T1_vs_T3: Gini=0.474, Top-3 share=54.5% (n=14 links; T1-referenced contrast only).
- Fig1 distribution inset uses T1_vs_T2 and T1_vs_T3 only; T2_vs_T3 is excluded because it uses a different JcvPCA reference space.
- Fig1 xNV denominator: NV_T1_abs_delta (T1_R1 vs T1_R2 repetition contrast, all-PC mean |JcvPCA_link| per link)
- Fig1 top-N per panel: 7
- Fig1 distribution computation: Per T1-referenced contrast: abs_delta=|longitudinal_delta|; link_change_share=abs_delta/sum(abs_delta); Gini(link_change_share); Top-3 share=sum of 3 largest link_change_share
- Fig3 null/all ratio: link-level variability in null-space (after p50/p60) divided by all-PC link variability at each within-timepoint R1–R2 contrast; >1 = later PCs carry disproportionate natural-variability magnitude.
- Fig3 family share: within each subspace, relative_family_share = family's sum |link Δ| / total |link Δ| across all links in that subspace.
