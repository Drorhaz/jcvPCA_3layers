"""Artifact comparability helpers for G2 read-only GUI (stdlib only)."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any


class ComparabilityStatus(str, Enum):
    COMPARABLE = "comparable"
    NOT_DIRECTLY_COMPARABLE = "not_directly_comparable"
    UNKNOWN = "unknown"
    PRE_REGISTRY_CANONICAL = "pre_registry_canonical"


def load_artifact_science_hash(artifact_dir: Path) -> str | None:
    """Return science hash from ``_config_snapshot/config_hash.json`` if present."""
    snap = artifact_dir / "_config_snapshot" / "config_hash.json"
    if not snap.is_file():
        return None
    import json

    try:
        meta = json.loads(snap.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    value = meta.get("science_hash")
    return str(value) if value else None


def comparability_status(
    artifact_science_hash: str | None,
    current_science_hash: str,
    *,
    is_canonical_batch: bool = False,
) -> ComparabilityStatus:
    """Compare artifact config hash to the live registry science hash."""
    if artifact_science_hash is None:
        if is_canonical_batch:
            return ComparabilityStatus.PRE_REGISTRY_CANONICAL
        return ComparabilityStatus.UNKNOWN
    if artifact_science_hash == current_science_hash:
        return ComparabilityStatus.COMPARABLE
    return ComparabilityStatus.NOT_DIRECTLY_COMPARABLE


def comparability_banner_text(
    status: ComparabilityStatus,
    *,
    artifact_label: str,
    artifact_hash: str | None,
    current_hash: str,
) -> str:
    """Human-readable banner for G2 pages."""
    hash_short = lambda h: f"{h[:12]}…" if h and len(h) > 12 else (h or "—")
    lines = [
        f"**Artifact:** {artifact_label}",
        f"**Artifact config hash:** {hash_short(artifact_hash)}",
        f"**Current registry science hash:** {hash_short(current_hash)}",
    ]
    if status == ComparabilityStatus.COMPARABLE:
        lines.append("**Status:** comparable — generated under the current registry.")
    elif status == ComparabilityStatus.NOT_DIRECTLY_COMPARABLE:
        lines.append(
            "**Status:** not directly comparable — registry differs from artifact snapshot."
        )
    elif status == ComparabilityStatus.PRE_REGISTRY_CANONICAL:
        lines.append(
            "**Status:** pre-registry canonical — frozen batch predates `_config_snapshot/`; "
            "treat as authoritative for poster-era results, not hash-comparable to G1 registry."
        )
    else:
        lines.append(
            "**Status:** unknown — no stored config snapshot on this artifact."
        )
    return "\n\n".join(lines)


def threshold_badge_flags(threshold: Any) -> dict[str, bool]:
    """Derive G2 badge booleans from a ``Threshold`` dataclass."""
    return {
        "differs_from_default": threshold.differs_from_default,
        "differs_from_canonical": threshold.differs_from_canonical_batch,
        "differs_from_scope_approved": threshold.differs_from_scope_approved,
        "scope_locked": threshold.locked_by_scope,
        "requires_approval": threshold.requires_approval,
        "gui_editable_later": threshold.gui_editable,
    }
