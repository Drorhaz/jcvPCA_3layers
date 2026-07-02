"""Tests for request-driven Gaga batch planning."""

from __future__ import annotations

from pathlib import Path

import pytest

from layer3_jcvpca.batch_settings import GagaBatchSettings
from layer3_jcvpca.request_plan import load_analysis_request_yaml, plan_from_analysis_request


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_batch_settings_from_analysis_config(repo_root: Path):
    settings = GagaBatchSettings.from_analysis_config(repo_root)
    assert settings.variance_threshold == 0.80
    assert settings.sensitivity_p == 2
    assert settings.explained_variance_weighting is False


def test_plan_from_analysis_request_filters_comparisons():
    request = {
        "selection": {
            "participant_id": "671",
            "blocks": {"A": ["P1", "P2"], "B": ["P3", "P4", "P5"]},
        },
        "comparisons": [{"comparison_id": "L1_T1_vs_T2"}],
        "outputs": {"pc_focus_spaces": ["all", "functional"], "generate_comparison_plots": False},
        "link_focus": {"body_regions": [], "link_stems": [], "use_comparable_links_only": True},
    }
    plan = plan_from_analysis_request(request, settings=GagaBatchSettings.defaults())
    assert plan.participants == ("671",)
    assert plan.comparison_ids == ("L1_T1_vs_T2",)
    assert plan.settings.generate_comparison_plots is False
    assert "functional" in plan.settings.pc_focus_spaces
    assert "null_space" not in plan.settings.pc_focus_spaces
    assert plan.link_focus.use_comparable_links_only is True
    assert plan.link_focus.requests_explicit_region_or_stem_filter is False


def test_load_template_request(repo_root: Path):
    path = repo_root / "config" / "analysis_request.template.yaml"
    request = load_analysis_request_yaml(path)
    plan = plan_from_analysis_request(request, settings=GagaBatchSettings.defaults())
    assert plan.participants[0] == "671"
