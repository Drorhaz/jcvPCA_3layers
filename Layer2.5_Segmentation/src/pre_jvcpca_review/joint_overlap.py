"""Cross-session joint/link overlap and comparability detection.

Compares the canonical parent->child link structures of the Layer 2 outputs for
several sessions of one participant and classifies each candidate canonical link.

Direct comparability detection only. Composite rotation math is NOT implemented;
links that would require composite mapping are flagged and (downstream) blocked
unless an explicit harmonization manifest exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from pre_jvcpca_review.load_layer2 import LinkRecord
from pre_jvcpca_review.warnings import (
    SEVERITY_BLOCKING,
    WarningCollector,
)

# Classification labels
DIRECT = "directly_comparable"
COMPOSITE = "requires_composite_mapping"
NOT_COMPARABLE = "not_comparable"
MISSING_SOME = "missing_in_some_sessions"
AMBIGUOUS = "ambiguous_requires_user_decision"

JOINT_OVERLAP_COLUMNS = [
    "participant_id",
    "comparison_scope",
    "session_ids_compared",
    "canonical_link_name",
    "parent_canonical",
    "child_canonical",
    "axis",
    "present_in_sessions",
    "missing_in_sessions",
    "directly_comparable",
    "requires_composite_mapping",
    "not_comparable",
    "native_link_ids_by_session",
    "topology_warning",
    "recommended_action",
    "requires_user_decision",
    "classification",
]


@dataclass(frozen=True)
class OverlapRow:
    canonical_link_name: str
    parent_canonical: str
    child_canonical: str
    classification: str
    present_in_sessions: list[str]
    missing_in_sessions: list[str]
    native_link_ids_by_session: dict[str, str]
    topology_warning: str
    requires_user_decision: bool


def _composite_path_exists(
    parent: str, child: str, links: list[LinkRecord]
) -> bool:
    """True if parent reaches child via >=2 hops in this session's link graph."""
    adj: dict[str, set[str]] = {}
    for link in links:
        adj.setdefault(link.parent_canonical, set()).add(link.child_canonical)
    # BFS for a path length >= 2 (direct edge handled separately by caller)
    visited: set[str] = {parent}
    frontier = [(parent, 0)]
    while frontier:
        node, depth = frontier.pop()
        for nxt in adj.get(node, ()):  # noqa: SIM118
            if nxt == child and depth >= 1:
                return True
            if nxt not in visited and depth + 1 <= 6:
                visited.add(nxt)
                frontier.append((nxt, depth + 1))
    return False


def _recommended_action(classification: str) -> str:
    return {
        DIRECT: "include (direct canonical match across sessions)",
        MISSING_SOME: "exclude or restrict scope; link absent in some sessions",
        COMPOSITE: "do not treat as direct; requires explicit harmonization manifest",
        NOT_COMPARABLE: "exclude from cross-session Layer 3 matrix",
        AMBIGUOUS: "user must resolve duplicate/ambiguous link mapping",
    }.get(classification, "review")


def classify_links(
    session_links: dict[str, list[LinkRecord]],
    candidate_links: list[tuple[str, str]] | None = None,
) -> list[OverlapRow]:
    """Classify each candidate (parent, child) across the given sessions."""
    sessions = list(session_links.keys())

    # Build per-session lookup of canonical pair -> [link_ids]
    by_session: dict[str, dict[tuple[str, str], list[str]]] = {}
    for sid, links in session_links.items():
        d: dict[tuple[str, str], list[str]] = {}
        for link in links:
            d.setdefault((link.parent_canonical, link.child_canonical), []).append(link.link_id)
        by_session[sid] = d

    if candidate_links is None:
        pairs: set[tuple[str, str]] = set()
        for d in by_session.values():
            pairs.update(d.keys())
        candidate_links = sorted(pairs)

    rows: list[OverlapRow] = []
    for parent, child in candidate_links:
        present: list[str] = []
        missing: list[str] = []
        native: dict[str, str] = {}
        ambiguous = False
        composite_in_missing = False

        for sid in sessions:
            ids = by_session[sid].get((parent, child), [])
            if ids:
                present.append(sid)
                native[sid] = ";".join(ids)
                if len(ids) > 1:
                    ambiguous = True
            else:
                missing.append(sid)
                native[sid] = ""
                if _composite_path_exists(parent, child, session_links[sid]):
                    composite_in_missing = True

        topo = ""
        if ambiguous:
            classification = AMBIGUOUS
            topo = "duplicate native link ids for one canonical pair"
        elif not missing:
            classification = DIRECT
        elif composite_in_missing:
            classification = COMPOSITE
            topo = (
                "direct link in some sessions but only a multi-segment chain in others "
                "(e.g. Neck->Head vs Neck->Neck2->Head); composite mapping required"
            )
        elif present:
            classification = MISSING_SOME
            topo = "link absent (and no composite chain) in some sessions"
        else:
            classification = NOT_COMPARABLE
            topo = "link absent in all compared sessions"

        rows.append(
            OverlapRow(
                canonical_link_name=f"{parent}->{child}",
                parent_canonical=parent,
                child_canonical=child,
                classification=classification,
                present_in_sessions=present,
                missing_in_sessions=missing,
                native_link_ids_by_session=native,
                topology_warning=topo,
                requires_user_decision=classification in {COMPOSITE, AMBIGUOUS, MISSING_SOME},
            )
        )
    return rows


def overlap_dataframe(
    rows: list[OverlapRow],
    participant_id: str,
    session_ids: list[str],
) -> pd.DataFrame:
    scope = "single_session" if len(session_ids) <= 1 else f"{len(session_ids)}_session_compare"
    out_rows = []
    for r in rows:
        out_rows.append(
            {
                "participant_id": participant_id,
                "comparison_scope": scope,
                "session_ids_compared": ";".join(session_ids),
                "canonical_link_name": r.canonical_link_name,
                "parent_canonical": r.parent_canonical,
                "child_canonical": r.child_canonical,
                "axis": "rx;ry;rz",
                "present_in_sessions": ";".join(r.present_in_sessions),
                "missing_in_sessions": ";".join(r.missing_in_sessions),
                "directly_comparable": r.classification == DIRECT,
                "requires_composite_mapping": r.classification == COMPOSITE,
                "not_comparable": r.classification in {NOT_COMPARABLE, MISSING_SOME},
                "native_link_ids_by_session": "; ".join(
                    f"{sid}={lid}" for sid, lid in r.native_link_ids_by_session.items()
                ),
                "topology_warning": r.topology_warning,
                "recommended_action": _recommended_action(r.classification),
                "requires_user_decision": r.requires_user_decision,
                "classification": r.classification,
            }
        )
    return pd.DataFrame(out_rows, columns=JOINT_OVERLAP_COLUMNS)


def write_joint_overlap_table(df: pd.DataFrame, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return out_path


def non_comparable_required_features(
    overlap_df: pd.DataFrame,
    required_links: list[tuple[str, str]],
) -> list[str]:
    """Return canonical_link_names among required links that are not directly comparable."""
    required = {f"{p}->{c}" for p, c in required_links}
    bad = overlap_df[
        overlap_df["canonical_link_name"].isin(required)
        & (~overlap_df["directly_comparable"])
    ]
    return sorted(bad["canonical_link_name"].tolist())


def canonical_names_to_link_tuples(names: list[str]) -> list[tuple[str, str]]:
    """Convert ``Parent->Child`` names to ``(parent, child)`` tuples."""
    out: list[tuple[str, str]] = []
    for name in names:
        if "->" not in name:
            continue
        parent, child = name.split("->", 1)
        out.append((parent, child))
    return out


def emit_joint_comparability_warnings(
    collector: WarningCollector,
    overlap_df: pd.DataFrame,
    scope_links: list[tuple[str, str]],
    *,
    harmonization_manifest_exists: bool = False,
    **ident_kw: str,
) -> None:
    """Emit comparability warnings only for joints in the user's current selection."""
    if overlap_df is None or overlap_df.empty:
        return

    if not scope_links:
        return

    scoped_bad = non_comparable_required_features(overlap_df, scope_links)
    if scoped_bad and not harmonization_manifest_exists:
        for name in scoped_bad:
            collector.emit(
                "joint.not_directly_comparable",
                SEVERITY_BLOCKING,
                "joint_alignment",
                f"Selected link {name} is not directly comparable across this "
                "participant's sessions and no harmonization manifest exists.",
                recommended_action=(
                    "Deselect this link, provide a harmonization manifest, or restrict scope."
                ),
                canonical_link_name=name,
                **ident_kw,
            )
