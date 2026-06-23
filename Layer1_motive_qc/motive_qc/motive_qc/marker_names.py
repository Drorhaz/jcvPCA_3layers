"""Canonical marker-name helpers for Layer 1 contract outputs."""

from __future__ import annotations

import pandas as pd

from motive_qc.marker_meta import parse_marker_identity


def inventory_lookup(inventory: pd.DataFrame) -> dict[str, dict[str, str]]:
    """Map raw marker_name -> {canonical_short_name, skeleton_prefix}."""
    lookup: dict[str, dict[str, str]] = {}
    if inventory.empty or "marker_name" not in inventory.columns:
        return lookup
    for _, row in inventory.iterrows():
        name = str(row["marker_name"])
        canonical = str(row.get("canonical_short_name") or "")
        prefix = str(row.get("skeleton_prefix") or "")
        if not canonical or not prefix:
            skel, canon = parse_marker_identity(name)
            canonical = canonical or canon
            prefix = prefix or skel
        lookup[name] = {
            "marker_name_canonical": canonical,
            "asset_prefix": prefix,
        }
    return lookup


def resolve_marker_parts(raw_name: str, lookup: dict[str, dict[str, str]]) -> tuple[str, str, str]:
    """Return (raw, canonical, asset_prefix) for one marker or pair label."""
    raw = str(raw_name).strip()
    if not raw:
        return "", "", ""
    if raw in lookup:
        parts = lookup[raw]
        return raw, parts["marker_name_canonical"], parts["asset_prefix"]
    if "__" in raw and ":" not in raw and "_" not in raw.split("__", 1)[0]:
        return raw, raw, ""
    skel, canon = parse_marker_identity(raw)
    return raw, canon, skel


def add_marker_name_columns(
    df: pd.DataFrame,
    lookup: dict[str, dict[str, str]],
    marker_col: str = "marker_name",
) -> pd.DataFrame:
    """Add marker_name_raw, marker_name_canonical, asset_prefix; preserve marker_col."""
    if df.empty or marker_col not in df.columns:
        return df
    out = df.copy()
    raw_vals = out[marker_col].astype(str)
    canonical: list[str] = []
    prefixes: list[str] = []
    for val in raw_vals:
        raw, canon, prefix = resolve_marker_parts(val, lookup)
        canonical.append(canon)
        prefixes.append(prefix)
    out["marker_name_raw"] = raw_vals
    out["marker_name_canonical"] = canonical
    out["asset_prefix"] = prefixes
    return out


def add_pair_marker_columns(
    df: pd.DataFrame,
    lookup: dict[str, dict[str, str]],
    col_a: str = "marker_a",
    col_b: str = "marker_b",
) -> pd.DataFrame:
    """Add canonical/prefix columns for marker pair columns."""
    if df.empty:
        return df
    out = df.copy()
    if col_a in out.columns:
        out = add_marker_name_columns(out, lookup, marker_col=col_a)
        out = out.rename(
            columns={
                "marker_name_raw": f"{col_a}_raw",
                "marker_name_canonical": f"{col_a}_canonical",
                "asset_prefix": f"{col_a}_asset_prefix",
            }
        )
    if col_b in out.columns:
        out = add_marker_name_columns(out, lookup, marker_col=col_b)
        out = out.rename(
            columns={
                "marker_name_raw": f"{col_b}_raw",
                "marker_name_canonical": f"{col_b}_canonical",
                "asset_prefix": f"{col_b}_asset_prefix",
            }
        )
    return out


def enrich_marker_level_tables(
    tables: dict[str, pd.DataFrame],
    inventory: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Return copies of marker-level tables with canonical name columns added."""
    lookup = inventory_lookup(inventory)
    out = dict(tables)
    for key, marker_col in (
        ("gaps_over_0p2s", "marker_name"),
        ("gaps_over_0p5s", "marker_name"),
        ("artifact_events", "marker_name"),
        ("quarantined_markers", "marker_name"),
    ):
        if key in out:
            out[key] = add_marker_name_columns(out[key], lookup, marker_col=marker_col)
    if "segment_length_qc" in out:
        out["segment_length_qc"] = add_pair_marker_columns(out["segment_length_qc"], lookup)
    return out
