"""Explanation-first verdict model (PROGRAM_GUI_OPTIMIZATION_PLAN §3.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

HEADLINE_READY = "Ready"
HEADLINE_CAUTION = "Usable with caution"
HEADLINE_NOT_RECOMMENDED = "Not recommended"
HEADLINE_BLOCKED = "Blocked"
HEADLINE_MISSING = "Missing / insufficient data"

SEVERITY_ADVISORY = "advisory"
SEVERITY_STRONG_WARNING = "strong_warning"
SEVERITY_BLOCKING = "blocking"

SCOPE_WHOLE_SEGMENT = "whole_segment"
SCOPE_LINK_SUBSET = "link_subset"
SCOPE_FRAME_SUBSET = "frame_subset"
SCOPE_SESSION = "session"


@dataclass(frozen=True)
class EvidenceItem:
    issue_type: str
    scope: str
    severity: str
    qc_source: str
    blocks_layer3: bool
    affected_fraction: float | None = None
    affected_frame_count: int | None = None
    gap_duration_s: float | None = None
    affected_links: tuple[str, ...] = ()
    affected_body_regions: tuple[str, ...] = ()
    affected_sessions: tuple[str, ...] = ()
    affected_repetitions: tuple[str, ...] = ()
    affected_p_phases: tuple[str, ...] = ()
    threshold_key: str = ""
    threshold_value: str = ""
    observed_value: str = ""
    detail: str = ""


@dataclass(frozen=True)
class VerdictCard:
    headline: str
    explanation: str
    evidence: tuple[EvidenceItem, ...] = ()
    consequence: str = ""
    action: str = ""
    subject_id: str = ""
    layer: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline": self.headline,
            "explanation": self.explanation,
            "consequence": self.consequence,
            "action": self.action,
            "subject_id": self.subject_id,
            "layer": self.layer,
            "evidence": [
                {
                    "issue_type": e.issue_type,
                    "scope": e.scope,
                    "severity": e.severity,
                    "qc_source": e.qc_source,
                    "blocks_layer3": e.blocks_layer3,
                    "affected_fraction": e.affected_fraction,
                    "affected_frame_count": e.affected_frame_count,
                    "gap_duration_s": e.gap_duration_s,
                    "affected_links": list(e.affected_links),
                    "affected_body_regions": list(e.affected_body_regions),
                    "threshold_key": e.threshold_key,
                    "threshold_value": e.threshold_value,
                    "observed_value": e.observed_value,
                    "detail": e.detail,
                }
                for e in self.evidence
            ],
        }


def headline_from_status(status: str) -> str:
    s = status.lower()
    if s in {"pass", "ready", "exported"}:
        return HEADLINE_READY
    if s in {"warn", "warning", "strong_warning", "caution", "proceed_with_caution", "review_required"}:
        return HEADLINE_CAUTION
    if s in {"fail", "not_recommended"}:
        return HEADLINE_NOT_RECOMMENDED
    if s in {"block", "blocking", "blocked"}:
        return HEADLINE_BLOCKED
    return HEADLINE_MISSING


def _evidence_from_layer(
    layer_name: str,
    status: str,
    summary: str,
    evidence_text: str,
    threshold_keys: tuple[str, ...],
) -> EvidenceItem:
    blocks = status.lower() in {"block", "blocking", "fail", "missing"}
    severity = SEVERITY_BLOCKING if blocks else (
        SEVERITY_STRONG_WARNING if status.lower() in {"strong_warning", "fail"} else SEVERITY_ADVISORY
    )
    return EvidenceItem(
        issue_type=f"{layer_name.lower()}_status",
        scope=SCOPE_SESSION,
        severity=severity,
        qc_source=layer_name,
        blocks_layer3=blocks,
        threshold_key=threshold_keys[0] if threshold_keys else "",
        detail=evidence_text or summary,
    )


def verdict_from_readiness_cell(cell: Any) -> VerdictCard:
    """Build VerdictCard from a ReadinessCell."""
    parts = [cell.l1.summary, cell.l2.summary, cell.l2_5.summary]
    explanation = " · ".join(p for p in parts if p)
    evidence = (
        _evidence_from_layer("L1", cell.l1.status, cell.l1.summary, cell.l1.evidence, cell.l1.threshold_keys),
        _evidence_from_layer("L2", cell.l2.status, cell.l2.summary, cell.l2.evidence, cell.l2.threshold_keys),
        _evidence_from_layer("L2.5", cell.l2_5.status, cell.l2_5.summary, cell.l2_5.evidence, cell.l2_5.threshold_keys),
    )
    headline = headline_from_status(cell.overall)
    if headline == HEADLINE_CAUTION:
        consequence = (
            "Downstream Layer 3 may proceed for this P-phase, but interpret link- or frame-level "
            "cautions narrowly."
        )
        action = "Include with caution; review evidence table before strong segment-specific claims."
    elif headline == HEADLINE_READY:
        consequence = "Segment meets governed readiness gates for Layer 3 selection."
        action = "Eligible for Stage 5 verification and Stage 6 analysis intent."
    elif headline == HEADLINE_NOT_RECOMMENDED:
        consequence = "Layer 3 interpretation may be misleading without addressing L2 QC concerns."
        action = "Review L2 drill-down; consider excluding this P-phase from primary comparisons."
    elif headline == HEADLINE_BLOCKED:
        consequence = "Layer 3 must not use this segment without explicit logged override (G6+)."
        action = "Exclude from analysis intent or re-run upstream pipeline."
    else:
        consequence = "Insufficient indexed evidence to support Layer 3 selection."
        action = "Complete discovery (Stage 1) and upstream exports before analysis."

    return VerdictCard(
        headline=headline,
        explanation=explanation,
        evidence=evidence,
        consequence=consequence,
        action=action,
        subject_id=f"{cell.session_id}::{cell.p_phase}",
        layer="readiness",
    )


def verdict_from_coverage_row(row: dict[str, Any]) -> VerdictCard:
    status = str(row.get("coverage_status", ""))
    session_id = str(row.get("session_id", ""))
    label = str(row.get("exercise_export_label", ""))
    subject = f"{session_id}::{label}"

    if status == "exported":
        qc = str(row.get("qc_status", "")).lower()
        safe = str(row.get("layer3_safe", "")).lower()
        if safe == "false" or qc == "blocking":
            headline = HEADLINE_BLOCKED
            explanation = (
                f"Segment {label} is exported but manifest reports qc_status={row.get('qc_status')} "
                f"and layer3_safe={row.get('layer3_safe')}."
            )
            blocks = True
        elif qc == "warning":
            headline = HEADLINE_CAUTION
            explanation = (
                f"Segment {label} is exported (frames {row.get('start_frame')}–{row.get('end_frame')}) "
                f"with qc_status=warning; review window warnings before Layer 3."
            )
            blocks = False
        else:
            headline = HEADLINE_READY
            explanation = (
                f"Segment {label} is exported for session {session_id} "
                f"(frames {row.get('start_frame')}–{row.get('end_frame')})."
            )
            blocks = False
    elif status == "requested_not_exported":
        headline = HEADLINE_MISSING
        explanation = (
            f"Exercise {label} (id {row.get('exercise_id')}) is in the segmentation xlsx "
            f"but not in the central export manifest."
        )
        blocks = True
    elif status == "missing_from_sheet":
        headline = HEADLINE_CAUTION
        explanation = f"Manifest lists export {label} for {session_id} but no matching xlsx row was found."
        blocks = False
    else:
        headline = HEADLINE_READY
        explanation = f"Exercise {label} exists in xlsx but is not currently requested for export."
        blocks = False

    evidence = (
        EvidenceItem(
            issue_type="segmentation_coverage",
            scope=SCOPE_WHOLE_SEGMENT,
            severity=SEVERITY_BLOCKING if blocks else SEVERITY_ADVISORY,
            qc_source=str(row.get("segmentation_source") or row.get("manifest_path") or "xlsx/manifest"),
            blocks_layer3=blocks,
            affected_sessions=(session_id,),
            detail=status,
        ),
    )
    return VerdictCard(
        headline=headline,
        explanation=explanation,
        evidence=evidence,
        consequence="Export and QC state determine Stage 5 verification eligibility.",
        action="Run L2.5 export (G6+) for missing segments; verify QC on Stage 5.",
        subject_id=subject,
        layer="segmentation",
    )


def verdict_from_inclusion(rec: Any) -> VerdictCard:
    headline_map = {
        "ready": HEADLINE_READY,
        "caution": HEADLINE_CAUTION,
        "not_recommended": HEADLINE_NOT_RECOMMENDED,
        "blocked": HEADLINE_BLOCKED,
        "missing": HEADLINE_MISSING,
        "insufficient_data": HEADLINE_MISSING,
    }
    headline = headline_map.get(str(rec.verdict), HEADLINE_MISSING)
    evidence = tuple(
        EvidenceItem(
            issue_type="inclusion_advisory",
            scope=SCOPE_WHOLE_SEGMENT,
            severity=SEVERITY_BLOCKING if rec.verdict == "blocked" else SEVERITY_ADVISORY,
            qc_source=item.source,
            blocks_layer3=rec.verdict in {"blocked", "missing"},
            threshold_key=item.threshold_key,
            detail=item.detail,
        )
        for item in rec.evidence
    )
    return VerdictCard(
        headline=headline,
        explanation=rec.summary,
        evidence=evidence,
        consequence="Inclusion advisory informs Stage 5 verification; not a final exclusion decision.",
        action="Review evidence; confirm on Stage 5 before Stage 6 analysis intent.",
        subject_id=f"{rec.session_id}::{rec.p_phase}",
        layer="inclusion",
    )
