"""Pre-export Layer 1 <-> Layer 2 pairing / identity / provenance gate.

Minimal critical-checks wrapper (per audit R2). Deeper unification with
`layer2_motive.segmentation.validate_inputs` is intentionally left for later to
avoid a broad refactor; that validator requires the normalized single-folder
layout, whereas the real output trees are stage-folder based.
"""

from __future__ import annotations

import pandas as pd

from pre_jvcpca_review.session_index import parse_session_key
from pre_jvcpca_review.warnings import (
    SEVERITY_BLOCKING,
    SEVERITY_STRONG,
    SEVERITY_WARNING,
    WarningCollector,
)


def _ident_kw(row: pd.Series) -> dict[str, str]:
    return {
        "participant_id": str(row.get("participant_id", "")),
        "session_id": str(row.get("session_id", "")),
        "timepoint": str(row.get("timepoint", "")),
        "part_id": str(row.get("part_id", "")),
        "repetition_id": str(row.get("repetition_id", "")),
    }


def run_pairing_gate(row: pd.Series, collector: WarningCollector) -> bool:
    """Append warnings for a paired session row. Return True if export may proceed."""
    kw = _ident_kw(row)

    l1_dir = str(row.get("layer1_run_dir", "") or "")
    l2_dir = str(row.get("layer2_run_dir", "") or "")

    if not l1_dir:
        collector.emit(
            "pairing.missing_layer1", SEVERITY_BLOCKING, "pairing",
            "No Layer 1 output found for this session.",
            recommended_action="Run Layer 1 QC for this session or pick another session.",
            source_layer="layer1", **kw,
        )
    if not l2_dir:
        collector.emit(
            "pairing.missing_layer2", SEVERITY_BLOCKING, "pairing",
            "No Layer 2 export found for this session.",
            recommended_action="Run Layer 2 kinematics for this session or pick another.",
            source_layer="layer2", **kw,
        )

    # Session identity: both dirs must parse to the same canonical key.
    if l1_dir and l2_dir:
        k1 = parse_session_key(l1_dir)
        k2 = parse_session_key(l2_dir)
        if k1 is None or k2 is None or k1.session_id != k2.session_id:
            collector.emit(
                "pairing.identity_mismatch", SEVERITY_BLOCKING, "pairing",
                f"Layer 1 and Layer 2 directories resolve to different sessions "
                f"(L1={k1.session_id if k1 else '?'}, L2={k2.session_id if k2 else '?'}).",
                recommended_action="Do not export. Re-pair the correct L1/L2 runs.",
                **kw,
            )

    # Source-file compatibility (best-effort; both encode the same session key).
    src1 = str(row.get("layer1_source_file", "") or "")
    src2 = str(row.get("layer2_source_file", "") or "")
    k1s = parse_session_key(src1)
    k2s = parse_session_key(src2)
    if src1 and src2 and k1s and k2s and k1s.session_id != k2s.session_id:
        collector.emit(
            "pairing.source_file_mismatch", SEVERITY_BLOCKING, "pairing",
            f"Layer 1 source file ({src1}) and Layer 2 source file ({src2}) "
            "appear to be different recordings.",
            recommended_action="Do not export. Verify both layers used the same CSV.",
            source_file=f"L1={src1}; L2={src2}", **kw,
        )
    elif not src1 or not src2 or src1 == "unknown" or src2 == "unknown":
        collector.emit(
            "pairing.source_file_unverified", SEVERITY_WARNING, "pairing",
            "Could not confirm Layer 1 / Layer 2 source-file identity (missing metadata).",
            recommended_action="Confirm both layers processed the same recording.",
            source_file=f"L1={src1 or '?'}; L2={src2 or '?'}", **kw,
        )

    # Frame range compatibility.
    n1 = row.get("n_frames_layer1", "")
    n2 = row.get("n_frames_layer2", "")
    if isinstance(n1, (int,)) and isinstance(n2, (int,)) and n1 and n2 and n1 != n2:
        collector.emit(
            "pairing.frame_count_mismatch", SEVERITY_BLOCKING, "pairing",
            f"Layer 1 frame count ({n1}) != Layer 2 frame count ({n2}).",
            recommended_action="Do not export. Frame ranges must match for join.",
            start_frame=0, end_frame=max(int(n1), int(n2)) - 1, **kw,
        )

    # Provenance availability (non-blocking but strong).
    if not str(row.get("layer2_provenance_path", "") or ""):
        collector.emit(
            "pairing.missing_layer2_provenance", SEVERITY_STRONG, "provenance",
            "Layer 2 provenance (session manifest) not found.",
            recommended_action="Verify Layer 2 export completeness before trusting output.",
            source_layer="layer2", **kw,
        )
    if str(row.get("layer2_git_commit", "unknown")) == "unknown":
        collector.emit(
            "pairing.layer2_git_commit_unknown", SEVERITY_WARNING, "provenance",
            "Layer 2 git commit is unknown (provenance cannot be pinned).",
            recommended_action="Record git commit / config hash in Layer 2 exports.",
            source_layer="layer2", **kw,
        )

    # Layer 1 marker-set evidence availability.
    if str(row.get("marker_set_id", "unknown")) == "unknown":
        collector.emit(
            "pairing.missing_marker_set", SEVERITY_WARNING, "layer1_evidence",
            "Layer 1 marker-set id/hash not found (cannot compare marker sets).",
            recommended_action="Ensure Layer 1 emits layer1_marker_set.csv.",
            source_layer="layer1", **kw,
        )

    return not collector.has_blocking
