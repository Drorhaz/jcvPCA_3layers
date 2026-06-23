"""Canonical identity columns for Layer 3 tables."""

from __future__ import annotations

import pandas as pd

from layer3_jcvpca.io import axis_of, link_id_of


def parse_canonical_feature(feature: str) -> dict[str, str]:
    """Split ``Parent_to_Child_rx`` into identity fields."""
    axis = axis_of(feature)
    stem = link_id_of(feature)
    if "_to_" not in stem:
        return {
            "feature_name": feature,
            "canonical_link_name": stem,
            "parent_canonical": "",
            "child_canonical": "",
            "axis": axis,
            "link_id": stem,
        }
    parent, child = stem.split("_to_", 1)
    return {
        "feature_name": feature,
        "canonical_link_name": f"{parent}->{child}",
        "parent_canonical": parent,
        "child_canonical": child,
        "axis": axis,
        "link_id": stem,
    }


def enrich_dataframe_with_identity(df: pd.DataFrame, feature_col: str = "feature") -> pd.DataFrame:
    """Add canonical identity columns to a feature-level DataFrame."""
    out = df.copy()
    parsed = [parse_canonical_feature(str(f)) for f in out[feature_col]]
    for key in ("canonical_link_name", "parent_canonical", "child_canonical", "axis", "link_id"):
        out[key] = [p[key] for p in parsed]
    return out
