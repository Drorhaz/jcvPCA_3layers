"""G3 advisory inclusion recommendations (participant / session / P-phase)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from project_status import GAGA_P_PHASES, ProjectSnapshot
from readiness import ReadinessCell, ReadinessMatrix, build_readiness_matrix

# Advisory verdicts — not final exclusion decisions.
VERDICT_READY = "ready"
VERDICT_CAUTION = "caution"
VERDICT_NOT_RECOMMENDED = "not_recommended"
VERDICT_BLOCKED = "blocked"
VERDICT_INSUFFICIENT = "insufficient_data"
VERDICT_MISSING = "missing"

ADVISORY_LABEL = "Advisory — manual review required before Layer 3 inclusion."

_READINESS_TO_INCLUSION = {
    "pass": VERDICT_READY,
    "warn": VERDICT_CAUTION,
    "strong_warning": VERDICT_CAUTION,
    "fail": VERDICT_NOT_RECOMMENDED,
    "block": VERDICT_BLOCKED,
    "missing": VERDICT_MISSING,
    "unknown": VERDICT_INSUFFICIENT,
}

_INCLUSION_RANK = {
    VERDICT_READY: 0,
    VERDICT_CAUTION: 1,
    VERDICT_NOT_RECOMMENDED: 2,
    VERDICT_INSUFFICIENT: 3,
    VERDICT_MISSING: 4,
    VERDICT_BLOCKED: 5,
}


@dataclass(frozen=True)
class EvidenceItem:
    source: str  # registry | manifest | session_index | l2_qc | l2_5_export
    field: str
    detail: str
    threshold_key: str = ""


@dataclass(frozen=True)
class InclusionRecommendation:
    participant_id: str
    timepoint: str
    repetition: str
    p_phase: str
    session_id: str
    verdict: str
    summary: str
    evidence: tuple[EvidenceItem, ...] = ()
    threshold_keys: tuple[str, ...] = ()


@dataclass
class InclusionReport:
    recommendations: list[InclusionRecommendation] = field(default_factory=list)
    advisory_label: str = ADVISORY_LABEL


def _cell_evidence(cell: ReadinessCell) -> tuple[EvidenceItem, ...]:
    items: list[EvidenceItem] = []
    for layer_name, layer in (("L1", cell.l1), ("L2", cell.l2), ("L2.5", cell.l2_5)):
        items.append(
            EvidenceItem(
                source="registry" if layer.threshold_keys else "manifest",
                field=f"{layer_name}_status",
                detail=layer.evidence or layer.summary,
                threshold_key=layer.threshold_keys[0] if layer.threshold_keys else "",
            )
        )
    return tuple(items)


def _inclusion_from_cell(cell: ReadinessCell) -> InclusionRecommendation:
    verdict = _READINESS_TO_INCLUSION.get(cell.overall, VERDICT_INSUFFICIENT)
    keys = tuple(dict.fromkeys(cell.l1.threshold_keys + cell.l2.threshold_keys + cell.l2_5.threshold_keys))
    summary = {
        VERDICT_READY: "Structurally eligible for Layer 3 selection (QC pass).",
        VERDICT_CAUTION: "Usable with caution — review warnings before interpreting JcvPCA.",
        VERDICT_NOT_RECOMMENDED: "Not recommended — L2 fail or persistent QC concern.",
        VERDICT_BLOCKED: "Blocked — export or session QC prevents Layer 3 use.",
        VERDICT_MISSING: "Missing export or L1 output for this P-phase.",
        VERDICT_INSUFFICIENT: "Insufficient indexed evidence to advise inclusion.",
    }[verdict]
    return InclusionRecommendation(
        participant_id=cell.participant_id,
        timepoint=cell.timepoint,
        repetition=cell.repetition,
        p_phase=cell.p_phase,
        session_id=cell.session_id,
        verdict=verdict,
        summary=summary,
        evidence=_cell_evidence(cell),
        threshold_keys=keys,
    )


def build_inclusion_report(snapshot: ProjectSnapshot, matrix: ReadinessMatrix | None = None) -> InclusionReport:
    """Map G2 readiness cells to G3 advisory inclusion recommendations."""
    if matrix is None:
        matrix = build_readiness_matrix(snapshot)
    return InclusionReport(
        recommendations=[_inclusion_from_cell(c) for c in matrix.cells],
    )


def filter_inclusion_report(
    report: InclusionReport,
    *,
    participant_ids: list[str] | None = None,
    timepoints: list[str] | None = None,
    repetitions: list[str] | None = None,
    p_phases: list[str] | None = None,
    verdicts: list[str] | None = None,
) -> list[InclusionRecommendation]:
    out = report.recommendations
    if participant_ids:
        out = [r for r in out if r.participant_id in participant_ids]
    if timepoints:
        out = [r for r in out if r.timepoint in timepoints]
    if repetitions:
        out = [r for r in out if r.repetition in repetitions]
    if p_phases:
        out = [r for r in out if r.p_phase in p_phases]
    if verdicts:
        out = [r for r in out if r.verdict in verdicts]
    return out


def summarize_inclusion(report: InclusionReport) -> dict[str, int]:
    counts: dict[str, int] = {v: 0 for v in _READINESS_TO_INCLUSION.values()}
    for rec in report.recommendations:
        counts[rec.verdict] = counts.get(rec.verdict, 0) + 1
    return counts


def worst_inclusion_verdict(verdicts: list[str]) -> str:
    if not verdicts:
        return VERDICT_INSUFFICIENT
    return max(verdicts, key=lambda v: _INCLUSION_RANK.get(v, 99))
