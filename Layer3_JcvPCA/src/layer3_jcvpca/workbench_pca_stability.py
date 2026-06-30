"""PCA Stability / Readiness checks for Gaga workbench Phase 7.

Evaluates centered Dataset A (reference) and centered Dataset B (comparison)
before B projection. Uses numerical readiness language only: pass / warning / blocking.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from layer3_jcvpca.jcvpca_trace import PcaATrace, SELECTED_M_MODE_AUTO
from layer3_jcvpca.matrix_stability import MatrixStabilityParams, _split_half_stability


@dataclass
class WorkbenchPcaStabilityResult:
    role: str
    status: str
    metrics: dict[str, Any] = field(default_factory=dict)
    findings: list[dict[str, str]] = field(default_factory=list)
    near_zero_variance_features: pd.DataFrame = field(default_factory=pd.DataFrame)
    singular_values: pd.DataFrame = field(default_factory=pd.DataFrame)
    split_half: pd.DataFrame = field(default_factory=pd.DataFrame)
    pca_reference_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkbenchPcaStabilityBundle:
    a: WorkbenchPcaStabilityResult
    b: WorkbenchPcaStabilityResult
    combined_status: str = "pass"
    can_continue_to_phase8: bool = False
    requires_acknowledgment: bool = False
    warnings_acknowledged: bool = False


def _feature_matrix(centered: pd.DataFrame, feature_names: list[str]) -> np.ndarray:
    return centered[feature_names].to_numpy(dtype=float)


def assess_workbench_centered_stability(
    centered: pd.DataFrame,
    feature_names: list[str],
    role: str,
    *,
    params: MatrixStabilityParams | None = None,
    is_reference: bool = False,
    pca_trace: PcaATrace | None = None,
) -> WorkbenchPcaStabilityResult:
    """Assess PCA readiness on an already-centered feature matrix."""
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

    n_rows = len(centered)
    n_features = len(feature_names)
    rows_to_features_ratio = n_rows / n_features if n_features else 0.0
    X = _feature_matrix(centered, feature_names)

    nan_count = int(np.isnan(X).sum())
    inf_count = int(np.isinf(X).sum())
    if nan_count > 0:
        add("blocking", "nan_in_features", f"{nan_count} NaN value(s) in feature columns.")
    if inf_count > 0:
        add("blocking", "inf_in_features", f"{inf_count} infinite value(s) in feature columns.")

    for col in feature_names:
        if not pd.api.types.is_numeric_dtype(centered[col]):
            add("blocking", "non_numeric_feature", f"Non-numeric feature column: {col}.")

    if n_rows < params.min_frames_required:
        add(
            "blocking",
            "too_few_frames",
            f"n_rows={n_rows} < min_frames_required={params.min_frames_required}.",
        )

    variances = centered[feature_names].var(axis=0, ddof=0).to_numpy(dtype=float)
    total_variance = float(np.sum(variances)) if len(variances) else 0.0
    if n_features and total_variance <= 0:
        add("blocking", "zero_total_variance", "Total feature variance is zero.")

    zero_mask = variances == 0.0
    zero_count = int(np.sum(zero_mask))
    if zero_count > 0:
        add("blocking", "zero_variance_features", f"{zero_count} feature(s) have exactly zero variance.")

    nz_mask = variances <= params.near_zero_variance_threshold
    nz_count = int(np.sum(nz_mask))
    nz_pct = 100.0 * nz_count / n_features if n_features else 0.0
    if nz_count > 0 and zero_count == 0:
        add(
            "warning",
            "near_zero_variance_features",
            f"{nz_count} feature(s) ({nz_pct:.1f}%) have variance <= {params.near_zero_variance_threshold}.",
        )

    if rows_to_features_ratio < params.min_frames_per_feature_ratio and n_features > 0:
        add(
            "warning",
            "low_rows_to_features_ratio",
            f"rows_to_features_ratio={rows_to_features_ratio:.1f} < {params.min_frames_per_feature_ratio}.",
        )

    rank = 0
    rank_deficiency = n_features
    cond = np.nan
    singular_values: list[float] = []
    dominant_pc = np.nan
    pca_fit_success = False
    pca_fit_message = "PCA fit not attempted."

    if n_features and nan_count == 0 and inf_count == 0 and total_variance > 0:
        try:
            _u, s, _vt = np.linalg.svd(X, full_matrices=False)
            singular_values = s.tolist()
            rank = int(np.sum(s > params.rank_tolerance * s[0])) if len(s) else 0
            rank_deficiency = max(n_features - rank, 0)
            if rank == 0:
                add("blocking", "matrix_rank_zero", "Effective matrix rank is zero.")
            elif rank < n_features:
                add(
                    "warning",
                    "rank_deficiency",
                    f"rank_deficiency={rank_deficiency} (matrix_rank={rank}, n_features={n_features}).",
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

        max_comp = min(n_rows, n_features)
        if max_comp >= 1:
            try:
                pca_full = PCA(n_components=max_comp)
                pca_full.fit(X)
                pca_fit_success = True
                pca_fit_message = "PCA fit succeeded on centered matrix."
                evr = pca_full.explained_variance_ratio_
                if len(evr):
                    dominant_pc = float(evr[0])
                    if dominant_pc >= params.pc_dominance_warning_threshold:
                        add(
                            "warning",
                            "dominant_first_pc",
                            f"PC1 explains {dominant_pc:.1%} of variance (>= {params.pc_dominance_warning_threshold:.0%}).",
                        )
            except Exception as exc:
                pca_fit_success = False
                pca_fit_message = f"PCA fit failed: {exc}"
                add("blocking", "pca_fit_failed", pca_fit_message)
        else:
            pca_fit_message = "Insufficient rows/features for PCA fit."
            add("blocking", "pca_fit_failed", pca_fit_message)

    near_zero = pd.DataFrame(
        {
            "feature_column": [feature_names[i] for i in np.where(nz_mask)[0]],
            "variance": variances[nz_mask],
        }
    )

    sv_df = pd.DataFrame({"index": range(len(singular_values)), "singular_value": singular_values})

    split_metrics: dict[str, Any] = {"split_half_enabled": params.split_half_stability_check}
    split_df = pd.DataFrame()
    if params.split_half_stability_check and pca_fit_success and n_rows >= params.min_frames_required:
        k = min(10, n_features, n_rows // 2)
        sh = _split_half_stability(X, k, params)
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

    metrics: dict[str, Any] = {
        "role": role,
        "is_reference": is_reference,
        "dataset_label": "reference_pca_frame" if is_reference else "comparison_matrix",
        "n_rows": n_rows,
        "n_features": n_features,
        "rows_to_features_ratio": round(rows_to_features_ratio, 3),
        "matrix_rank": rank,
        "rank_deficiency": rank_deficiency,
        "condition_number": cond,
        "dominant_pc_variance_percent": round(dominant_pc * 100, 2) if not np.isnan(dominant_pc) else np.nan,
        "near_zero_variance_feature_count": nz_count,
        "zero_variance_feature_count": zero_count,
        "nan_count": nan_count,
        "inf_count": inf_count,
        "pca_fit_success": pca_fit_success,
        "pca_fit_message": pca_fit_message,
        "stability_status": status,
        **split_metrics,
    }

    pca_reference_fields: dict[str, Any] = {}
    if is_reference and pca_trace is not None:
        params_a = pca_trace.parameters
        raw_m = int(
            np.searchsorted(
                pca_trace.cumulative_variance["cumulative_explained_variance"].to_numpy(),
                params_a.variance_threshold,
            )
            + 1
        )
        raw_m = min(raw_m, min(n_rows, n_features))
        clamp_warning = ""
        if params_a.selected_m_mode == SELECTED_M_MODE_AUTO and raw_m != pca_trace.selected_m:
            clamp_warning = (
                f"selected_m={pca_trace.selected_m} differs from variance-only choice m={raw_m} "
                f"due to min_pcs={params_a.min_pcs} / max_pcs={params_a.max_pcs} bounds."
            )
            add("warning", "selected_m_clamped", clamp_warning)

        pca_reference_fields = {
            "selected_m": pca_trace.selected_m,
            "selected_m_reason": pca_trace.selected_m_reason,
            "selected_m_clamp_warning": clamp_warning or None,
            "variance_threshold": params_a.variance_threshold,
            "cumulative_variance_at_selected_m": float(
                pca_trace.cumulative_variance.iloc[pca_trace.selected_m - 1][
                    "cumulative_explained_variance"
                ]
            ),
            "explained_variance_artifact": "pca_A_explained_variance.csv",
            "cumulative_variance_artifact": "pca_A_cumulative_variance.csv",
        }
        metrics.update(pca_reference_fields)

    metrics["stability_status"] = status

    return WorkbenchPcaStabilityResult(
        role=role,
        status=status,
        metrics=metrics,
        findings=findings,
        near_zero_variance_features=near_zero,
        singular_values=sv_df,
        split_half=split_df,
        pca_reference_fields=pca_reference_fields,
    )


def assess_workbench_pca_stability_pair(
    centered_a: pd.DataFrame,
    centered_b: pd.DataFrame,
    feature_names: list[str],
    pca_trace: PcaATrace,
    *,
    params: MatrixStabilityParams | None = None,
) -> WorkbenchPcaStabilityBundle:
    """Assess centered A (reference) and B (comparison diagnostic only)."""
    params = params or MatrixStabilityParams()
    a = assess_workbench_centered_stability(
        centered_a,
        feature_names,
        "A",
        params=params,
        is_reference=True,
        pca_trace=pca_trace,
    )
    b = assess_workbench_centered_stability(
        centered_b,
        feature_names,
        "B",
        params=params,
        is_reference=False,
        pca_trace=None,
    )
    if a.status == "blocking" or b.status == "blocking":
        combined = "blocking"
    elif a.status == "warning" or b.status == "warning":
        combined = "warning"
    else:
        combined = "pass"

    return WorkbenchPcaStabilityBundle(
        a=a,
        b=b,
        combined_status=combined,
        can_continue_to_phase8=combined == "pass",
        requires_acknowledgment=combined == "warning",
    )


def build_stability_report_rows(result: WorkbenchPcaStabilityResult) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for finding in result.findings:
        rows.append(
            {
                "role": result.role,
                "check_id": finding["code"],
                "severity": finding["severity"],
                "status": finding["severity"],
                "message": finding["message"],
            }
        )
    for key in (
        "n_rows",
        "n_features",
        "rows_to_features_ratio",
        "matrix_rank",
        "rank_deficiency",
        "condition_number",
        "dominant_pc_variance_percent",
        "near_zero_variance_feature_count",
        "zero_variance_feature_count",
        "nan_count",
        "inf_count",
        "pca_fit_success",
        "split_half_pc_similarity",
    ):
        if key in result.metrics:
            rows.append(
                {
                    "role": result.role,
                    "check_id": key,
                    "severity": "info",
                    "status": result.status,
                    "message": f"{key}={result.metrics[key]}",
                }
            )
    if result.pca_reference_fields:
        for key, value in result.pca_reference_fields.items():
            rows.append(
                {
                    "role": result.role,
                    "check_id": key,
                    "severity": "info",
                    "status": result.status,
                    "message": f"{key}={value}",
                }
            )
    return pd.DataFrame(rows)


def load_pca_stability_acknowledgment(output_dir: Path | str) -> bool:
    path = Path(output_dir) / "pca_stability_acknowledgment.json"
    if not path.is_file():
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    return bool(payload.get("warnings_acknowledged"))


def save_pca_stability_acknowledgment(
    output_dir: Path | str,
    *,
    acknowledged: bool,
    combined_summary: dict[str, Any] | None = None,
) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "pca_stability_acknowledgment.json"
    payload = {
        "warnings_acknowledged": acknowledged,
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
        "combined_status": (combined_summary or {}).get("combined_status"),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    combined_path = root / "pca_stability_combined_summary.json"
    if combined_path.is_file():
        combined = json.loads(combined_path.read_text(encoding="utf-8"))
        combined["warnings_acknowledged"] = acknowledged
        combined["can_continue_to_phase8"] = combined.get("combined_status") != "blocking" and (
            combined.get("combined_status") == "pass" or acknowledged
        )
        combined_path.write_text(json.dumps(combined, indent=2), encoding="utf-8")
    return path


def check_pca_stability_gate(output_dir: Path | str) -> tuple[bool, dict[str, Any]]:
    root = Path(output_dir)
    report: dict[str, Any] = {
        "gate_passed": False,
        "combined_status": "",
        "warnings_acknowledged": False,
        "can_continue_to_phase8": False,
        "messages": [],
    }
    combined_path = root / "pca_stability_combined_summary.json"
    if not combined_path.is_file():
        report["messages"].append("Missing pca_stability_combined_summary.json; run Step 7A first.")
        return False, report

    combined = json.loads(combined_path.read_text(encoding="utf-8"))
    report["combined_status"] = str(combined.get("combined_status") or "")
    report["warnings_acknowledged"] = load_pca_stability_acknowledgment(root)
    report["can_continue_to_phase8"] = bool(combined.get("can_continue_to_phase8"))

    if report["combined_status"] == "blocking":
        report["messages"].append("PCA stability status is blocking for A and/or B.")
        return False, report

    if report["combined_status"] == "warning" and not report["warnings_acknowledged"]:
        report["messages"].append("Acknowledge PCA stability warnings before Phase 8.")
        return False, report

    if not report["can_continue_to_phase8"]:
        report["messages"].append("pca_stability_combined_summary.json reports can_continue_to_phase8=false.")
        return False, report

    report["gate_passed"] = True
    return True, report
