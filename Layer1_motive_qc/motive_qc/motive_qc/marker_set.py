"""Per-session marker-set identity summary for Layer 1 contract outputs."""

from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd

from motive_qc.session_identity import session_identity_from_metadata


def _canonical_labeled_names(inventory: pd.DataFrame) -> list[str]:
    if inventory.empty:
        return []
    labeled = inventory[inventory.get("is_labeled", False).astype(bool)]
    if labeled.empty:
        return []
    if "canonical_short_name" in labeled.columns:
        names = labeled["canonical_short_name"].astype(str).tolist()
    else:
        names = labeled["marker_name"].astype(str).tolist()
    return sorted({n for n in names if n and n.lower() != "nan"})


def _observed_prefixes(inventory: pd.DataFrame) -> list[str]:
    if inventory.empty or "skeleton_prefix" not in inventory.columns:
        return []
    labeled = inventory[inventory.get("is_labeled", False).astype(bool)]
    prefixes = sorted(
        {
            str(p).strip()
            for p in labeled["skeleton_prefix"].astype(str)
            if str(p).strip() and str(p).strip().lower() != "nan"
        }
    )
    return prefixes


def marker_set_hash(canonical_names: list[str]) -> str:
    """Stable short hash of sorted canonical marker short names."""
    if not canonical_names:
        return ""
    payload = "|".join(canonical_names).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def build_marker_set_warning(
    participant_id: str,
    prefixes: list[str],
) -> str:
    """Human-readable marker-set warnings for one session."""
    warnings: list[str] = []
    if len(prefixes) > 1:
        warnings.append(f"MULTIPLE_ASSET_PREFIXES:{','.join(prefixes)}")
    if not prefixes:
        return ""
    default_prefix = participant_id
    non_default = [p for p in prefixes if p != default_prefix]
    for prefix in non_default:
        warnings.append(
            f"ASSET_PREFIX_{prefix} (participant {participant_id}; "
            "compare canonical_marker_names / marker_set_id across sessions)"
        )
    if len(prefixes) == 1 and prefixes[0] == default_prefix:
        return ""
    if len(prefixes) == 1 and not non_default:
        return ""
    return "; ".join(warnings)


def prefix_change_flag(participant_id: str, prefixes: list[str]) -> bool:
    """True when asset prefix differs from participant id or multiple prefixes exist."""
    if len(prefixes) > 1:
        return True
    if not prefixes:
        return False
    return prefixes[0] != participant_id


def build_layer1_marker_set(
    session_metadata: dict[str, Any],
    inventory: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """One-row marker-set summary for ``layer1_marker_set.csv``."""
    identity = session_identity_from_metadata(session_metadata, config)
    canonical_names = _canonical_labeled_names(inventory)
    prefixes = _observed_prefixes(inventory)
    n_raw_labeled = int(inventory["is_labeled"].sum()) if "is_labeled" in inventory.columns else 0
    n_in_analysis = (
        int(inventory["included_in_analysis"].sum())
        if "included_in_analysis" in inventory.columns
        else n_raw_labeled
    )
    marker_set_id = marker_set_hash(canonical_names)
    warning = build_marker_set_warning(identity["participant_id"], prefixes)
    row = {
        **identity,
        "asset_prefixes_observed": ";".join(prefixes),
        "n_raw_labeled_markers": n_raw_labeled,
        "n_in_analysis_markers": n_in_analysis,
        "n_canonical_markers": len(canonical_names),
        "canonical_marker_names": ";".join(canonical_names),
        "marker_set_id_or_hash": marker_set_id,
        "marker_set_warning": warning,
    }
    return pd.DataFrame([row])
