# Figure 1 logic (participant 671, P3_P4_P5)

## Style
Matches `figure_A_longitudinal_shift_vs_NV.png` (lollipop layout): absolute stem
length, ratio-encoded dot colour, ± direction glyph, and `ratio× (NV value)` tip
labels. Participant 671 only; **T1-referenced panels only** (T1→T2, T1→T3).

## Purpose
Show which links changed, how large the change is, whether it exceeds T1
repetition variability, and whether change is concentrated or distributed across links.

## Main panels
- T1→T2 and T1→T3 (top 7 links per panel by |signed longitudinal Δ|)
- T2→T3 is **not** included (different JcvPCA reference space).

## Links shown (top 7 per panel)
- **T1→T2**: RFArm_to_RHand, RUArm_to_RFArm, LThigh_to_LShin, LShin_to_LFoot, RThigh_to_RShin, LShoulder_to_LUArm, RShin_to_RFoot
- **T1→T3**: RFArm_to_RHand, LThigh_to_LShin, LUArm_to_LFArm, RUArm_to_RFArm, RThigh_to_RShin, RShin_to_RFoot, LFArm_to_LHand

## Distribution inset (T1_vs_T2 and T1_vs_T3 only)
Within each T1-referenced contrast, Gini summarizes whether link-level change is
concentrated in a few links or distributed across links. Top-3 share indicates how
much of total |link Δ| is captured by the three most changing links.

**Computation (per contrast, all links in contrast):**
1. `abs_delta = |longitudinal_delta|`
2. `link_change_share = abs_delta / sum(abs_delta)` across all links
3. `Gini(link_change_share)` and `Top-3 share = sum of 3 largest link_change_share`

**Values plotted in inset:**
- **T1→T2**: Gini=0.475, Top-3 share=54.2% (n=14 links, sum |Δ|=0.1561)
- **T1→T3**: Gini=0.474, Top-3 share=54.5% (n=14 links, sum |Δ|=0.1652)

This is a **within-contrast** distribution summary only — not a direct shared-space
trajectory across sessions.

## X-axis (stem length)
- **Label:** Absolute longitudinal JcvPCA link Delta
- Absolute |longitudinal Δ|; direction shown by ± glyph left of zero.
- **Percentage-point conversion:** no
- **Reason:** Per-condition link JRW (RSS of PCA loadings) sums to ~2.46 per PC, not 1.0; JcvPCA link Δ is a raw B−A JRW difference, not a change in normalized link share. Multiplying by 100 would not yield valid percentage points of contribution.

## Dot colour and ring
- **Fill:** Δ / T1 NV ratio (yellow→red colorbar; clipped at 4×)
- **Thick dark ring:** ratio > 1 (outside T1 NV reference)
- **Thin grey ring:** ratio ≤ 1 (within T1 NV reference)

## Tip label
- **Format:** e.g. `3.6× (NV 0.011)`
- **Ratio:** |longitudinal_delta| / NV_T1_abs_delta
- **Denominator:** NV_T1_abs_delta (T1_R1 vs T1_R2 repetition contrast, all-PC mean |JcvPCA_link| per link)
- Descriptive reference only; not inferential significance.
