"""Tests for on-demand report policy handling."""

from __future__ import annotations

from pathlib import Path

from layer3_jcvpca.on_demand_reports import (
    OUTPUT_POLICY_ALWAYS,
    OUTPUT_POLICY_NEVER,
    OUTPUT_POLICY_ON_DEMAND,
    generate_on_demand_reports,
    normalize_output_policy,
)


def test_normalize_output_policy_defaults_invalid():
    assert normalize_output_policy(None) == OUTPUT_POLICY_ON_DEMAND
    assert normalize_output_policy("bogus") == OUTPUT_POLICY_ON_DEMAND
    assert normalize_output_policy("always") == OUTPUT_POLICY_ALWAYS


def test_on_demand_skips_heavy_reports_by_default(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    (repo / "config" / "analysis_params.yaml").write_text("version: 1\n", encoding="utf-8")
    batch_root = repo / "Layer3_JcvPCA" / "outputs" / "gaga_batch_jcvpca_test"
    batch_root.mkdir(parents=True)
    manifest = generate_on_demand_reports(
        batch_root,
        generate_full_numeric_reports=OUTPUT_POLICY_ON_DEMAND,
        generate_poster_package=OUTPUT_POLICY_ON_DEMAND,
        project_root=repo,
    )
    assert manifest["artifacts"]["full_numeric"]["status"] == "skipped"
    assert manifest["artifacts"]["poster_package"]["status"] == "skipped"
    assert (batch_root / "on_demand_reports_manifest.json").is_file()


def test_never_policy_skips_even_when_forced(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    (repo / "config" / "analysis_params.yaml").write_text("version: 1\n", encoding="utf-8")
    batch_root = repo / "Layer3_JcvPCA" / "outputs" / "gaga_batch_jcvpca_test"
    batch_root.mkdir(parents=True)

    def _fail_run(*args, **kwargs):
        raise AssertionError("should not run subprocess when policy=never")

    monkeypatch.setattr("layer3_jcvpca.on_demand_reports._run_script", _fail_run)
    manifest = generate_on_demand_reports(
        batch_root,
        generate_full_numeric_reports=OUTPUT_POLICY_NEVER,
        generate_poster_package=OUTPUT_POLICY_NEVER,
        project_root=repo,
        force=True,
    )
    assert manifest["artifacts"]["full_numeric"]["status"] == "skipped"
    assert manifest["artifacts"]["poster_package"]["status"] == "skipped"
