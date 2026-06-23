"""Canonical pilot feature manifest loading and identity resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from pre_jvcpca_review.load_layer2 import LinkRecord

MANIFEST_COLUMNS = [
    "feature_name",
    "canonical_link_name",
    "parent_canonical",
    "child_canonical",
    "axis",
    "source_layer2_column",
    "include_in_pilot",
    "feature_scope",
    "notes",
]

FEATURE_AXES = ("rx", "ry", "rz")
CANONICAL_NAMING_POLICY = "canonical_parent_child_axis"
DEFAULT_PILOT_MANIFEST = (
    Path(__file__).resolve().parents[2] / "config" / "group4_upper_body_pilot_feature_manifest.csv"
)


@dataclass(frozen=True)
class ManifestFeature:
    feature_name: str
    canonical_link_name: str
    parent_canonical: str
    child_canonical: str
    axis: str
    source_layer2_column: str
    include_in_pilot: bool
    feature_scope: str
    notes: str


class ManifestError(Exception):
    """Manifest load or resolution failure."""


def canonical_link_name(parent: str, child: str) -> str:
    return f"{parent}->{child}"


def canonical_feature_name(parent: str, child: str, axis: str) -> str:
    if axis not in FEATURE_AXES:
        raise ValueError(f"Invalid axis: {axis}")
    return f"{parent}_to_{child}_{axis}"


def load_pilot_manifest(path: Path | None = None) -> list[ManifestFeature]:
    manifest_path = path or DEFAULT_PILOT_MANIFEST
    if not manifest_path.is_file():
        raise ManifestError(f"Pilot manifest not found: {manifest_path}")

    df = pd.read_csv(manifest_path)
    missing = [col for col in MANIFEST_COLUMNS if col not in df.columns]
    if missing:
        raise ManifestError(f"Manifest missing columns: {missing}")

    features: list[ManifestFeature] = []
    for _, row in df.iterrows():
        include = str(row["include_in_pilot"]).strip().lower() in {"true", "1", "yes"}
        parent = str(row["parent_canonical"])
        child = str(row["child_canonical"])
        axis = str(row["axis"])
        expected_name = canonical_feature_name(parent, child, axis)
        feature_name = str(row["feature_name"])
        if feature_name != expected_name:
            raise ManifestError(
                f"Manifest feature_name {feature_name!r} != expected {expected_name!r}"
            )
        features.append(
            ManifestFeature(
                feature_name=feature_name,
                canonical_link_name=str(row["canonical_link_name"]),
                parent_canonical=parent,
                child_canonical=child,
                axis=axis,
                source_layer2_column=str(row["source_layer2_column"]),
                include_in_pilot=include,
                feature_scope=str(row["feature_scope"]),
                notes=str(row.get("notes", "")),
            )
        )
    return features


def pilot_feature_order(manifest: list[ManifestFeature]) -> list[str]:
    """Return ordered feature names for pilot exports (manifest order, pilot-included only)."""
    return [feature.feature_name for feature in manifest if feature.include_in_pilot]


def pilot_link_order(manifest: list[ManifestFeature]) -> list[tuple[str, str]]:
    """Unique parent-child pairs in manifest order."""
    seen: set[tuple[str, str]] = set()
    order: list[tuple[str, str]] = []
    for feature in manifest:
        if not feature.include_in_pilot:
            continue
        key = (feature.parent_canonical, feature.child_canonical)
        if key not in seen:
            seen.add(key)
            order.append(key)
    return order


def resolve_session_links_from_manifest(
    manifest: list[ManifestFeature],
    session_links: list[LinkRecord],
) -> tuple[list[str], dict[tuple[str, str], LinkRecord]]:
    """Map canonical parent-child identity to session link_ids.

    Returns selected link_ids in manifest order and a lookup by (parent, child).
    """
    by_canonical: dict[tuple[str, str], list[LinkRecord]] = {}
    for link in session_links:
        key = (link.parent_canonical, link.child_canonical)
        by_canonical.setdefault(key, []).append(link)

    selected_ids: list[str] = []
    resolved: dict[tuple[str, str], LinkRecord] = {}
    link_order = pilot_link_order(manifest)

    for parent, child in link_order:
        matches = by_canonical.get((parent, child), [])
        if not matches:
            raise ManifestError(
                f"Session missing canonical link {parent}->{child} required by pilot manifest"
            )
        if len(matches) > 1:
            raise ManifestError(
                f"Ambiguous canonical link {parent}->{child}: "
                f"{[link.link_id for link in matches]}"
            )
        link = matches[0]
        resolved[(parent, child)] = link
        selected_ids.append(link.link_id)

    return selected_ids, resolved


def manifest_axes_for_link(
    manifest: list[ManifestFeature],
    parent: str,
    child: str,
) -> list[str]:
    axes: list[str] = []
    for feature in manifest:
        if (
            feature.include_in_pilot
            and feature.parent_canonical == parent
            and feature.child_canonical == child
        ):
            axes.append(feature.axis)
    if axes != list(FEATURE_AXES):
        raise ManifestError(
            f"Link {parent}->{child} must have exactly rx/ry/rz in manifest; got {axes}"
        )
    return axes


def feature_column_name_from_manifest(feature: ManifestFeature) -> str:
    return feature.feature_name


def expected_pilot_feature_order(
    manifest: list[ManifestFeature],
    links_by_canonical: dict[tuple[str, str], LinkRecord],
) -> list[str]:
    names: list[str] = []
    for parent, child in pilot_link_order(manifest):
        link = links_by_canonical[(parent, child)]
        for feature in manifest:
            if (
                not feature.include_in_pilot
                or feature.parent_canonical != link.parent_canonical
                or feature.child_canonical != link.child_canonical
            ):
                continue
            names.append(feature.feature_name)
    return names
