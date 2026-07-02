"""Scientific settings for Gaga batch runs — loaded from repo ``analysis_config``."""

from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from layer3_jcvpca.jcvpca_trace import PcaAParameters
from layer3_jcvpca.pc_focus import PC_FOCUS_ALL, PC_FOCUS_FUNCTIONAL, PC_FOCUS_NULL_SPACE
from layer3_jcvpca.workbench_jcvpca_runner import WeightingParameters


def _repo_root(start: Path | None = None) -> Path:
    anchor = (start or Path(__file__).resolve()).resolve()
    for candidate in (anchor, *anchor.parents):
        if (candidate / "config" / "analysis_params.yaml").is_file():
            return candidate
        if (candidate.parent / "config" / "analysis_params.yaml").is_file():
            return candidate.parent
    raise FileNotFoundError("Could not locate repository root (config/analysis_params.yaml).")


def _ensure_repo_src_on_path(project_root: Path) -> None:
    src = project_root / "src"
    entry = str(src)
    if src.is_dir() and entry not in sys.path:
        sys.path.insert(0, entry)


@dataclass(frozen=True)
class GagaBatchSettings:
    variance_threshold: float = 0.80
    min_pcs: int = 2
    max_pcs: int = 10
    sensitivity_p: int = 2
    explained_variance_weighting: bool = False
    pc_focus_spaces: tuple[str, ...] = ("all", "functional", "null_space")
    generate_comparison_plots: bool = True
    generate_full_numeric_reports: str = "on_demand"
    generate_poster_package: str = "on_demand"

    @classmethod
    def from_analysis_config(cls, project_root: Path | None = None) -> GagaBatchSettings:
        root = (project_root or _repo_root()).resolve()
        _ensure_repo_src_on_path(root)
        from analysis_config import load_analysis_config

        cfg = load_analysis_config(project_root=root)
        return cls(
            variance_threshold=float(cfg.get("pca.variance_threshold")),
            min_pcs=int(cfg.get("pca.min_pcs")),
            max_pcs=int(cfg.get("pca.max_pcs")),
            sensitivity_p=int(cfg.get("pc_focus.sensitivity_p_archived")),
            explained_variance_weighting=bool(cfg.get("weighting.explained_variance_weighting")),
        )

    @classmethod
    def defaults(cls) -> GagaBatchSettings:
        """Hardcoded fallbacks matching historical gaga_batch_runner behavior."""
        return cls()

    def merge_request_outputs(self, outputs: dict[str, Any] | None) -> GagaBatchSettings:
        if not outputs:
            return self
        spaces = outputs.get("pc_focus_spaces")
        pc_focus_spaces = tuple(str(s) for s in spaces) if spaces else self.pc_focus_spaces
        generate_plots = bool(outputs.get("generate_comparison_plots", self.generate_comparison_plots))
        full_numeric = str(
            outputs.get("generate_full_numeric_reports", self.generate_full_numeric_reports)
        )
        poster = str(outputs.get("generate_poster_package", self.generate_poster_package))
        return replace(
            self,
            pc_focus_spaces=pc_focus_spaces,
            generate_comparison_plots=generate_plots,
            generate_full_numeric_reports=full_numeric,
            generate_poster_package=poster,
        )

    def pca_a_parameters(self) -> PcaAParameters:
        return PcaAParameters(
            variance_threshold=self.variance_threshold,
            min_pcs=self.min_pcs,
            max_pcs=self.max_pcs,
        )

    def weighting_parameters(self) -> WeightingParameters:
        return WeightingParameters(
            explained_variance_weighting=self.explained_variance_weighting,
        )

    def wants_functional_focus(self) -> bool:
        return "functional" in self.pc_focus_spaces

    def wants_null_space_focus(self) -> bool:
        return "null_space" in self.pc_focus_spaces

    def focus_mode_for_label(self, focus_label: str) -> str | None:
        if focus_label == "functional_p2":
            return PC_FOCUS_FUNCTIONAL if self.wants_functional_focus() else None
        if focus_label == "null_space_p2":
            return PC_FOCUS_NULL_SPACE if self.wants_null_space_focus() else None
        return None
