# Layer 3 JcvPCA Scope

## Purpose

Layer 3 implements a conservative adaptation of the JcvPCA computational framework from Dubois et al. to Gaga/OptiTrack/Motive-derived movement data.

The purpose is to compare changes in parent-child relative rotation-vector contribution structure between a reference condition A and comparison condition B.

Layer 3 does not perform raw marker QC, quaternion reconstruction, filtering, segmentation, or window selection. It consumes already prepared Layer 2.5 JcvPCA-ready matrices.

## Scientific framing

The analysis should be described as:

> JcvPCA-style comparison of Motive-derived parent-child relative rotation-vector contribution structure.

Do not describe the outputs as direct anatomical joint loading, muscle use, direct encoder joint angles, or proof of motor change.

Preferred interpretation language:

* increased contribution in B relative to A;
* decreased contribution in B relative to A;
* change beyond T1 repetition-level variability;
* within T1 repetition-level variability / inconclusive.

Avoid:

* statistically significant;
* proved change;
* no change;
* synchronization change;
* causal interpretation.

## Core reference implementation

The core JcvPCA computation should intentionally preserve the structure and logic of the paper's Python implementation.

Use the same core libraries:

```python
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
```

The central function should remain recognizable as the paper implementation:

1. build/concatenate dataset A;
2. center A independently;
3. fit PCA on A;
4. build/concatenate dataset B;
5. center B independently;
6. manually project B into A PCA space using matrix multiplication;
7. fit PCA on projected B;
8. re-express B loadings in the original feature space;
9. compute JcvPCA as `abs(B_reprojected_loadings) - abs(A_loadings)`.

Do not replace this with another PCA-comparison method.

## Layer 3 V1 scope

V1 should implement only Group 4 cross-repetition analysis.

Reference dataset:

```text
A_T1 = T1_P1_R1_Group4 + T1_P1_R2_Group4
```

Comparison datasets:

```text
B_T2 = T2_P1_R1_Group4 + T2_P1_R2_Group4
B_T3 = T3_P1_R1_Group4 + T3_P1_R2_Group4
```

Natural variability reference:

```text
NV_T1 = T1_P1_R1_Group4 vs T1_P1_R2_Group4
```

Do not implement in V1:

* Group 5;
* task-level analysis;
* JsvCRP;
* CRP;
* bootstrap statistics;
* cross-subject analysis;
* automatic segmentation;
* automatic clean-window selection;
* Euler features;
* omega features;
* position features;
* velocity features;
* z-scoring;
* variance normalization.

## Input contract

Layer 3 consumes Layer 2.5 exported window matrices.

Required metadata columns:

```text
session_id
run_label
frame
time_sec
```

Required feature columns:

```text
columns ending in _rx, _ry, _rz
```

The actual PCA matrix must use only `_rx`, `_ry`, `_rz` columns.

Metadata columns must not enter PCA.

Layer 3 must validate:

* feature columns are numeric;
* no NaNs;
* no infinite values;
* no constant feature columns;
* identical feature names across A/B matrices;
* identical feature order across A/B matrices;
* each joint-link unit has a complete rx/ry/rz triplet;
* enough rows exist for PCA;
* selected number of PCs is valid.

If validation fails, Layer 3 must stop and write a clear validation report. It must not silently repair data.

## Centering rule

Each feature column is centered independently.

Correct:

```python
A_centered = A - A.mean(axis=0)
B_centered = B - B.mean(axis=0)
```

Incorrect:

```python
B_centered = B - A.mean(axis=0)
```

Do not use `PCA_A.transform(B_raw)` because it applies A's fitted PCA mean to B. Manual projection must be used.

## Normalization rule

Do not z-score.

Do not divide by standard deviation.

Do not range-normalize.

JcvPCA should preserve natural amplitude differences between features.

## PC selection

For V1:

```text
selected_m = smallest number of PCs from A reaching 90% cumulative explained variance
```

PC selection must be based on A only.

Export explained variance ratios and cumulative explained variance.

## Axis-level JcvPCA

For each selected PC and each feature:

```python
JcvPCA_axis = abs(B_reprojected_loading) - abs(A_loading)
```

Positive values mean the feature contributed more in B relative to A.

Negative values mean the feature contributed less in B relative to A.

## Joint-link aggregation

Features are parent-child relative rotation-vector components.

Each joint-link unit is represented by three axes:

```text
J004_Neck_to_Head_rx
J004_Neck_to_Head_ry
J004_Neck_to_Head_rz
```

Joint-link aggregation must use root-sum-square, not simple sum:

```python
JRW_A_link = sqrt(A_rx^2 + A_ry^2 + A_rz^2)
JRW_B_link = sqrt(B_rx^2 + B_ry^2 + B_rz^2)
JcvPCA_link = JRW_B_link - JRW_A_link
```

This is a project-specific adaptation because the paper uses scalar joint variables, while this project uses 3D rotation-vector features.

## Outputs

Layer 3 should export:

```text
outputs/layer3_jcvpca/
├── validation_report.json
├── analysis_metadata.json
├── explained_variance.csv
├── jrw_axis.csv
├── jcvpca_axis.csv
├── jrw_link.csv
├── jcvpca_link.csv
├── natural_variability_t1.csv
└── interpretation_summary.md
```

Outputs should be concise and auditable.

## Implementation principle

Keep the implementation lean, readable, and scientifically conservative.

The core JcvPCA function should look close to the paper code.

Project-specific complexity should be isolated in input/output, validation, manifest handling, and link-level RSS aggregation.

---

# Phase 2 Amendment (G8) — Approved conservative statistical extension

**Status:** Documentation only. Approved as a *planned* extension; not yet implemented. No code changes accompany this amendment.
**Date:** 2026-07-01
**Governing plan:** [`PROGRAM_GUI_OPTIMIZATION_PLAN.md`](../../docs/research_recovery/PROGRAM_GUI_OPTIMIZATION_PLAN.md) — Sections 4, 12, 14 and roadmap phase G8.
**Purpose:** Remove the contradiction between the V1 scope above (which forbids statistical significance and bootstrap) and the new Phase-2 statistical plan, **without weakening the V1 boundaries**.

## V1 boundaries remain intact

Everything in the sections above still defines **V1**. This amendment does **not** change the V1 core: manual B-projection, independent per-dataset centering, no z-scoring / no normalization, RSS link aggregation, fail-fast validation, and the conservative interpretation vocabulary. V1 outputs continue to be produced and described exactly as specified above.

The V1 exclusion list ("Do not implement in V1: … bootstrap statistics …") stays correct **for V1**. The items below are explicitly **not part of V1**; they are approved only as the separate, later **Phase 2 / G8** layer.

## Not in V1 — approved for Phase 2 / G8

The following are **excluded from V1** and **approved as a conservative Phase-2 extension**, to be built only under roadmap phase **G8** after G1–G5:

1. **Statistical significance** — expressed only as *reliability relative to natural variability*, never as population significance.
2. **Bootstrap-based NV estimation** — temporal block / split-half resampling to build each participant's natural-variability reference distribution (autocorrelation-respecting; matched P-combination; matched frame count).
3. **BH-FDR flags** — Benjamini–Hochberg false-discovery-rate control within an explicitly declared family (links within one comparison × focus); reported as *flags*, not proof.
4. **Confidence intervals** — bootstrap percentile CIs reported alongside every effect.
5. **Null-calibration checks** — running the procedure on within-timepoint repeat comparisons (e.g. T1R1 vs T1R2) to confirm the reliable-flag rate ≈ alpha before any real comparison is trusted.
6. **Minimum-detectable-effect reporting** — per comparison, so null results remain interpretable rather than silently dropped.
7. **Agent-runnable statistical analysis** — declarative `analysis_request.yaml` requests (selected participants, P phases, session comparisons, accumulation mode, focus) executed automatically to produce per-participant and accumulated results.

## Conservative interpretation (preserved and extended)

Phase-2 outputs must preserve V1 caution and add the following framing rules:

- Results are **N-of-1, participant-level statistical evidence**, referenced to **each participant's own within-session natural variability**. Report participants (e.g. 671, 252) **separately**.
- **No cohort-level or population-level effects.** With the current design there is no valid cross-participant or population inference.
- **No psilocybin-specific conclusions before unblinding.** Describe results as kinematic-coordination change over time relative to natural variability, not as drug effects, until unblinding is complete and separately approved.
- Preferred phrasing: "**change beyond within-session variability (FDR q < threshold)**," "narrower NV-referenced interval," "consistent direction across P phases." Continue to **avoid**: "statistically significant" (unqualified), "proved change," "no change," causal or drug-attributed language.
- Accumulated multi-P evidence is described as **pooled-data JcvPCA plus direction-consistency / narrower NV-referenced interval**, never as independent-sample meta-analytic significance.

## Explicit connections (contradiction removed)

This amendment binds the Phase-2 statistics to the governing plan so scope and implementation stay consistent:

1. **Section 14 — Automated, agent-driven statistical analysis layer.** The full statistical design (NV reference distribution, per-unit test procedure, multi-level outputs, movement-organization metrics, Stage-1 robust set, validation, visualization) is defined there. This amendment authorizes it as an out-of-V1, Phase-2 capability.
2. **Section 4 — governed config thresholds / no hidden parameters.** Every statistical threshold (block size, `n_bootstrap`, `alpha`, `q_threshold`, NV-null method, PCA variance threshold, p50/p60) must live in `config/analysis_params.yaml` with the rich schema (value/default/range/meaning/gui_editable/invalidates). **No statistical constant may be hidden in Python.**
3. **Section 12 — modular segment / P-phase selection.** Statistical requests select P phases and combinations through the manifest-driven selection layer (no duplicated combined files); the exact resolved segment set is saved with each analysis.
4. **G8 roadmap phase.** Implementation occurs only under G8 (after G1–G5), read-only on the canonical batch, writing new timestamped outputs only, with the scope-doc amendment approved as the first G8 step.
5. **Reproducibility via snapshots.** Every statistical output must save a frozen config snapshot (Section 4.5) and the resolved `analysis_request.yaml`, with a config hash surfaced in the GUI ("generated with config hash X / current Y / comparable | not directly comparable"). Old statistical results stay bound to the snapshot that produced them and are never retroactively relabeled.

## Gating conditions before G8 outputs are reported

- This amendment is formally approved (sign-off recorded).
- Null-calibration (item 5) passes — flag rate ≈ alpha on within-timepoint repeat comparisons.
- N-of-1 framing and conservative language are enforced in every report.
- All statistical thresholds are config-governed and snapshotted.

Until G8 is implemented and these conditions are met, Layer 3 remains **V1-only** as specified in the sections above.
