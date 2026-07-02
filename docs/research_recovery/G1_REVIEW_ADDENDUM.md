# G1 Review Addendum — Coverage, Badges, Invalidation, Variance Threshold

**Date:** 2026-07-01  
**Status:** Pre–G2 review (documentation + recommendations; no runner rewiring)  
**Related:** [`G1_THRESHOLD_INVENTORY.md`](G1_THRESHOLD_INVENTORY.md) · [`PROGRAM_GUI_OPTIMIZATION_PLAN.md`](PROGRAM_GUI_OPTIMIZATION_PLAN.md)

---

## 1. What G1 is (and is not)

G1 delivers a **governed initial threshold registry**, not a complete all-layer catalog.

| Coverage | Status |
|----------|--------|
| **Layer 3 (Gaga batch path)** | **Full** — all main batch constants mirrored in `config/analysis_params.yaml` and verified bit-for-bit against live Python |
| **Layer 1 QC** | **Curated subset** (5 of ~13 decision-relevant thresholds) — live values remain in `Layer1_motive_qc/motive_qc/config.yaml` |
| **Layer 2 kinematics** | **Curated subset** (4 of ~8) — live values remain in `Layer2_Motive_Kinematics/configs/default_layer2_config.yaml` |
| **Layer 2.5 export** | **Curated** (scope + severity lists) — logic partly in `warnings.py` |
| **G8 statistics** | **Not in G1** — planned under G8 / Phase-2 scope amendment |

**Runtime:** Layer runners still read their original sources (Option A federation). The registry is validated and ready for GUI display; wiring runners to it is a **post–G1-approval** step.

---

## 2. Scientific opinion — expand registry now vs G2 with curated subset?

### Recommendation: **Proceed to G2 with the curated registry, after a small G1.1 high-impact expansion (optional but recommended).**

Do **not** block G2 on full L1/L2 enumeration. Do **not** present G2 as if every L1/L2 knob is governed until G1.2.

### Why not wait for full enumeration?

- Full L1/L2 YAML mirroring is **documentation-heavy**, low immediate science risk if G2 is read-only and labels coverage.
- G2’s first pages (Overview, Data Readiness, Config view) need **structure and badges**, not 40+ thresholds on day one.
- L1/L2 thresholds are **already externalized** in layer YAML — they are not hidden in Python like L3 was.

### Which missing thresholds matter scientifically for downstream?

| Missing threshold (not in registry yet) | Downstream impact | Priority for registry |
|----------------------------------------|-------------------|------------------------|
| L1 gap tiers `max_missing_percent` (1 / 5 / 10%) | **High** — drives pass/warn/fail → export `qc_status`, Layer 3 inclusion | **Add before G2 Data Readiness** |
| L1 `max_large_gaps` per tier | **High** — same QC ladder | **Add** |
| L2 `rotvec.jump_warning_rad` (0.5) | **Medium** — soft flags before hard fail | Add in G1.2 |
| L2 `rotvec.near_pi_warning_fraction` | **Medium** — branch-cut warnings in windows | Add in G1.2 |
| L2 `quaternion_qc.warning_max_abs_norm_error` | **Medium** — early quaternion QC | Add in G1.2 |
| L2 `filtering.nyquist_safety_factor` | **Low** for GUI readiness | Defer |
| L1 `acceleration_percentile_threshold` | **Medium** — artifact flags overlap export warnings | Add in G1.2 |
| L1 `min_jump_distance_m`, `max_rigid_cv`, `peer_zscore_threshold` | **Medium** — artifact/swap detection | Defer unless QC page shows L1 detail |
| L1 `primary_report_thresholds_seconds` | **Low** — reporting bins only | Defer |
| L2.5 per-rule severity in `warnings.py` | **Medium** — explain *why* strong_warning | G1.2 as documented policy entries |

**Bottom line:** The thresholds that most affect **QC status → segmentation readiness → Layer 3 comparability** are **L1 missing-data tiers** and **L2 stage07/08 jump/mask settings**. If G2’s Data Readiness page shows traffic lights, add those **6–8 entries** in a quick **G1.1** config-only pass. Everything else can wait for **G1.2 full enumeration**.

---

## 3. Invalidation tags — review and proposed fix

### Problem

Today, `outputs.generate_full_numeric_reports` and `outputs.generate_poster_package` use `invalidates: []`, and there is no tag for **exported figures** under `results/poster/`. A threshold change can stale figures/reports without the GUI warning.

### Proposed invalidation taxonomy (G1.1)

| Tag | Meaning | GUI message |
|-----|---------|-------------|
| `layer1_qc` | Re-run L1 QC | "L1 QC may be stale" |
| `layer2` | Re-run L2 sessions | "L2 kinematics may be stale" |
| `layer2_5_exports` | Re-export segments | "L2.5 exports may be stale" |
| `layer3_batches` | New JcvPCA batch | "Layer 3 batch not comparable" |
| `decision_summaries` | Decision JSON/MD | "Decision summary may be stale" |
| `audit_reports` | Full-numeric / integrated MD audits | "Audit reports may be stale" |
| `poster_packages` | Poster evidence CSV package | "Poster evidence may be stale" |
| `exported_figures` | `results/poster/final_figures/` | "Figures may not match current config" |

### Proposed propagation rules

| Threshold class | Should invalidate |
|-----------------|-------------------|
| L1/L2/L2.5 QC | → exports → batches → decision → audit → poster → **figures** |
| L3 PCA / focus / weighting / blocks | → batches → decision → audit → poster → **figures** |
| Output `on_demand` toggles | → **audit_reports** / **poster_packages** / **exported_figures** (when set to regenerate) |
| GUI display-only | *(none)* |

### G2 behavior (read-only)

When displaying any artifact path, compute:

```text
artifact.config_hash  vs  current science_hash  →  comparable | not directly comparable
```

If `not directly comparable`, show which **invalidation tags** apply based on which threshold groups changed (L1 vs L3 vs output settings). No silent relabeling.

*Implementation note:* Canonical batch `193319` has **no** stored config hash today; G2 should show **"canonical batch: pre-registry (no config snapshot)"** until a promoted batch writes `_config_snapshot/`.

---

## 4. Variance threshold 0.80 vs scope 0.90 — explicit resolution

There are **four distinct concepts**; conflating them will confuse G2 badges.

| Concept | Value | Source of truth | Meaning |
|---------|-------|-----------------|---------|
| **Runtime / canonical batch** | **0.80** | `gaga_batch_runner.py`, `jcvpca_trace.py`, golden test, **frozen batch `193319`** | What actually produced poster-era and smoke results |
| **Registry `value` / `default`** | **0.80** | `config/analysis_params.yaml` | Mirrors runtime until rewiring |
| **Scope-approved (V1 narrative)** | **0.90** | `Layer3_JcvPCA/docs/LAYER3_SCOPE.md` § PC selection | Documented V1 *intent* for generic Layer 3 / manifest runner |
| **V1 manifest runner config** | **0.90** | `Layer3_JcvPCA/config/layer3_config.yaml` | Separate code path (`run_layer3_jcvpca.py`), **not** Gaga batch |

**This is not a G1 bug.** It is a **pre-existing split** between:

1. **Gaga batch / workbench path** (operational, canonical) → **0.80**
2. **V1 manifest runner + scope doc text** → **0.90**

### Recommended resolution (before G2 badges)

1. **Do not change runtime to 0.90** without a new timestamped batch and scientific sign-off.
2. **Registry** carries explicit metadata on `pca.variance_threshold`:
   - `value` / `default` = **0.80** (runtime)
   - `scope_approved_value` = **0.90**
   - `canonical_batch_value` = **0.80**
3. **G2 badges** show all three labels where relevant; flag **"scope narrative differs from runtime/canonical"** when scope ≠ runtime.
4. **Follow-up doc fix (separate approval):** Amend `LAYER3_SCOPE.md` V1 PC section to state that the **Gaga batch path uses 0.80** operationally while the V1 manifest runner default remains 0.90 — or harmonize to one value via a scoped scientific decision.

Until that scope edit, treat **0.80 as authoritative for Gaga/canonical** and **0.90 as scope/manifest-runner reference only**.

---

## 5. G2 badge / status model (read-only)

Each threshold row in the Config page should expose:

| Badge / field | Source | Display rule |
|---------------|--------|--------------|
| **Current value** | `threshold.value` in registry | Always show |
| **Default value** | `threshold.default` | Show; badge **differs from default** if `value ≠ default` |
| **Canonical value** | `canonical_batch_value` if present, else "unknown (no snapshot)" | For L3 params tied to batch `193319` |
| **Scope-approved value** | `scope_approved_value` if present | Show when ≠ runtime; badge **scope ≠ runtime** |
| **Scope-locked** | `locked_by_scope: true` | Lock icon; not editable in G2 |
| **Requires approval** | `requires_approval: true` | Warning icon (informational in G2; enforced in G6) |
| **GUI-editable** | `gui_editable: true/false` | G2: read-only regardless; icon hints future G6 |
| **Invalidates** | `invalidates[]` | Expandable list of output classes |
| **Coverage** | layer + `source_config` | **Partial registry** badge on L1/L2 rows not yet mirrored |

### Artifact-level banner (Results / Reports / Poster pages in G2+)

```text
Generated with config hash:     <artifact hash or "pre-registry">
Current registry science hash:  <science_hash>
Status: comparable | not directly comparable | unknown (no snapshot)

If not comparable, affected output classes: layer3_batches, decision_summaries, …
```

### Page-level coverage banner (Config / Data Readiness)

```text
Registry coverage: Layer 3 full | Layer 1 curated (5/N) | Layer 2 curated (4/N) | Layer 2.5 curated
Live runners may read additional thresholds from layer YAML not shown here.
```

---

## 6. Recommendation before G2

| Option | Verdict |
|--------|---------|
| **Block G2 until full L1/L2 enumeration** | **No** — delays GUI value; L1/L2 already in YAML |
| **Block G2 until G1.1 high-impact QC thresholds added** | **Optional but recommended** (~6–8 entries, config-only) |
| **Proceed to G2 read-only with curated registry + coverage banners** | **Yes** — with badges in §5 and variance resolution in §4 |

**Suggested sequence:**

1. Accept G1 as **initial registry** (wording updated).
2. *(Optional, 1–2 hours)* **G1.1** — add L1 gap tiers + L2 jump/mask thresholds; extend invalidation tags (`audit_reports`, `exported_figures`).
3. **G2** — read-only Overview, Data Readiness, Config/Thresholds with coverage + scope/canonical/runtime badges; **no runner rewiring**.

---

*Addendum for G1 approval gate — no analysis runs, no canonical batch changes.*
