"""Shared synthetic fixtures for Layer 3 JcvPCA tests.

Synthetic generators are a project-specific testing addition (not part of the
paper script). They build small, deterministic matrices with the Layer 2.5
schema so tests do not depend on real session data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

METADATA_COLS = ["session_id", "run_label", "frame", "time_sec"]

# Two joint-links x three axes = six feature columns.
LINKS = ["J004_Neck_to_Head", "J028_Chest_to_Neck"]
AXES = ["rx", "ry", "rz"]
FEATURE_NAMES = [f"{link}_{axis}" for link in LINKS for axis in AXES]


def make_matrix(
    n_rows: int = 200,
    seed: int = 0,
    session_id: str = "671_T1_P1_R1",
    feature_names: list[str] | None = None,
    scale: float | None = None,
) -> pd.DataFrame:
    """Build a synthetic Layer 2.5-style matrix with metadata + feature columns."""
    feature_names = feature_names or FEATURE_NAMES
    rng = np.random.default_rng(seed)
    n_feat = len(feature_names)
    data = rng.standard_normal((n_rows, n_feat))
    if scale is not None:
        data = data * scale
    df = pd.DataFrame(data, columns=feature_names)
    df.insert(0, "time_sec", np.arange(n_rows) / 120.0)
    df.insert(0, "frame", np.arange(n_rows))
    df.insert(0, "run_label", f"{session_id}_Take")
    df.insert(0, "session_id", session_id)
    return df


@pytest.fixture()
def feature_names() -> list[str]:
    return list(FEATURE_NAMES)


@pytest.fixture()
def metadata_cols() -> list[str]:
    return list(METADATA_COLS)


@pytest.fixture()
def matrix_A() -> pd.DataFrame:
    return make_matrix(n_rows=200, seed=1)


@pytest.fixture()
def matrix_B() -> pd.DataFrame:
    return make_matrix(n_rows=200, seed=2, session_id="671_T2_P1_R1")
