"""Preflight validation for Layer 3 direct-window analysis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from layer3_jcvpca.io import infer_feature_columns, load_matrix
from layer3_jcvpca.matrix_stability import (
    MatrixStabilityParams,
    MatrixStabilityResult,
    assess_all_matrices,
    combined_stability_status,
)
from layer3_jcvpca.validation import (
    ValidationError,
    validate_feature_schema_match,
    validate_jcvpca_matrix,
)

REQUIRED_METADATA_COLS = ["session_id", "run_label", "frame", "time_sec"]
J00X_PATTERN = re.compile(r"^J\d{3}_")


@dataclass
class WindowLoadInfo:
    role: str
    matrix_path: str
    manifest_path: str | None
    df: pd.DataFrame
    manifest: dict[str, Any] | None
    window_id: str = ""
    session_id: str = ""
    timepoint: str = ""
    part_id: str = ""
    repetition_id: str = ""
    n_frames: int = 0
    n_features: int = 0
    feature_scope: str = ""
    layer3_safe: bool | None = None
    warning_count: int = 0


@dataclass
class PreflightCheck:
    name: str
    status: str  # pass | warning | blocking
    message: str
    category: str = "schema"


@dataclass
class PreflightReport:
    checks: list[PreflightCheck] = field(default_factory=list)
    windows: list[WindowLoadInfo] = field(default_factory=list)
    stability: dict[str, MatrixStabilityResult] = field(default_factory=dict)
    feature_names: list[str] = field(default_factory=list)
    status: str = "pass"

    def add(self, check: PreflightCheck) -> None:
        self.checks.append(check)
        if check.status == "blocking":
            self.status = "blocking"
        elif check.status == "warning" and self.status != "blocking":
            self.status = "warning"

    @property
    def blocking_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "blocking")

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "warning")


def _find_manifest(matrix_path: Path) -> Path | None:
    candidate = matrix_path.parent / "window_export_manifest.json"
    return candidate if candidate.is_file() else None


def _parse_session_fields(session_id: str) -> tuple[str, str, str]:
    # e.g. 671_T1_P1_R1
    parts = session_id.split("_")
    tp = parts[1] if len(parts) > 1 else ""
    part = parts[2] if len(parts) > 2 else ""
    rep = parts[3] if len(parts) > 3 else ""
    return tp, part, rep


def _uses_j00x_identity(feature_names: list[str]) -> bool:
    stems = {f.rsplit("_", 1)[0] for f in feature_names if f.endswith(("_rx", "_ry", "_rz"))}
    return any(J00X_PATTERN.match(s) for s in stems)


def load_window(role: str, matrix_path: str | Path) -> WindowLoadInfo:
    path = Path(matrix_path)
    df = load_matrix(path)
    manifest_path = _find_manifest(path)
    manifest = None
    if manifest_path:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    feature_names = infer_feature_columns(df)
    session_id = str(df["session_id"].iloc[0]) if "session_id" in df.columns and len(df) else ""
    tp, part, rep = _parse_session_fields(session_id)
    ws = manifest.get("warnings_summary", {}) if manifest else {}
    identity = manifest.get("identity", {}) if manifest else {}

    return WindowLoadInfo(
        role=role,
        matrix_path=str(path),
        manifest_path=str(manifest_path) if manifest_path else None,
        df=df,
        manifest=manifest,
        window_id=manifest.get("window_label", path.parent.name) if manifest else path.parent.name,
        session_id=session_id,
        timepoint=str(identity.get("timepoint", tp)),
        part_id=str(identity.get("part_id", part)),
        repetition_id=str(identity.get("repetition_id", rep)),
        n_frames=len(df),
        n_features=len(feature_names),
        feature_scope=str(manifest.get("feature_naming_policy", "")) if manifest else "",
        layer3_safe=manifest.get("layer3_safe") if manifest else None,
        warning_count=int(ws.get("n_warnings", 0)) if ws else 0,
    )


def run_preflight(
    paths: dict[str, str],
    *,
    required_metadata_cols: list[str] | None = None,
    min_rows_for_pca: int = 10,
    stability_params: MatrixStabilityParams | None = None,
) -> PreflightReport:
    """Validate four windows: A, B, NV_A, NV_B."""
    required_metadata_cols = required_metadata_cols or REQUIRED_METADATA_COLS
    stability_params = stability_params or MatrixStabilityParams()
    report = PreflightReport()

    loaded: dict[str, WindowLoadInfo] = {}
    for role in ("A", "B", "NV_A", "NV_B"):
        if role not in paths or not paths[role]:
            report.add(
                PreflightCheck(
                    name=f"{role}_path",
                    status="blocking",
                    message=f"Missing path for {role}.",
                    category="input",
                )
            )
            continue
        try:
            info = load_window(role, paths[role])
            loaded[role] = info
            report.windows.append(info)
        except (FileNotFoundError, ValidationError, ValueError) as exc:
            report.add(
                PreflightCheck(
                    name=f"{role}_load",
                    status="blocking",
                    message=str(exc),
                    category="input",
                )
            )

    if len(loaded) < 4:
        return report

    reference_features = infer_feature_columns(loaded["A"].df)
    report.feature_names = reference_features

    # Per-matrix schema validation
    for role, info in loaded.items():
        try:
            validate_jcvpca_matrix(info.df, required_metadata_cols, min_rows_for_pca)
            report.add(
                PreflightCheck(
                    name=f"{role}_schema",
                    status="pass",
                    message=f"{role} passed schema validation.",
                    category="schema",
                )
            )
        except ValidationError as exc:
            report.add(
                PreflightCheck(
                    name=f"{role}_schema",
                    status="blocking",
                    message=str(exc),
                    category="schema",
                )
            )

        if info.layer3_safe is False:
            report.add(
                PreflightCheck(
                    name=f"{role}_layer3_safe",
                    status="blocking",
                    message=f"{role} export manifest reports layer3_safe=false.",
                    category="manifest",
                )
            )
        elif info.layer3_safe is True:
            report.add(
                PreflightCheck(
                    name=f"{role}_layer3_safe",
                    status="pass",
                    message=f"{role} layer3_safe=true.",
                    category="manifest",
                )
            )
        else:
            report.add(
                PreflightCheck(
                    name=f"{role}_layer3_safe",
                    status="warning",
                    message=f"{role} manifest missing or layer3_safe not set.",
                    category="manifest",
                )
            )

        if info.warning_count > 0:
            report.add(
                PreflightCheck(
                    name=f"{role}_export_warnings",
                    status="warning",
                    message=f"{role} has {info.warning_count} export warning(s).",
                    category="qc",
                )
            )

    # Feature identity / order
    try:
        validate_feature_schema_match(
            {role: info.df for role, info in loaded.items()},
            reference_features,
        )
        report.add(
            PreflightCheck(
                name="feature_identity_match",
                status="pass",
                message="All matrices share identical feature names and order.",
                category="schema",
            )
        )
    except ValidationError as exc:
        report.add(
            PreflightCheck(
                name="feature_identity_match",
                status="blocking",
                message=str(exc),
                category="schema",
            )
        )

    if _uses_j00x_identity(reference_features):
        report.add(
            PreflightCheck(
                name="canonical_feature_identity",
                status="blocking",
                message="J00x link stems detected; canonical parent_child_axis identity required.",
                category="schema",
            )
        )
    else:
        report.add(
            PreflightCheck(
                name="canonical_feature_identity",
                status="pass",
                message="Features use canonical parent_child_axis naming.",
                category="schema",
            )
        )

    report.add(
        PreflightCheck(
            name="ab_direction",
            status="pass",
            message="A is reference; B is comparison (fixed by UI design).",
            category="analysis",
        )
    )
    report.add(
        PreflightCheck(
            name="nv_windows_present",
            status="pass",
            message="NV_A and NV_B loaded for natural-variability baseline.",
            category="analysis",
        )
    )

    # Matrix stability
    if stability_params.check_matrix_stability:
        matrices = {role: info.df for role, info in loaded.items()}
        manifests = {role: info.manifest for role, info in loaded.items()}
        report.stability = assess_all_matrices(
            matrices, params=stability_params, manifests=manifests
        )
        combined = combined_stability_status(report.stability)
        for role, stab in report.stability.items():
            for finding in stab.findings:
                report.add(
                    PreflightCheck(
                        name=f"{role}_stability_{finding['code']}",
                        status=finding["severity"],
                        message=f"[{role}] {finding['message']}",
                        category="matrix_stability",
                    )
                )
            if role == "A":
                report.add(
                    PreflightCheck(
                        name="A_reference_pca_readiness",
                        status=stab.status,
                        message=(
                            f"A/reference PCA readiness: rank={stab.metrics.get('matrix_rank')}, "
                            f"cond={stab.metrics.get('condition_number')}, "
                            f"dominant PC={stab.metrics.get('dominant_pc_variance_percent')}%."
                        ),
                        category="matrix_stability",
                    )
                )
        report.add(
            PreflightCheck(
                name="matrix_stability_combined",
                status=combined,
                message=f"Combined matrix stability status: {combined}.",
                category="matrix_stability",
            )
        )

    return report


def windows_summary_table(windows: list[WindowLoadInfo]) -> pd.DataFrame:
    rows = []
    for w in windows:
        rows.append(
            {
                "role": w.role,
                "window_id": w.window_id,
                "session_id": w.session_id,
                "timepoint": w.timepoint,
                "part_id": w.part_id,
                "repetition_id": w.repetition_id,
                "n_frames": w.n_frames,
                "n_features": w.n_features,
                "feature_scope": w.feature_scope,
                "layer3_safe": w.layer3_safe,
                "warning_count": w.warning_count,
            }
        )
    return pd.DataFrame(rows)


def stability_summary_table(stability: dict[str, MatrixStabilityResult]) -> pd.DataFrame:
    rows = [r.metrics for r in stability.values()]
    return pd.DataFrame(rows)
