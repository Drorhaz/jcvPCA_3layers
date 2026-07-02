"""G3 comparison-readiness evaluation (T1–T2, T1–T3, etc.) — read-only."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from inclusion_recommendations import (
    ADVISORY_LABEL,
    VERDICT_BLOCKED,
    VERDICT_CAUTION,
    VERDICT_INSUFFICIENT,
    VERDICT_MISSING,
    VERDICT_NOT_RECOMMENDED,
    VERDICT_READY,
    EvidenceItem,
    InclusionReport,
    build_inclusion_report,
    worst_inclusion_verdict,
)
from project_status import GAGA_P_PHASES, ProjectSnapshot
from readiness import build_readiness_matrix

COMPARISON_READY = VERDICT_READY
COMPARISON_CAUTION = VERDICT_CAUTION
COMPARISON_NOT_RECOMMENDED = VERDICT_NOT_RECOMMENDED
COMPARISON_BLOCKED = VERDICT_BLOCKED
COMPARISON_INSUFFICIENT = VERDICT_INSUFFICIENT


@dataclass(frozen=True)
class ComparisonRequest:
    participant_id: str
    timepoint_a: str
    timepoint_b: str
    p_phases: tuple[str, ...] = GAGA_P_PHASES
    repetitions: tuple[str, ...] = ("R1", "R2")


@dataclass(frozen=True)
class ComparisonRecommendation:
    request: ComparisonRequest
    verdict: str
    summary: str
    evidence: tuple[EvidenceItem, ...] = ()
    threshold_keys: tuple[str, ...] = ()
    segment_rows_found: int = 0
    segment_rows_expected: int = 0
    feature_schema_ids: tuple[str, ...] = ()
    comparable_link_count: int | None = None
    advisory_label: str = ADVISORY_LABEL


def _manifest_rows_for(
    snapshot: ProjectSnapshot,
    participant_id: str,
    timepoint: str,
    repetition: str,
    p_phase: str,
) -> list[dict[str, Any]]:
    return [
        r
        for r in snapshot.l25_manifest_rows
        if str(r.get("participant_id")) == participant_id
        and str(r.get("timepoint")) == timepoint
        and str(r.get("repetition")) == repetition
        and str(r.get("gaga_exercise_label")) == p_phase
        and str(r.get("export_granularity")) == "per_exercise"
    ]


def _inclusion_lookup(report: InclusionReport) -> dict[tuple[str, str, str, str], str]:
    return {
        (r.participant_id, r.timepoint, r.repetition, r.p_phase): r.verdict
        for r in report.recommendations
    }


def _matching_rules(snapshot: ProjectSnapshot) -> dict[str, Any]:
    matching = snapshot.config.raw_by_file.get("segment_selection.yaml", {}).get("matching", {})
    return {
        "require_same_participant": bool(
            matching.get("require_same_participant", {}).get("value", True)
        ),
        "require_same_feature_schema_id": bool(
            matching.get("require_same_feature_schema_id", {}).get("value", True)
        ),
        "warn_on_cross_timepoint_mix": bool(
            matching.get("warn_on_cross_timepoint_mix", {}).get("value", True)
        ),
    }


def evaluate_comparison_readiness(
    snapshot: ProjectSnapshot,
    request: ComparisonRequest,
    *,
    inclusion_report: InclusionReport | None = None,
    check_comparable_links: bool = False,
) -> ComparisonRecommendation:
    """Evaluate whether a cross-timepoint comparison is structurally valid."""
    if inclusion_report is None:
        inclusion_report = build_inclusion_report(snapshot, build_readiness_matrix(snapshot))

    inclusion = _inclusion_lookup(inclusion_report)
    rules = _matching_rules(snapshot)
    evidence: list[EvidenceItem] = []
    threshold_keys: list[str] = [
        "matching.require_same_feature_schema_id",
        "matching.warn_on_cross_timepoint_mix",
    ]

    expected = len(request.repetitions) * len(request.p_phases) * 2
    found_rows: list[dict[str, Any]] = []
    side_verdicts: list[str] = []

    for repetition in request.repetitions:
        for p_phase in request.p_phases:
            for timepoint in (request.timepoint_a, request.timepoint_b):
                key = (request.participant_id, timepoint, repetition, p_phase)
                side_verdicts.append(inclusion.get(key, VERDICT_MISSING))
                rows = _manifest_rows_for(
                    snapshot, request.participant_id, timepoint, repetition, p_phase
                )
                if rows:
                    found_rows.extend(rows)
                else:
                    evidence.append(
                        EvidenceItem(
                            source="manifest",
                            field="layer25_export_manifest.csv",
                            detail=f"No export row for {key}",
                        )
                    )

    schema_ids = sorted(
        {str(r.get("feature_schema_id", "")) for r in found_rows if r.get("feature_schema_id")}
    )
    if rules["require_same_feature_schema_id"] and len(schema_ids) > 1:
        evidence.append(
            EvidenceItem(
                source="registry",
                field="feature_schema_id",
                detail=f"Mixed feature schemas across selection: {schema_ids}",
                threshold_key="matching.require_same_feature_schema_id",
            )
        )

    qc_blocking = [
        r for r in found_rows
        if str(r.get("qc_status", "")).lower() == "blocking"
        or str(r.get("layer3_safe", "")).lower() == "false"
    ]
    if qc_blocking:
        evidence.append(
            EvidenceItem(
                source="manifest",
                field="qc_status / layer3_safe",
                detail=f"{len(qc_blocking)} segment(s) blocking or not layer3_safe",
                threshold_key="layer2_5.block_if",
            )
        )
        threshold_keys.append("layer2_5.block_if")

    comparable_count: int | None = None
    if check_comparable_links and found_rows:
        comparable_count = _try_comparable_link_count(found_rows)

    if found_rows and len(found_rows) < expected:
        verdict = COMPARISON_INSUFFICIENT
        summary = (
            f"Insufficient segment coverage for {request.timepoint_a}–{request.timepoint_b} "
            f"({len(found_rows)}/{expected} exports found)."
        )
    elif qc_blocking or VERDICT_BLOCKED in side_verdicts:
        verdict = COMPARISON_BLOCKED
        summary = "Comparison blocked by export or session QC."
    elif len(schema_ids) > 1 and rules["require_same_feature_schema_id"]:
        verdict = COMPARISON_BLOCKED
        summary = "Comparison blocked — feature_schema_id mismatch."
    elif VERDICT_MISSING in side_verdicts:
        verdict = COMPARISON_INSUFFICIENT
        summary = "Missing exports on one or both sides of the comparison."
    elif VERDICT_NOT_RECOMMENDED in side_verdicts:
        verdict = COMPARISON_NOT_RECOMMENDED
        summary = "Not recommended — fail-level QC on at least one segment."
    elif VERDICT_CAUTION in side_verdicts or rules["warn_on_cross_timepoint_mix"]:
        verdict = COMPARISON_CAUTION
        summary = (
            f"Caution — warnings present for {request.timepoint_a}–{request.timepoint_b}; "
            "review before interpreting JcvPCA contrasts."
        )
        if rules["warn_on_cross_timepoint_mix"]:
            evidence.append(
                EvidenceItem(
                    source="registry",
                    field="cross_timepoint_comparison",
                    detail="Cross-timepoint mix flagged by segment_selection matching policy.",
                    threshold_key="matching.warn_on_cross_timepoint_mix",
                )
            )
    else:
        verdict = COMPARISON_READY
        summary = (
            f"Structurally ready for {request.participant_id} "
            f"{request.timepoint_a} vs {request.timepoint_b} "
            f"({', '.join(request.p_phases)})."
        )

    if comparable_count is not None and comparable_count == 0 and found_rows:
        verdict = worst_inclusion_verdict([verdict, COMPARISON_NOT_RECOMMENDED])
        evidence.append(
            EvidenceItem(
                source="manifest",
                field="comparable_links",
                detail="No comparable links detected across selected matrices.",
            )
        )

    return ComparisonRecommendation(
        request=request,
        verdict=verdict,
        summary=summary,
        evidence=tuple(evidence),
        threshold_keys=tuple(dict.fromkeys(threshold_keys)),
        segment_rows_found=len(found_rows),
        segment_rows_expected=expected,
        feature_schema_ids=tuple(schema_ids),
        comparable_link_count=comparable_count,
    )


def _try_comparable_link_count(rows: list[dict[str, Any]]) -> int | None:
    try:
        import pandas as pd
        from layer3_jcvpca.comparable_links import detect_comparable_links

        df = pd.DataFrame(rows)
        report = detect_comparable_links(df, min_rows=1)
        return len(report.comparable_link_stems)
    except Exception:
        return None


def comparison_label(request: ComparisonRequest) -> str:
    phases = ",".join(request.p_phases)
    return (
        f"{request.participant_id} {request.timepoint_a}–{request.timepoint_b} "
        f"[{phases}]"
    )


@dataclass(frozen=True)
class RepetitionComparisonRequest:
    participant_id: str
    timepoint: str
    repetition_a: str = "R1"
    repetition_b: str = "R2"
    p_phases: tuple[str, ...] = GAGA_P_PHASES


@dataclass(frozen=True)
class RepetitionComparisonRecommendation:
    request: RepetitionComparisonRequest
    verdict: str
    summary: str
    evidence: tuple[EvidenceItem, ...] = ()
    threshold_keys: tuple[str, ...] = ()
    segment_rows_found: int = 0
    segment_rows_expected: int = 0
    feature_schema_ids: tuple[str, ...] = ()
    comparable_link_count: int | None = None
    advisory_label: str = ADVISORY_LABEL


def evaluate_repetition_comparison_readiness(
    snapshot: ProjectSnapshot,
    request: RepetitionComparisonRequest,
    *,
    inclusion_report: InclusionReport | None = None,
    check_comparable_links: bool = False,
) -> RepetitionComparisonRecommendation:
    """Evaluate R1 vs R2 within one timepoint (exploratory repetition comparison)."""
    if inclusion_report is None:
        inclusion_report = build_inclusion_report(snapshot, build_readiness_matrix(snapshot))

    inclusion = _inclusion_lookup(inclusion_report)
    rules = _matching_rules(snapshot)
    evidence: list[EvidenceItem] = []
    threshold_keys = ["matching.require_same_feature_schema_id"]

    expected = len(request.p_phases) * 2
    found_rows: list[dict[str, Any]] = []
    side_verdicts: list[str] = []

    for p_phase in request.p_phases:
        for repetition in (request.repetition_a, request.repetition_b):
            key = (request.participant_id, request.timepoint, repetition, p_phase)
            side_verdicts.append(inclusion.get(key, VERDICT_MISSING))
            rows = _manifest_rows_for(
                snapshot, request.participant_id, request.timepoint, repetition, p_phase
            )
            if rows:
                found_rows.extend(rows)
            else:
                evidence.append(
                    EvidenceItem(
                        source="manifest",
                        field="layer25_export_manifest.csv",
                        detail=f"No export row for {key}",
                    )
                )

    schema_ids = sorted(
        {str(r.get("feature_schema_id", "")) for r in found_rows if r.get("feature_schema_id")}
    )
    if rules["require_same_feature_schema_id"] and len(schema_ids) > 1:
        evidence.append(
            EvidenceItem(
                source="registry",
                field="feature_schema_id",
                detail=f"Mixed feature schemas: {schema_ids}",
                threshold_key="matching.require_same_feature_schema_id",
            )
        )

    qc_blocking = [
        r for r in found_rows
        if str(r.get("qc_status", "")).lower() == "blocking"
        or str(r.get("layer3_safe", "")).lower() == "false"
    ]
    if qc_blocking:
        evidence.append(
            EvidenceItem(
                source="manifest",
                field="qc_status / layer3_safe",
                detail=f"{len(qc_blocking)} segment(s) blocking or not layer3_safe",
                threshold_key="layer2_5.block_if",
            )
        )
        threshold_keys.append("layer2_5.block_if")

    comparable_count: int | None = None
    if check_comparable_links and found_rows:
        comparable_count = _try_comparable_link_count(found_rows)

    if found_rows and len(found_rows) < expected:
        verdict = COMPARISON_INSUFFICIENT
        summary = (
            f"Insufficient segments for {request.timepoint} "
            f"{request.repetition_a} vs {request.repetition_b} "
            f"({len(found_rows)}/{expected} found)."
        )
    elif qc_blocking or VERDICT_BLOCKED in side_verdicts:
        verdict = COMPARISON_BLOCKED
        summary = "Repetition comparison blocked by export or session QC."
    elif len(schema_ids) > 1 and rules["require_same_feature_schema_id"]:
        verdict = COMPARISON_BLOCKED
        summary = "Blocked — feature_schema_id mismatch between repetitions."
    elif VERDICT_MISSING in side_verdicts:
        verdict = COMPARISON_INSUFFICIENT
        summary = "Missing exports for one or both repetitions."
    elif VERDICT_NOT_RECOMMENDED in side_verdicts:
        verdict = COMPARISON_NOT_RECOMMENDED
        summary = "Not recommended — fail-level QC on at least one segment."
    elif VERDICT_CAUTION in side_verdicts:
        verdict = COMPARISON_CAUTION
        summary = (
            f"Caution — warnings for {request.timepoint} "
            f"{request.repetition_a} vs {request.repetition_b}."
        )
    else:
        verdict = COMPARISON_READY
        summary = (
            f"Structurally ready for {request.participant_id} {request.timepoint} "
            f"{request.repetition_a} vs {request.repetition_b}."
        )

    if comparable_count is not None and comparable_count == 0 and found_rows:
        verdict = worst_inclusion_verdict([verdict, COMPARISON_NOT_RECOMMENDED])
        evidence.append(
            EvidenceItem(
                source="manifest",
                field="comparable_links",
                detail="No comparable links across selected repetition matrices.",
            )
        )

    return RepetitionComparisonRecommendation(
        request=request,
        verdict=verdict,
        summary=summary,
        evidence=tuple(evidence),
        threshold_keys=tuple(dict.fromkeys(threshold_keys)),
        segment_rows_found=len(found_rows),
        segment_rows_expected=expected,
        feature_schema_ids=tuple(schema_ids),
        comparable_link_count=comparable_count,
    )


# Gaga batch comparison presets (mirrors gaga_batch_runner.build_comparison_specs)
KNOWN_LONGITUDINAL_COMPARISONS: dict[str, tuple[str, str, str]] = {
    "L1_T1_vs_T2": ("T1_vs_T2", "T1", "T2"),
    "L2_T1_vs_T3": ("T1_vs_T3", "T1", "T3"),
}

KNOWN_REPETITION_COMPARISONS: dict[str, str] = {
    "I_T1_R1_vs_R2": "T1",
    "I_T2_R1_vs_R2": "T2",
    "I_T3_R1_vs_R2": "T3",
}
