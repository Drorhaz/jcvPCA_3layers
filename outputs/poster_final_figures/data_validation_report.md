# Poster Final Figures - Data Validation Report

**Final status: PASS**

Descriptive within-participant analysis; participants not pooled.

## Files used

- `longitudinal_delta_nv_ratio_by_link.csv` -> `Layer3_JcvPCA/outputs/poster_ready_evidence_package/longitudinal_delta_nv_ratio_by_link.csv`
- `body_region_anatomical_family_summary.csv` -> `Layer3_JcvPCA/outputs/poster_ready_evidence_package/body_region_anatomical_family_summary.csv`
- `nullspace_top7_links_all_contexts.csv` -> `Layer3_JcvPCA/outputs/poster_ready_evidence_package/nullspace_top7_links_all_contexts.csv`
- `natural_variability_scalar_poster_table.csv` -> `Layer3_JcvPCA/outputs/poster_ready_evidence_package/natural_variability_scalar_poster_table.csv`
- `concentration_metrics_all_analyses.csv` -> `Layer3_JcvPCA/outputs/poster_ready_evidence_package/concentration_metrics_all_analyses.csv`
- `directional_robustness_t1_t2_summary.csv` -> `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/directional_robustness_t1_t2_summary.csv`
- `directional_robustness_t1_t3_summary.csv` -> `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/directional_robustness_t1_t3_summary.csv`
- `directional_robustness_t2_t3_summary.csv` -> `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/directional_robustness_t2_t3_summary.csv`
- `direction_vs_magnitude_integrated_report.csv` -> `Layer3_JcvPCA/outputs/poster_ready_evidence_package/direction_vs_magnitude_integrated_report.csv`

## Column checks

| Table | Required columns | Missing |
| --- | --- | --- |
| Figure A | 11 checked | none |
| Figure B | 11 checked | none |
| Figure B (PC counts) | 5 checked | none |
| Figure C | 8 checked | none |
| Figure C (concentration) | 6 checked | none |
| Figure D summary (T1_vs_T2) | 4 checked | none |
| Figure D summary (T1_vs_T3) | 4 checked | none |
| Figure D summary (T2_vs_T3) | 4 checked | none |
| Figure D2 | 5 checked | none |

## Row counts after filtering

| Subset | Rows |
| --- | --- |
| A 671 T1_vs_T2 (top links shown) | 8 |
| A 671 T1_vs_T3 (top links shown) | 8 |
| B 671 families x subspaces | 10 |
| B 252 families x subspaces | 12 |
| D1 sign-agreement rows (focus=all) | 48 |

## Structural / sanity checks

| Figure | Check | Pass | Detail |
| --- | --- | --- | --- |
| A | NV_T1_abs_delta denominator > 0 | YES | min NV_T1_abs_delta = 0.00013 |
| A | delta_to_NV_T1_ratio = abs_delta / NV | YES | max |recomputed - stored| = 0.0000 |
| A | outside-NV flag agrees with ratio>1 | YES | 0 rows disagree |
| B | 671 functional_p50 family shares sum to 1 | YES | sum = 1.0000 |
| B | 671 null_space_after_p50 family shares sum to 1 | YES | sum = 1.0000 |
| B | 252 functional_p50 family shares sum to 1 | YES | sum = 1.0000 |
| B | 252 null_space_after_p50 family shares sum to 1 | YES | sum = 1.0000 |
| D1 | percent_sign_agreement on 0-100 scale | YES | observed range [14.3, 87.5] |

## Expected-vs-actual value checks

| Figure | Item | Expected | Actual | Tol | Match |
| --- | --- | --- | --- | --- | --- |
| A | 671 T1_vs_T2 RFArm_to_RHand abs_delta | 0.039 | 0.039 | 0.001 | YES |
| A | 671 T1_vs_T2 RFArm_to_RHand delta/NV | 3.619 | 3.619 | 0.01 | YES |
| A | 671 T1_vs_T2 RUArm_to_RFArm abs_delta | 0.0232 | 0.0232 | 0.001 | YES |
| A | 671 T1_vs_T2 RUArm_to_RFArm delta/NV | 8.7172 | 8.7172 | 0.01 | YES |
| A | 671 T1_vs_T2 LThigh_to_LShin abs_delta | 0.0225 | 0.0225 | 0.001 | YES |
| A | 671 T1_vs_T2 LThigh_to_LShin delta/NV | 1.9632 | 1.9632 | 0.01 | YES |
| A | 671 T1_vs_T3 RFArm_to_RHand abs_delta | 0.0417 | 0.0417 | 0.001 | YES |
| A | 671 T1_vs_T3 RFArm_to_RHand delta/NV | 3.874 | 3.874 | 0.01 | YES |
| A | 671 T1_vs_T3 LThigh_to_LShin abs_delta | 0.0304 | 0.0304 | 0.001 | YES |
| A | 671 T1_vs_T3 LThigh_to_LShin delta/NV | 2.6561 | 2.6561 | 0.01 | YES |
| B | 671 functional PCs | 3 | 3.0 | 0.5 | YES |
| B | 671 null-space PCs | 6 | 6.0 | 0.5 | YES |
| B | 252 functional PCs | 4 | 4.0 | 0.5 | YES |
| B | 252 null-space PCs | 6 | 6.0 | 0.5 | YES |
| B | 671 functional_p50 distal_upper_limb share | 0.3545 | 0.3545 | 0.001 | YES |
| B | 671 functional_p50 shoulder_chain share | 0.2633 | 0.2633 | 0.001 | YES |
| B | 671 null_space_after_p50 lower_limb share | 0.344 | 0.344 | 0.001 | YES |
| B | 252 functional_p50 proximal_upper_limb share | 0.3107 | 0.3107 | 0.001 | YES |
| B | 252 functional_p50 shoulder_chain share | 0.2781 | 0.2781 | 0.001 | YES |
| B | 252 null_space_after_p50 shoulder_chain share | 0.2953 | 0.2953 | 0.001 | YES |
| C | 671 T1 mean_abs_delta | 0.0125 | 0.0125 | 0.001 | YES |
| C | 671 T1 top3_share | 0.5956 | 0.5956 | 0.001 | YES |
| C | 671 T1 gini | 0.5366 | 0.5366 | 0.001 | YES |
| C | 671 T2 mean_abs_delta | 0.0156 | 0.0156 | 0.001 | YES |
| C | 671 T2 top3_share | 0.6114 | 0.6114 | 0.001 | YES |
| C | 671 T2 gini | 0.5634 | 0.5634 | 0.001 | YES |
| C | 671 T3 mean_abs_delta | 0.011 | 0.011 | 0.001 | YES |
| C | 671 T3 top3_share | 0.4701 | 0.4701 | 0.001 | YES |
| C | 671 T3 gini | 0.4592 | 0.4592 | 0.001 | YES |
| C | 252 T1 mean_abs_delta | 0.014 | 0.014 | 0.001 | YES |
| C | 252 T1 top3_share | 0.5832 | 0.5832 | 0.001 | YES |
| C | 252 T1 gini | 0.5867 | 0.5867 | 0.001 | YES |
| C | 252 T2 mean_abs_delta | 0.0072 | 0.0072 | 0.001 | YES |
| C | 252 T2 top3_share | 0.4348 | 0.4348 | 0.001 | YES |
| C | 252 T2 gini | 0.4646 | 0.4646 | 0.001 | YES |
| C | 252 T3 mean_abs_delta | 0.009 | 0.009 | 0.001 | YES |
| C | 252 T3 top3_share | 0.6184 | 0.6184 | 0.001 | YES |
| C | 252 T3 gini | 0.6244 | 0.6244 | 0.001 | YES |
| D1 | T1_vs_T2 overall median | 62.5 | 62.5 | 0.2 | YES |
| D1 | T1_vs_T2 P3 mean | 59.4 | 59.375 | 0.2 | YES |
| D1 | T1_vs_T2 all-block mean | 58.5 | 58.4821 | 0.2 | YES |
| D1 | T1_vs_T3 overall median | 53.1 | 53.125 | 0.2 | YES |
| D1 | T1_vs_T3 P3 mean | 60.2 | 60.1562 | 0.2 | YES |
| D1 | T1_vs_T3 all-block mean | 43.2 | 43.192 | 0.2 | YES |
| D1 | T2_vs_T3 overall median | 62.5 | 62.5 | 0.2 | YES |
| D1 | T2_vs_T3 P3 mean | 65.8 | 65.8482 | 0.2 | YES |
| D1 | T2_vs_T3 all-block mean | 59.6 | 59.5982 | 0.2 | YES |
| D2 | T1_vs_T2 low_magnitude_stable_direction | 9 | 9.0 | 0.5 | YES |
| D2 | T1_vs_T2 stable_magnitude_direction_sensitive | 11 | 11.0 | 0.5 | YES |
| D2 | T1_vs_T2 stable_magnitude_stable_direction | 5 | 5.0 | 0.5 | YES |
| D2 | T1_vs_T2 unstable_both | 5 | 5.0 | 0.5 | YES |
| D2 | T1_vs_T3 low_magnitude_stable_direction | 8 | 8.0 | 0.5 | YES |
| D2 | T1_vs_T3 stable_magnitude_direction_sensitive | 5 | 5.0 | 0.5 | YES |
| D2 | T1_vs_T3 stable_magnitude_stable_direction | 9 | 9.0 | 0.5 | YES |
| D2 | T1_vs_T3 unstable_both | 8 | 8.0 | 0.5 | YES |

Value checks matched: 55/55

## Notes (informational)

- A 671 T1_vs_T2 RUArm_to_RFArm: ratio 8.7x driven by small NV_T1_abs_delta = 0.00266 (abs_delta = 0.02316)
