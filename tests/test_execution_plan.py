"""Tests for G5 dry-run execution planning."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def snapshot():
    from project_status import load_project_snapshot

    return load_project_snapshot(project_root=REPO_ROOT)


def _build_validated_request(snapshot):
    from analysis_request import AnalysisRequestInput, build_analysis_request, comparison_spec_from_preset

    inp = AnalysisRequestInput(
        participant_id="671",
        p_phases=("P1", "P2", "P3"),
        repetitions=("R1", "R2"),
        comparisons=[comparison_spec_from_preset("L1_T1_vs_T2")],
        segment_preset="only_P1_P3",
    )
    return build_analysis_request(snapshot, inp, request_id="g5_test_671_L1")


def test_build_execution_plan_structure(snapshot):
    from execution_plan import build_execution_plan

    request = _build_validated_request(snapshot)
    plan = build_execution_plan(snapshot, request)
    assert plan["version"] == 1
    assert plan["execution_plan_version"] == "G5"
    assert plan["execution"]["allowed"] is False
    assert "preflight" in plan
    assert "runner_translation" in plan
    assert "output_plan" in plan
    assert "reproducibility_package" in plan
    assert plan["runner_translation"]["requested_job_count"] >= 1


def test_runner_translation_maps_comparisons(snapshot):
    from execution_plan import translate_request_to_runner_plan

    request = _build_validated_request(snapshot)
    runner = translate_request_to_runner_plan(snapshot, request)
    assert runner["entrypoint"].endswith("run_gaga_batch_jcvpca.py")
    assert "671" in runner["participant_ids"]
    assert "L1_T1_vs_T2" in runner["requested_comparison_ids"]
    jobs = runner["requested_jobs"]
    assert any(j["comparison_id"] == "L1_T1_vs_T2" for j in jobs)
    assert all(j["comparison_output_dir"].startswith("comparisons/") for j in jobs)


def test_preflight_separates_levels(snapshot):
    from execution_plan import run_preflight_checks

    request = _build_validated_request(snapshot)
    preflight = run_preflight_checks(snapshot, request)
    assert hasattr(preflight, "blockers")
    assert hasattr(preflight, "warnings")
    assert hasattr(preflight, "advisory_notes")
    assert any(m.code == "no_execution_g5" for m in preflight.advisory_notes)


def test_canonical_batch_guard(snapshot):
    from execution_plan import run_preflight_checks

    request = _build_validated_request(snapshot)
    if not snapshot.canonical_batch_path:
        pytest.skip("No canonical batch path configured")
    preflight = run_preflight_checks(
        snapshot,
        request,
        proposed_batch_root=snapshot.canonical_batch_path,
    )
    codes = [m.code for m in preflight.blockers]
    assert "canonical_batch_guard" in codes or "canonical_batch_id_guard" in codes


def test_parse_request_to_input_roundtrip(snapshot):
    from execution_plan import parse_request_to_input

    request = _build_validated_request(snapshot)
    inp = parse_request_to_input(request)
    assert inp.participant_id == "671"
    assert inp.comparisons[0].comparison_id == "L1_T1_vs_T2"


def test_save_and_load_execution_plan(snapshot, tmp_path):
    from execution_plan import build_execution_plan, load_execution_plan, save_execution_plan

    request = _build_validated_request(snapshot)
    plan = build_execution_plan(snapshot, request)
    path = save_execution_plan(REPO_ROOT, plan, plans_dir=tmp_path / "plans")
    loaded = load_execution_plan(path)
    assert loaded["source_request_id"] == "g5_test_671_L1"
    assert loaded["execution"]["allowed"] is False


def test_reproducibility_spec_does_not_target_canonical(snapshot):
    from execution_plan import build_reproducibility_package_spec

    request = _build_validated_request(snapshot)
    spec = build_reproducibility_package_spec(snapshot, request)
    assert spec["write_policy"] == "future_guarded_runner_only"
    assert "_config_snapshot/" in spec["target_directory"]
    canonical = str(snapshot.canonical_batch_path or "")
    if canonical:
        assert canonical in spec["explicitly_not_written"]
