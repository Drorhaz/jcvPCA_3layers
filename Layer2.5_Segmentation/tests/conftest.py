"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_LAYER1 = REPO_ROOT / "input" / "Layer1_QC" / "QC_671_T1_P1_R1"
FIXTURE_LAYER2 = REPO_ROOT / "input" / "Layer2_Kinematics" / "671_T1_P1_R1"


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def fixture_layer1_dir() -> Path:
    return FIXTURE_LAYER1


@pytest.fixture
def fixture_layer2_dir() -> Path:
    return FIXTURE_LAYER2
