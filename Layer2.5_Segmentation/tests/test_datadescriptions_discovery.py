"""Tests for session DataDescriptions auto-discovery."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pre_jvcpca_review.datadescriptions_discovery import (
    normalize_take_key,
    resolve_datadescriptions_path,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DESC = ROOT / "data_description"
EVAL_671 = (
    ROOT
    / "reevluate_project"
    / "671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001_DataDescriptions.csv"
)


def test_normalize_take_key_matches_layer1_and_layer2_names() -> None:
    layer1 = "252_T3_P1_R2_Take 2026-06-09 05.04.14 PM_001.csv"
    layer2 = "252_T3_P1_R2_Take_2026-06-09_05.04.14_PM_001"
    assert normalize_take_key(layer1) == normalize_take_key(layer2)


def test_resolve_datadescriptions_for_671_session() -> None:
    row = {
        "session_id": "671_T1_P1_R1",
        "layer1_source_file": "671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv",
        "layer2_run_dir": str(
            ROOT.parent
            / "Layer2_Motive_Kinematics"
            / "outputs"
            / "671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001"
        ),
    }
    resolved = resolve_datadescriptions_path(
        row,
        search_roots=[DATA_DESC, ROOT / "reevluate_project"],
    )
    assert resolved is not None
    assert resolved.name.endswith("_DataDescriptions.csv")
    assert "671_T1_P1_R1" in resolved.name


def test_resolve_skips_empty_placeholder_for_252(tmp_path: Path) -> None:
    empty = tmp_path / "252_T3_P1_R2_Take 2026-06-09 05.04.14 PM_001_DataDescriptions.csv"
    empty.write_text("")
    row = {
        "session_id": "252_T3_P1_R2",
        "layer1_source_file": "252_T3_P1_R2_Take 2026-06-09 05.04.14 PM_001.csv",
        "layer2_run_dir": "252_T3_P1_R2_Take_2026-06-09_05.04.14_PM_001",
    }
    assert resolve_datadescriptions_path(row, search_roots=[tmp_path]) is None

    populated = tmp_path / "252_T3_P1_R2_Take 2026-06-09 05.04.14 PM_001_DataDescriptions.csv"
    populated.write_text("Skeleton,252,0,\nBone Marker,SJN,252_SJN,252,0,0,0,\n")
    assert resolve_datadescriptions_path(row, search_roots=[tmp_path]) == populated


def test_controller_resolve_datadescriptions() -> None:
    from pre_jvcpca_review.app_controller import PreJcvpcaReviewController

    ctrl = PreJcvpcaReviewController(ROOT)
    ctrl.current_row = pd.Series(
        {
            "session_id": "671_T1_P1_R1",
            "layer1_source_file": "671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv",
            "layer2_run_dir": "",
        }
    )
    resolved = ctrl.resolve_datadescriptions()
    assert resolved is not None
    assert resolved.is_file()
    assert resolved.stat().st_size > 0
