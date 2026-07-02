"""Read-only gate recommendations for G2/G3 (pure Python, no side effects)."""

from __future__ import annotations

from dataclasses import dataclass

from comparison_readiness import ComparisonRequest, evaluate_comparison_readiness
from inclusion_recommendations import (
    ADVISORY_LABEL,
    VERDICT_BLOCKED,
    VERDICT_CAUTION,
    build_inclusion_report,
    summarize_inclusion,
)
from joint_link_qc import LINK_NOT_RECOMMENDED, build_joint_link_qc_report
from project_status import ProjectSnapshot
from readiness import build_readiness_matrix


@dataclass(frozen=True)
class Recommendation:
    gate: str
    verdict: str
    reasons: tuple[str, ...] = ()
    threshold_refs: tuple[str, ...] = ()
    advisory_label: str = ADVISORY_LABEL


def recommend_pre_checks(snapshot: ProjectSnapshot) -> Recommendation:
    reasons: list[str] = []
    if not snapshot.path_validation_ok:
        reasons.append(
            f"Path registry errors: {'; '.join(snapshot.path_validation_errors[:3])}"
        )
    if not snapshot.canonical_batch_exists:
        reasons.append(f"Canonical batch missing: {snapshot.canonical_batch_id}")
    if reasons:
        return Recommendation("pre_checks", "review_required", tuple(reasons))
    return Recommendation(
        "pre_checks",
        "ready",
        ("Path registry OK; canonical batch present.",),
    )


def recommend_data_readiness(snapshot: ProjectSnapshot) -> Recommendation:
    matrix = build_readiness_matrix(snapshot)
    inclusion = build_inclusion_report(snapshot, matrix)
    counts = summarize_inclusion(inclusion)
    blocking = counts.get(VERDICT_BLOCKED, 0) + sum(
        1 for c in matrix.cells if c.overall in ("block", "fail")
    )
    caution = counts.get(VERDICT_CAUTION, 0)
    missing = counts.get("missing", 0)
    reasons: list[str] = []
    refs = (
        "layer2.rotvec_jump_fail_rad",
        "layer2_5.block_if",
        "layer1.max_missing_percent_caution",
    )
    if blocking:
        reasons.append(
            f"{blocking} inclusion cells blocked/failed — resolve before Layer 3 batch."
        )
    if caution:
        reasons.append(
            f"{caution} cells at caution — review joint/link QC before interpreting contrasts."
        )
    if missing:
        reasons.append(f"{missing} cells missing exports or L1 outputs.")
    if not reasons:
        return Recommendation(
            "data_readiness",
            "proceed_with_caution",
            ("No blocking cells; review caution rows and link QC before production batch.",),
            refs,
        )
    return Recommendation("data_readiness", "review_required", tuple(reasons), refs)


def recommend_inclusion_summary(snapshot: ProjectSnapshot) -> Recommendation:
    report = build_inclusion_report(snapshot)
    counts = summarize_inclusion(report)
    ready = counts.get("ready", 0)
    total = len(report.recommendations)
    reasons = [
        f"{ready}/{total} P-phase cells advisory-ready.",
        f"Caution: {counts.get('caution', 0)}, "
        f"not recommended: {counts.get('not_recommended', 0)}, "
        f"blocked: {counts.get('blocked', 0)}, "
        f"missing: {counts.get('missing', 0)}.",
    ]
    verdict = "ready" if counts.get("blocked", 0) == 0 and counts.get("missing", 0) == 0 else "review_required"
    return Recommendation("inclusion_summary", verdict, tuple(reasons))


def recommend_joint_link_qc(
    snapshot: ProjectSnapshot,
    *,
    participant_id: str | None = None,
) -> Recommendation:
    pids = [participant_id] if participant_id else None
    report = build_joint_link_qc_report(snapshot, participant_ids=pids, max_exports=24)
    bad = sum(1 for r in report.link_recommendations if r.verdict == LINK_NOT_RECOMMENDED)
    caution = sum(1 for r in report.link_recommendations if r.verdict == "caution")
    total = len(report.link_recommendations)
    reasons = [
        f"Indexed {total} link×export rows from window artifacts.",
        f"Not recommended: {bad}; caution: {caution}.",
        "See Joint / Link QC page for body-region breakdown and evidence.",
    ]
    verdict = "review_required" if bad or caution else "ready"
    return Recommendation(
        "joint_link_qc",
        verdict,
        tuple(reasons),
        ("layer2.rotvec_jump_fail_rad", "layer2.rotvec_jump_warning_rad", "layer2_5.block_if"),
    )


def recommend_comparison(
    snapshot: ProjectSnapshot,
    request: ComparisonRequest,
) -> Recommendation:
    comp = evaluate_comparison_readiness(snapshot, request, check_comparable_links=False)
    reasons = [comp.summary]
    for ev in comp.evidence[:5]:
        prefix = f"[{ev.source}] {ev.field}: "
        reasons.append(prefix + ev.detail)
    return Recommendation(
        f"comparison_{request.timepoint_a}_{request.timepoint_b}",
        comp.verdict,
        tuple(reasons),
        comp.threshold_keys,
    )


def all_recommendations(snapshot: ProjectSnapshot) -> list[Recommendation]:
    return [
        recommend_pre_checks(snapshot),
        recommend_data_readiness(snapshot),
        recommend_inclusion_summary(snapshot),
        recommend_joint_link_qc(snapshot),
    ]


def default_comparison_requests(snapshot: ProjectSnapshot) -> list[ComparisonRequest]:
    """Standard Gaga cross-timepoint checks for all discovered participants."""
    cohort = snapshot.participants
    if not cohort:
        return []
    requests: list[ComparisonRequest] = []
    for pid in cohort:
        requests.append(
            ComparisonRequest(
                participant_id=pid,
                timepoint_a="T1",
                timepoint_b="T2",
                p_phases=("P1", "P2", "P3"),
            )
        )
        requests.append(
            ComparisonRequest(
                participant_id=pid,
                timepoint_a="T1",
                timepoint_b="T3",
                p_phases=("P1", "P2", "P3"),
            )
        )
    return requests
