"""Input/output helpers for Layer 3 JcvPCA.

Responsibilities:
- load a Layer 2.5 JcvPCA-ready matrix (parquet or csv);
- load the Layer 3 analysis manifest CSV;
- infer the ordered list of feature columns (``*_rx``/``*_ry``/``*_rz``);
- build the joint-link map (link stem -> {rx, ry, rz} feature columns).

This module never modifies, repairs, fills, or interpolates data. It only reads
and organises it. Validation lives in ``validation.py``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

AXIS_SUFFIXES: tuple[str, str, str] = ("_rx", "_ry", "_rz")

MANIFEST_COLUMNS: list[str] = [
    "subject_id",
    "timepoint",
    "part_id",
    "repetition_id",
    "group_id",
    "matrix_path",
    "include_in_analysis",
    "analysis_role",
]


def load_matrix(path: str | Path) -> pd.DataFrame:
    """Load a single Layer 2.5 JcvPCA-ready matrix.

    Supports ``.parquet`` and ``.csv``. Returns the raw frame unchanged; no
    coercion, fill, or repair is performed.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Matrix file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported matrix file type '{suffix}' for: {path}")


def infer_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return feature columns (those ending in ``_rx``/``_ry``/``_rz``), in
    the dataframe's existing column order.
    """
    return [c for c in df.columns if c.endswith(AXIS_SUFFIXES)]


def axis_of(feature: str) -> str:
    """Return the axis token ('rx'/'ry'/'rz') for a feature column."""
    if not feature.endswith(AXIS_SUFFIXES):
        raise ValueError(f"Not a rotation-vector feature column: {feature}")
    return feature[-2:]


def link_id_of(feature: str) -> str:
    """Return the joint-link stem for a feature column by stripping the final
    axis suffix only.

    Example: ``J046_671_to_RThigh_rz`` -> ``J046_671_to_RThigh``.
    """
    if not feature.endswith(AXIS_SUFFIXES):
        raise ValueError(f"Not a rotation-vector feature column: {feature}")
    return feature[:-3]


def build_joint_link_map(feature_names: list[str]) -> dict[str, dict[str, str]]:
    """Build a mapping from each joint-link stem to its axis feature columns.

    Returns an insertion-ordered dict like::

        {"J004_Neck_to_Head": {"rx": "J004_Neck_to_Head_rx",
                                "ry": "J004_Neck_to_Head_ry",
                                "rz": "J004_Neck_to_Head_rz"}, ...}

    Link order follows first appearance of each stem in ``feature_names``.
    Completeness of triplets is enforced separately in ``validation.py``.
    """
    link_map: dict[str, dict[str, str]] = {}
    for feat in feature_names:
        link = link_id_of(feat)
        axis = axis_of(feat)
        link_map.setdefault(link, {})[axis] = feat
    return link_map


def load_analysis_manifest(path: str | Path) -> pd.DataFrame:
    """Load the Layer 3 analysis manifest CSV.

    Validates only that the required columns exist and normalises the
    ``include_in_analysis`` column to boolean. Role/duplicate/file-existence
    checks live in ``validation.py``.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Analysis manifest not found: {path}")
    df = pd.read_csv(path)
    missing = [c for c in MANIFEST_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Analysis manifest missing required columns: {missing}. "
            f"Expected columns: {MANIFEST_COLUMNS}"
        )
    df = df.copy()
    df["include_in_analysis"] = df["include_in_analysis"].map(_to_bool)
    return df


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n", ""}:
        return False
    raise ValueError(f"Cannot interpret include_in_analysis value: {value!r}")
