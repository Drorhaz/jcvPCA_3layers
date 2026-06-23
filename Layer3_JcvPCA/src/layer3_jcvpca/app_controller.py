"""Controller for Layer 3 JcvPCA Streamlit UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from layer3_jcvpca.analysis_service import (
    AnalysisIdentity,
    AnalysisParams,
    AnalysisResult,
    run_direct_analysis,
)
from layer3_jcvpca.matrix_stability import MatrixStabilityParams
from layer3_jcvpca.preflight import (
    PreflightReport,
    run_preflight,
    stability_summary_table,
    windows_summary_table,
)


DEFAULT_PATHS = {
    "A": "Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/671_T1_P1_R1/671_T1_P1_R1_g4_s14280_e21000/window_jvcpca_matrix.parquet",
    "B": "Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/671_T2_P1_R2/671_T2_P1_R2_g4_s14040_e21360/window_jvcpca_matrix.parquet",
    "NV_A": "Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/671_T1_P1_R1/671_T1_P1_R1_g4_s14280_e21000/window_jvcpca_matrix.parquet",
    "NV_B": "Layer2.5_Segmentation/outputs/pre_jvcpca_review/671/671_T1_P1_R2/671_T1_P1_R2_g4_s14040_e20880/window_jvcpca_matrix.parquet",
}


@dataclass
class Layer3AnalysisController:
    repo_root: Path
    preflight_report: PreflightReport | None = None
    analysis_result: AnalysisResult | None = None
    paths: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_PATHS))
    stability_params: MatrixStabilityParams = field(default_factory=MatrixStabilityParams)
    analysis_params: AnalysisParams = field(default_factory=AnalysisParams)
    warnings_acknowledged: bool = False

    def resolve_path(self, p: str) -> str:
        path = Path(p)
        if not path.is_absolute():
            path = self.repo_root / path
        return str(path.resolve())

    def load_preflight(self, paths: dict[str, str]) -> PreflightReport:
        resolved = {k: self.resolve_path(v) for k, v in paths.items()}
        self.paths = resolved
        self.preflight_report = run_preflight(
            resolved,
            stability_params=self.stability_params,
            min_rows_for_pca=self.analysis_params.min_rows_for_pca,
        )
        return self.preflight_report

    def can_run(self) -> tuple[bool, str]:
        if self.preflight_report is None:
            return False, "Run preflight first."
        if self.preflight_report.status == "blocking":
            return False, "Blocking validation failures must be resolved."
        if self.preflight_report.status == "warning" and not self.warnings_acknowledged:
            return False, "Acknowledge matrix-stability / QC warnings before running."
        return True, "Ready"

    def run_analysis(
        self,
        identity: AnalysisIdentity,
        output_dir: str | Path,
    ) -> AnalysisResult:
        ok, msg = self.can_run()
        if not ok:
            raise ValueError(msg)
        self.analysis_result = run_direct_analysis(
            self.paths,
            identity,
            self.analysis_params,
            output_dir,
            preflight=self.preflight_report,
        )
        return self.analysis_result

    def windows_table(self) -> pd.DataFrame:
        if not self.preflight_report:
            return pd.DataFrame()
        return windows_summary_table(self.preflight_report.windows)

    def stability_table(self) -> pd.DataFrame:
        if not self.preflight_report or not self.preflight_report.stability:
            return pd.DataFrame()
        return stability_summary_table(self.preflight_report.stability)

    def checks_table(self) -> pd.DataFrame:
        if not self.preflight_report:
            return pd.DataFrame()
        return pd.DataFrame(
            [
                {
                    "name": c.name,
                    "status": c.status,
                    "category": c.category,
                    "message": c.message,
                }
                for c in self.preflight_report.checks
            ]
        )

    def default_output_dir(self, analysis_id: str) -> Path:
        return self.repo_root / "Layer3_JcvPCA" / "outputs" / analysis_id
