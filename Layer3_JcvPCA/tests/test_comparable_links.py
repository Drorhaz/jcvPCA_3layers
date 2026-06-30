"""Tests for comparable link detection (Phase 3)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from layer3_jcvpca.comparable_links import (
    COMPARABILITY_PASS,
    REASON_FEATURE_ORDER_MISMATCH,
    REASON_INCOMPLETE_TRIPLET,
    REASON_MISSING_LINK,
    central_manifest_path_for_root,
    detect_comparable_links,
    load_central_manifest,
    select_manifest_rows,
    validate_manual_link_selection,
    write_comparability_artifacts,
)
from conftest import FEATURE_NAMES, LINKS, make_matrix


def _manifest_row(
    *,
    matrix_path: Path,
    session_id: str = "671_T1_P1_R1",
    label: str = "P1",
    feature_schema_id: str = "schema_a",
) -> dict:
    return {
        "participant_id": "671",
        "timepoint": "T1",
        "repetition": "R1",
        "task_part_id": "P1",
        "session_id": session_id,
        "run_label": f"{session_id}_Take",
        "gaga_exercise_id": "9" if label == "P1" else "",
        "gaga_exercise_label": label,
        "export_granularity": "per_exercise" if label in {"P1", "P2", "P3", "P4", "P5"} else "combined_group4",
        "export_mode": "per_exercise" if label in {"P1", "P2", "P3", "P4", "P5"} else "combined_group4",
        "matrix_path": str(matrix_path),
        "manifest_path": str(matrix_path.parent / "window_export_manifest.json"),
        "layer3_safe": "true",
        "qc_status": "warning",
        "n_frames": 100,
        "n_features": len(FEATURE_NAMES),
        "feature_schema_id": feature_schema_id,
        "created_at": "2026-06-26T00:00:00+00:00",
    }


def _write_matrix(path: Path, session_id: str, feature_names: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    make_matrix(session_id=session_id, feature_names=feature_names).to_parquet(path, index=False)


def test_complete_triplet_detection(tmp_path: Path) -> None:
    matrix_path = tmp_path / "a.parquet"
    _write_matrix(matrix_path, "671_T1_P1_R1")
    rows = pd.DataFrame([_manifest_row(matrix_path=matrix_path)])
    report = detect_comparable_links(rows)
    assert report.summary["comparability_status"] == COMPARABILITY_PASS
    assert len(report.comparable_link_stems) == len(LINKS)
    assert report.feature_triplet_report["triplet_complete"].all()


def test_missing_axis_exclusion(tmp_path: Path) -> None:
    incomplete = [f"{LINKS[0]}_rx", f"{LINKS[0]}_ry", f"{LINKS[1]}_rx", f"{LINKS[1]}_ry", f"{LINKS[1]}_rz"]
    matrix_path = tmp_path / "incomplete.parquet"
    _write_matrix(matrix_path, "671_T1_P1_R1", feature_names=incomplete)
    rows = pd.DataFrame([_manifest_row(matrix_path=matrix_path)])
    report = detect_comparable_links(rows)
    assert LINKS[0] not in report.comparable_link_stems
    excluded = report.excluded_links[report.excluded_links["link_stem"] == LINKS[0]]
    assert not excluded.empty
    assert REASON_INCOMPLETE_TRIPLET in excluded.iloc[0]["reason_code"]


def test_missing_link_across_matrices(tmp_path: Path) -> None:
    path_a = tmp_path / "a.parquet"
    path_b = tmp_path / "b.parquet"
    _write_matrix(path_a, "671_T1_P1_R1", feature_names=FEATURE_NAMES)
    _write_matrix(
        path_b,
        "671_T1_P1_R2",
        feature_names=[c for c in FEATURE_NAMES if not c.startswith(LINKS[1])],
    )
    rows = pd.DataFrame(
        [
            _manifest_row(matrix_path=path_a, session_id="671_T1_P1_R1"),
            _manifest_row(matrix_path=path_b, session_id="671_T1_P1_R2", label="P1"),
        ]
    )
    report = detect_comparable_links(rows)
    assert LINKS[1] not in report.comparable_link_stems
    excluded = report.excluded_links[report.excluded_links["link_stem"] == LINKS[1]]
    assert REASON_MISSING_LINK in excluded.iloc[0]["reason_code"]


def test_feature_order_mismatch(tmp_path: Path) -> None:
    path_a = tmp_path / "a.parquet"
    path_b = tmp_path / "b.parquet"
    _write_matrix(path_a, "671_T1_P1_R1", feature_names=FEATURE_NAMES)
    _write_matrix(path_b, "671_T1_P1_R2", feature_names=list(reversed(FEATURE_NAMES)))
    rows = pd.DataFrame(
        [
            _manifest_row(matrix_path=path_a, session_id="671_T1_P1_R1"),
            _manifest_row(matrix_path=path_b, session_id="671_T1_P1_R2", label="P1"),
        ]
    )
    report = detect_comparable_links(rows)
    assert report.summary["feature_order_match"] is False
    assert any(
        REASON_FEATURE_ORDER_MISMATCH in str(code)
        for code in report.excluded_links["reason_code"].tolist()
    )


def test_manual_subset_cannot_include_excluded_links() -> None:
    with pytest.raises(ValueError, match="non-comparable"):
        validate_manual_link_selection(
            ["J004_Neck_to_Head", "J999_Unknown"],
            ["J004_Neck_to_Head"],
        )


def test_select_manifest_rows_from_central_manifest(tmp_path: Path) -> None:
    manifest = pd.DataFrame(
        [
            _manifest_row(matrix_path=tmp_path / "a.parquet", label="P1"),
            _manifest_row(matrix_path=tmp_path / "b.parquet", session_id="671_T1_P1_R2", label="P2"),
            _manifest_row(matrix_path=tmp_path / "c.parquet", session_id="671_T2_P1_R2", label="combined_group4"),
        ]
    )
    selected = select_manifest_rows(
        manifest,
        participant_ids=["671"],
        gaga_exercise_labels=["P1"],
    )
    assert len(selected) == 1
    assert selected.iloc[0]["gaga_exercise_label"] == "P1"


def test_write_comparability_artifacts(tmp_path: Path) -> None:
    matrix_path = tmp_path / "a.parquet"
    _write_matrix(matrix_path, "671_T1_P1_R1")
    report = detect_comparable_links(pd.DataFrame([_manifest_row(matrix_path=matrix_path)]))
    out_dir = tmp_path / "artifacts"
    paths = write_comparability_artifacts(report, out_dir)
    assert paths["comparable_links"].is_file()
    assert paths["comparability_summary"].is_file()


@pytest.mark.skipif(
    not central_manifest_path_for_root(
        Path(__file__).resolve().parents[2] / "Layer2.5_Segmentation" / "outputs" / "pre_jvcpca_review"
    ).is_file(),
    reason="central manifest not present",
)
def test_current_manifest_produces_expected_comparable_links() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    l25_root = repo_root / "Layer2.5_Segmentation" / "outputs" / "pre_jvcpca_review"
    manifest = load_central_manifest(l25_root)
    assert len(manifest) >= 18

    selected = select_manifest_rows(
        manifest,
        participant_ids=["671"],
        gaga_exercise_labels=["P1"],
        export_granularities=["per_exercise"],
    )
    assert len(selected) == 4
    report = detect_comparable_links(selected)
    assert report.summary["feature_schema_consistent"] is True
    assert report.summary["feature_order_match"] is True
    assert report.summary["n_comparable_links"] == 10
    assert "Neck_to_Head" in report.comparable_link_stems
