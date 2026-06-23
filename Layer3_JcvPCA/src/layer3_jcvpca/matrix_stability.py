"""Matrix Stability / PCA Readiness checks for Layer 3 JcvPCA.

Evaluates whether a numeric feature matrix is suitable for PCA/JcvPCA.
This is distinct from Layer 1/2 QC (gaps, artifacts, masks).

Matrix stability does not prove scientific truth; it indicates numerical
suitability and whether the reference PCA space appears fragile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from layer3_jcvpca.io import build_joint_link_map, infer_feature_columns


@dataclass
class MatrixStabilityParams:
    check_matrix_stability: bool = True
    near_zero_variance_threshold: float = 1e-8
    rank_tolerance: float = 1e-10
    min_frames_required: int = 10
    min_frames_per_feature_ratio: float = 5.0
    condition_number_warning_threshold: float = 1e8
    pc_dominance_warning_threshold: float = 0.80
    split_half_stability_check: bool = True
    split_half_n_components: int | None = None
    split_half_similarity_warning_threshold: float = 0.85


@dataclass
class MatrixStabilityResult:
    role: str
    status: str  # pass | warning | blocking
    metrics: dict[str, Any] = field(default_factory=dict)
    findings: list[dict[str, str]] = field(default_factory=list)
    feature_variance_table: pd.DataFrame | None = None
    joint_variance_table: pd.DataFrame | None = None
    singular_value_table: pd.DataFrame | None = None
    split_half_table: pd.DataFrame | None = None


def _motion_energy_timeline(df: pd.DataFrame, feature_names: list[str]) -> np.ndarray:
    """Per-frame sum of squared feature values (exploratory motion-energy proxy)."""
    return np.sum(df[feature_names].to_numpy(dtype=float) ** 2, axis=1)


def _qc_burden_from_manifest(manifest: dict | None) -> dict[str, float]:
    if not manifest:
        return {
            "stage07_flagged_frame_burden": np.nan,
            "stage08_ineligible_frame_burden": np.nan,
            "layer1_warning_burden": np.nan,
        }
    burdens = {
        "stage07_flagged_frame_burden": 0.0,
        "stage08_ineligible_frame_burden": 0.0,
        "layer1_warning_burden": 0.0,
    }
    for w in manifest.get("warnings", []):
        wid = str(w.get("warning_id", ""))
        msg = str(w.get("message", ""))
        if "stage07" in wid.lower() or "stage 07" in msg.lower():
            burdens["stage07_flagged_frame_burden"] = 1.0
        if "stage08" in wid.lower() or "stage 08" in msg.lower():
            burdens["stage08_ineligible_frame_burden"] = 1.0
        if "layer1" in wid.lower() or w.get("category") == "layer1_evidence":
            burdens["layer1_warning_burden"] = 1.0
    ws = manifest.get("warnings_summary", {})
    n_frames = max(int(manifest.get("n_frames", manifest.get("jvcpca_matrix_row_count", 1))), 1)
    if ws.get("n_strong_warning", 0) or ws.get("n_warning", 0):
        burdens["layer1_warning_burden"] = max(
            burdens["layer1_warning_burden"],
            float(ws.get("n_strong_warning", 0) + ws.get("n_warning", 0)) / n_frames,
        )
    return burdens


def _split_half_stability(
    centered: np.ndarray,
    n_components: int,
    params: MatrixStabilityParams,
) -> dict[str, Any]:
    n_rows = centered.shape[0]
    if n_rows < 2 * params.min_frames_required:
        return {
            "split_half_enabled": True,
            "split_half_available": False,
            "split_half_reason": "insufficient_frames_for_split_half",
        }
    mid = n_rows // 2
    h1, h2 = centered[:mid], centered[mid:]
    k = n_components
    if params.split_half_n_components is not None:
        k = min(params.split_half_n_components, centered.shape[1], mid)
    k = max(1, k)
    pca1 = PCA(n_components=k).fit(h1)
    pca2 = PCA(n_components=k).fit(h2)
    v1 = np.abs(pca1.components_[0])
    v2 = np.abs(pca2.components_[0])
    denom = np.linalg.norm(v1) * np.linalg.norm(v2)
    pc_sim = float(np.dot(v1, v2) / denom) if denom > 0 else 0.0
    ev_diff = float(np.abs(pca1.explained_variance_ratio_[0] - pca2.explained_variance_ratio_[0]))
    return {
        "split_half_enabled": True,
        "split_half_available": True,
        "split_half_pc_similarity": pc_sim,
        "split_half_subspace_similarity": pc_sim,
        "split_half_variance_profile_difference": ev_diff,
    }


def assess_matrix_stability(
    df: pd.DataFrame,
    role: str,
    *,
    params: MatrixStabilityParams | None = None,
    manifest: dict | None = None,
    is_reference: bool = False,
) -> MatrixStabilityResult:
    """Compute matrix stability metrics and classify pass/warning/blocking."""
    params = params or MatrixStabilityParams()
    findings: list[dict[str, str]] = []
    status = "pass"

    def add(severity: str, code: str, message: str) -> None:
        nonlocal status
        findings.append({"severity": severity, "code": code, "message": message})
        if severity == "blocking":
            status = "blocking"
        elif severity == "warning" and status != "blocking":
            status = "warning"

    feature_names = infer_feature_columns(df)
    n_frames = len(df)
    n_features = len(feature_names)
    f2f = n_frames / n_features if n_features else 0.0

    nan_count = int(df[feature_names].isna().to_numpy().sum()) if feature_names else 0
    inf_count = int(np.isinf(df[feature_names].to_numpy()).sum()) if feature_names else 0

    if nan_count > 0:
        add("blocking", "nan_in_features", f"{nan_count} NaN value(s) in feature columns.")
    if inf_count > 0:
        add("blocking", "inf_in_features", f"{inf_count} infinite value(s) in feature columns.")

    for col in feature_names:
        if not pd.api.types.is_numeric_dtype(df[col]):
            add("blocking", "non_numeric_feature", f"Non-numeric feature column: {col}.")

    if n_frames < params.min_frames_required:
        add(
            "blocking",
            "too_few_frames",
            f"n_frames={n_frames} < min_frames_required={params.min_frames_required}.",
        )

    if feature_names:
        variances = df[feature_names].var(axis=0, ddof=0).to_numpy(dtype=float)
    else:
        variances = np.array([])

    total_variance = float(np.sum(variances)) if len(variances) else 0.0
    if feature_names and total_variance <= 0:
        add("blocking", "zero_total_variance", "Total feature variance is zero.")

    nz_mask = variances <= params.near_zero_variance_threshold if len(variances) else np.array([])
    nz_count = int(np.sum(nz_mask))
    nz_pct = 100.0 * nz_count / n_features if n_features else 0.0

    if nz_count > 0:
        add(
            "warning",
            "near_zero_variance_features",
            f"{nz_count} feature(s) ({nz_pct:.1f}%) have variance <= {params.near_zero_variance_threshold}.",
        )

    if f2f < params.min_frames_per_feature_ratio and n_features > 0:
        add(
            "warning",
            "low_frame_to_feature_ratio",
            f"frame_to_feature_ratio={f2f:.1f} < {params.min_frames_per_feature_ratio}.",
        )

    rank = 0
    cond = np.nan
    singular_values: list[float] = []
    dominant_pc = np.nan
    n80 = n90 = n95 = 0
    joint_var_rows: list[dict] = []
    motion_energy: np.ndarray | None = None

    if feature_names and nan_count == 0 and inf_count == 0 and total_variance > 0:
        X = df[feature_names].to_numpy(dtype=float)
        centered = X - X.mean(axis=0)
        motion_energy = _motion_energy_timeline(df, feature_names)

        try:
            _u, s, _vt = np.linalg.svd(centered, full_matrices=False)
            singular_values = s.tolist()
            rank = int(np.sum(s > params.rank_tolerance * s[0])) if len(s) else 0
            if rank == 0:
                add("blocking", "matrix_rank_zero", "Effective matrix rank is zero.")
            elif rank < n_features * 0.5:
                add(
                    "warning",
                    "low_rank",
                    f"matrix_rank={rank} is much smaller than n_features={n_features}.",
                )
            if len(s) > 0 and s[-1] > 0:
                cond = float(s[0] / s[-1])
                if cond > params.condition_number_warning_threshold:
                    add(
                        "warning",
                        "high_condition_number",
                        f"condition_number={cond:.2e} exceeds threshold.",
                    )
        except Exception as exc:
            add("warning", "svd_failed", f"SVD failed: {exc}")

        max_comp = min(n_frames, n_features)
        if max_comp >= 1:
            pca_full = PCA(n_components=max_comp)
            pca_full.fit(centered)
            evr = pca_full.explained_variance_ratio_
            if len(evr):
                dominant_pc = float(evr[0])
                if dominant_pc >= params.pc_dominance_warning_threshold:
                    add(
                        "warning",
                        "dominant_first_pc",
                        f"PC1 explains {dominant_pc:.1%} of variance (>= {params.pc_dominance_warning_threshold:.0%}).",
                    )
                cum = np.cumsum(evr)
                n80 = int(np.searchsorted(cum, 0.80) + 1)
                n90 = int(np.searchsorted(cum, 0.90) + 1)
                n95 = int(np.searchsorted(cum, 0.95) + 1)

        link_map = build_joint_link_map(feature_names)
        fi = {f: i for i, f in enumerate(feature_names)}
        for link, axes in link_map.items():
            idx = [fi[axes[a]] for a in ("rx", "ry", "rz")]
            jvar = float(np.sum(variances[idx]))
            parent, child = link.split("_to_", 1) if "_to_" in link else (link, "")
            joint_var_rows.append(
                {
                    "link_id": link,
                    "canonical_link_name": f"{parent}->{child}" if child else link,
                    "joint_variance": jvar,
                }
            )

    from layer3_jcvpca.identity import parse_canonical_feature

    feature_var_df = pd.DataFrame({"feature_name": feature_names, "variance": variances})
    if not feature_var_df.empty:
        for key in ("canonical_link_name", "parent_canonical", "child_canonical", "axis"):
            feature_var_df[key] = [
                parse_canonical_feature(f)[key] for f in feature_var_df["feature_name"]
            ]

    joint_var_df = pd.DataFrame(joint_var_rows)
    sv_df = pd.DataFrame({"index": range(len(singular_values)), "singular_value": singular_values})

    split_metrics: dict[str, Any] = {"split_half_enabled": params.split_half_stability_check}
    split_df = None
    if (
        params.split_half_stability_check
        and feature_names
        and nan_count == 0
        and total_variance > 0
        and n_frames >= params.min_frames_required
    ):
        X = df[feature_names].to_numpy(dtype=float)
        centered = X - X.mean(axis=0)
        k = min(n90 if n90 else 2, n_features, n_frames // 2)
        sh = _split_half_stability(centered, k, params)
        split_metrics.update(sh)
        if sh.get("split_half_available") and sh.get(
            "split_half_pc_similarity", 1
        ) < params.split_half_similarity_warning_threshold:
            add(
                "warning",
                "split_half_instability",
                f"Split-half PC similarity={sh['split_half_pc_similarity']:.3f} "
                f"< {params.split_half_similarity_warning_threshold}.",
            )
        split_df = pd.DataFrame([{"role": role, **split_metrics}])
    elif params.split_half_stability_check:
        split_metrics["split_half_available"] = False
        split_metrics["split_half_reason"] = "prerequisites_not_met"
        split_df = pd.DataFrame([{"role": role, **split_metrics}])

    qc_burden = _qc_burden_from_manifest(manifest)
    if qc_burden.get("stage07_flagged_frame_burden", 0) > 0:
        add("warning", "stage07_burden", "Stage 07 jump-fail flags reported in manifest.")
    if qc_burden.get("stage08_ineligible_frame_burden", 0) > 0:
        add("warning", "stage08_burden", "Stage 08 masked/ineligible frames reported in manifest.")
    if qc_burden.get("layer1_warning_burden", 0) > 0:
        add("warning", "layer1_burden", "Layer 1 evidence warnings reported in manifest.")

    metrics = {
        "role": role,
        "is_reference": is_reference,
        "n_frames": n_frames,
        "n_features": n_features,
        "frame_to_feature_ratio": round(f2f, 3),
        "numeric_completeness": 1.0 if nan_count == 0 and inf_count == 0 else 0.0,
        "nan_count": nan_count,
        "inf_count": inf_count,
        "total_variance": total_variance,
        "near_zero_variance_feature_count": nz_count,
        "near_zero_variance_feature_percent": round(nz_pct, 2),
        "feature_variance_min": float(np.min(variances)) if len(variances) else np.nan,
        "feature_variance_median": float(np.median(variances)) if len(variances) else np.nan,
        "feature_variance_max": float(np.max(variances)) if len(variances) else np.nan,
        "matrix_rank": rank,
        "rank_fraction": round(rank / n_features, 3) if n_features else np.nan,
        "condition_number": cond,
        "dominant_pc_variance_percent": round(dominant_pc * 100, 2)
        if not np.isnan(dominant_pc)
        else np.nan,
        "n_pcs_for_80_percent_variance": n80,
        "n_pcs_for_90_percent_variance": n90,
        "n_pcs_for_95_percent_variance": n95,
        "motion_energy_mean": float(np.mean(motion_energy)) if motion_energy is not None else np.nan,
        "motion_energy_max": float(np.max(motion_energy)) if motion_energy is not None else np.nan,
        **qc_burden,
        **split_metrics,
        "stability_verdict": status,
    }

    return MatrixStabilityResult(
        role=role,
        status=status,
        metrics=metrics,
        findings=findings,
        feature_variance_table=feature_var_df,
        joint_variance_table=joint_var_df,
        singular_value_table=sv_df,
        split_half_table=split_df,
    )


def assess_all_matrices(
    matrices: dict[str, pd.DataFrame],
    *,
    params: MatrixStabilityParams | None = None,
    manifests: dict[str, dict | None] | None = None,
) -> dict[str, MatrixStabilityResult]:
    """Assess A, B, NV_A, NV_B. Emphasizes A as reference."""
    params = params or MatrixStabilityParams()
    manifests = manifests or {}
    results = {}
    for role, df in matrices.items():
        is_ref = role == "A"
        results[role] = assess_matrix_stability(
            df,
            role,
            params=params,
            manifest=manifests.get(role),
            is_reference=is_ref,
        )
    return results


def combined_stability_status(results: dict[str, MatrixStabilityResult]) -> str:
    if any(r.status == "blocking" for r in results.values()):
        return "blocking"
    if any(r.status == "warning" for r in results.values()):
        return "warning"
    return "pass"
