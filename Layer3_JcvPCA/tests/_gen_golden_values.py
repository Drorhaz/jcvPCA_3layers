"""One-off generator for the frozen golden values used by test_core_golden_regression.py.

NOT run by pytest. Run manually only to (re)derive baseline numbers, and only
with explicit review — regenerating silently would defeat the regression guard.

    .venv/bin/python tests/_gen_golden_values.py
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from layer3_jcvpca.aggregation import aggregate_axis_to_link_rss
from layer3_jcvpca.core import compute_jcvpca, select_selected_m_from_A
from layer3_jcvpca.io import build_joint_link_map

LINKS = ["J004_Neck_to_Head", "J028_Chest_to_Neck"]
AXES = ["rx", "ry", "rz"]
FEATURES = [f"{link}_{axis}" for link in LINKS for axis in AXES]
CANONICAL_VARIANCE_THRESHOLD = 0.80


def make_fixture(seed: int, session_id: str, n_rows: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    data = rng.standard_normal((n_rows, len(FEATURES)))
    df = pd.DataFrame(data, columns=FEATURES)
    df.insert(0, "time_sec", np.arange(n_rows) / 120.0)
    df.insert(0, "frame", np.arange(n_rows))
    df.insert(0, "run_label", f"{session_id}_Take")
    df.insert(0, "session_id", session_id)
    return df


def main() -> None:
    A = make_fixture(seed=20260701, session_id="671_T1_P1_R1")
    B = make_fixture(seed=20260703, session_id="671_T3_P1_R1")

    selected_m, evr_table = select_selected_m_from_A(
        A, FEATURES, CANONICAL_VARIANCE_THRESHOLD
    )
    result = compute_jcvpca(
        A, B, FEATURES, variance_threshold=CANONICAL_VARIANCE_THRESHOLD
    )
    link_map = build_joint_link_map(FEATURES)
    link_df = aggregate_axis_to_link_rss(
        result["A_abs_loadings"], result["B_abs_loadings"], FEATURES, link_map
    )

    out = {
        "selected_m": int(selected_m),
        "evr": [round(float(x), 12) for x in evr_table["explained_variance_ratio"]],
        "cumulative": [
            round(float(x), 12) for x in evr_table["cumulative_explained_variance"]
        ],
        "jcvpca_axis": np.round(result["jcvpca_axis"], 12).tolist(),
        "link_JcvPCA": {
            link: [
                round(float(v), 12)
                for v in link_df[link_df["link_id"] == link]["JcvPCA_link"]
            ]
            for link in LINKS
        },
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
