"""Additive Layer 5 contract deliverables for Layer 2.5 / Layer 3 handoff."""

from __future__ import annotations

from typing import Any

import pandas as pd

from motive_qc.core import QCResult
from motive_qc.handoff import build_layer1_qc_handoff
from motive_qc.marker_gap_evidence import build_layer1_marker_gap_evidence
from motive_qc.marker_names import enrich_marker_level_tables
from motive_qc.marker_set import build_layer1_marker_set
from motive_qc.session_evidence import (
    append_evidence_to_session_summary,
    compute_session_evidence,
)


def build_layer5_contract_tables(
    layer1: QCResult,
    layer2: QCResult,
    layer3: QCResult | None,
    layer5_tables: dict[str, pd.DataFrame],
    config: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    """Build marker-set, evidence, handoff, and enriched marker-level tables."""
    session = layer1.session
    assert session is not None
    inventory = session.marker_inventory
    md = session.metadata

    marker_set = build_layer1_marker_set(md, inventory, config)
    marker_set_row = marker_set.iloc[0]

    qc_mask = layer5_tables.get("qc_mask", pd.DataFrame())
    qc_mask_intervals = layer5_tables.get("qc_mask_intervals", pd.DataFrame())
    gaps_over_0p5s = layer5_tables.get("gaps_over_0p5s", pd.DataFrame())
    gap_events = layer2.tables.get("gap_events", pd.DataFrame())

    n_frames = int(md.get("n_frames", len(qc_mask)))
    min_frame = int(md.get("start_frame", 0))
    config = dict(config)
    config["_session_duration_seconds"] = float(md.get("duration_seconds", 0.0))

    marker_gap_evidence = build_layer1_marker_gap_evidence(
        gap_events,
        gaps_over_0p5s,
        inventory,
        config,
        n_frames=n_frames,
        min_frame=min_frame,
    )

    session_summary = layer2.tables.get("session_summary", pd.DataFrame())
    evidence = compute_session_evidence(
        qc_mask, qc_mask_intervals, gaps_over_0p5s, marker_gap_evidence
    )
    session_summary_out = append_evidence_to_session_summary(session_summary, evidence)

    unlabeled = layer2.tables.get("unlabeled_marker_summary", pd.DataFrame())
    handoff = build_layer1_qc_handoff(
        qc_mask_intervals,
        marker_set_row,
        md,
        config,
        unlabeled_summary=unlabeled,
    )

    enriched = enrich_marker_level_tables(layer5_tables, inventory)
    if "quarantined_markers" in layer2.tables:
        enriched["quarantined_markers"] = enrich_marker_level_tables(
            {"quarantined_markers": layer2.tables["quarantined_markers"]},
            inventory,
        )["quarantined_markers"]

    out = {
        "layer1_marker_set": marker_set,
        "layer1_marker_gap_evidence": marker_gap_evidence,
        "layer1_qc_handoff": handoff,
        "session_summary": session_summary_out,
    }
    for key in (
        "gaps_over_0p2s",
        "gaps_over_0p5s",
        "artifact_events",
        "segment_length_qc",
        "quarantined_markers",
    ):
        if key in enriched:
            out[key] = enriched[key]
    return out
