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
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
DEFAULT_PILOT_MANIFEST = CONFIG_DIR / "group4_upper_body_pilot_feature_manifest.csv"
CORE_MANIFEST_671 = CONFIG_DIR / "group4_core_14link_within_671_feature_manifest.csv"
CORE_MANIFEST_252 = CONFIG_DIR / "group4_core_16link_within_252_feature_manifest.csv"
PARTICIPANT_CORE_MANIFESTS: dict[str, Path] = {
    "671": CORE_MANIFEST_671,
    "252": CORE_MANIFEST_252,
}

# Session-native link pairs accepted as equivalent to a manifest canonical pair.
# Export columns always use the manifest key (e.g. Neck_to_Head_*), not the alias stem.
CANONICAL_LINK_ALIASES: dict[tuple[str, str], tuple[tuple[str, str], ...]] = {
    ("Neck", "Head"): (("Neck2", "Head"),),
}


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


def core_manifest_path_for_participant(participant_id: str) -> Path:
    """Return the within-participant core feature manifest for Layer 3 prep exports."""
    path = PARTICIPANT_CORE_MANIFESTS.get(str(participant_id))
    if path is None:
        return DEFAULT_PILOT_MANIFEST
    if not path.is_file():
        raise ManifestError(
            f"Core feature manifest not found for participant {participant_id}: {path}"
        )
    return path


def pilot_link_names(manifest: list[ManifestFeature]) -> list[str]:
    """Canonical link names in manifest order."""
    return [canonical_link_name(p, c) for p, c in pilot_link_order(manifest)]


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


def canonical_link_aliases(parent: str, child: str) -> tuple[tuple[str, str], ...]:
    """Return session-native (parent, child) pairs accepted for a manifest canonical link."""
    direct = ((parent, child),)
    extra = CANONICAL_LINK_ALIASES.get((parent, child), ())
    return direct + extra


def resolve_session_link_for_manifest_pair(
    parent: str,
    child: str,
    by_canonical: dict[tuple[str, str], list[LinkRecord]],
) -> LinkRecord:
    """Map manifest canonical pair to one session link (direct match or alias)."""
    for alias_parent, alias_child in canonical_link_aliases(parent, child):
        matches = by_canonical.get((alias_parent, alias_child), [])
        if not matches:
            continue
        if len(matches) > 1:
            raise ManifestError(
                f"Ambiguous canonical link {parent}->{child} via "
                f"{alias_parent}->{alias_child}: {[link.link_id for link in matches]}"
            )
        return matches[0]
    raise ManifestError(
        f"Session missing canonical link {parent}->{child} required by pilot manifest"
    )


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
        link = resolve_session_link_for_manifest_pair(parent, child, by_canonical)
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
        for feature in manifest:
            if (
                not feature.include_in_pilot
                or feature.parent_canonical != parent
                or feature.child_canonical != child
            ):
                continue
            names.append(feature.feature_name)
    return names
