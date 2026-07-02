"""G3 joint/link QC interpretation — read-only, evidence-first."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from analysis_config import AnalysisConfig
from body_regions import infer_body_region
from project_status import ProjectSnapshot

LINK_USABLE = "usable"
LINK_CAUTION = "caution"
LINK_NOT_RECOMMENDED = "not_recommended"
LINK_UNKNOWN = "unknown"

_REGION_RANK = {LINK_USABLE: 0, LINK_CAUTION: 1, LINK_NOT_RECOMMENDED: 2, LINK_UNKNOWN: 3}


@dataclass(frozen=True)
class LinkEvidence:
    source: str  # registry | window_warnings | flag_log | l2_qc_link | export_manifest
    field: str
    detail: str
    threshold_key: str = ""
    curated_registry: bool = False


@dataclass(frozen=True)
class LinkRecommendation:
    participant_id: str
    session_id: str
    timepoint: str
    repetition: str
    p_phase: str
    link_id: str
    link_label: str
    body_region: str
    verdict: str
    summary: str
    evidence: tuple[LinkEvidence, ...] = ()
    jcvpca_note: str = ""


@dataclass(frozen=True)
class BodyRegionSummary:
    body_region: str
    verdict: str
    n_links: int
    n_caution: int
    n_not_recommended: int
    example_links: tuple[str, ...] = ()


@dataclass
class JointLinkQCReport:
    link_recommendations: list[LinkRecommendation] = field(default_factory=list)
    body_region_summaries: list[BodyRegionSummary] = field(default_factory=list)
    advisory_label: str = "Advisory — link recommendations guide interpretation; not automatic exclusion."


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _export_dir(manifest_row: dict[str, Any]) -> Path | None:
    manifest_path = str(manifest_row.get("manifest_path", "")).strip()
    if manifest_path:
        return Path(manifest_path).parent
    matrix_path = str(manifest_row.get("matrix_path", "")).strip()
    if matrix_path:
        return Path(matrix_path).parent
    return None


def _fmt_threshold(config: AnalysisConfig, key: str) -> str:
    try:
        t = config.get_threshold(key)
        return f"{key}={t.value!r}"
    except KeyError:
        return key


def _aggregate_flag_log(flag_rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    """Per link_id aggregate of frame-level QC in window_joint_frame_flag_log."""
    by_link: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "frames": 0,
            "jump_fail": 0,
            "jump_warn": 0,
            "stage08_not_pass": 0,
            "l1_flagged": 0,
            "not_eligible": 0,
            "link_or_joint": "",
            "parent": "",
            "child": "",
        }
    )
    for row in flag_rows:
        link_id = str(row.get("link_id", "")).strip()
        if not link_id:
            continue
        agg = by_link[link_id]
        agg["frames"] += 1
        agg["link_or_joint"] = row.get("link_or_joint") or agg["link_or_joint"]
        agg["parent"] = row.get("parent_canonical") or agg["parent"]
        agg["child"] = row.get("child_canonical") or agg["child"]
        if str(row.get("stage07_jump_status", "")).lower() == "fail":
            agg["jump_fail"] += 1
        if str(row.get("stage07_jump_status", "")).lower() == "warning":
            agg["jump_warn"] += 1
        s08 = str(row.get("stage08_filter_status", "")).lower()
        if s08 and s08 not in {"pass", ""}:
            agg["stage08_not_pass"] += 1
        if str(row.get("stage08_analysis_eligible", "")).lower() == "false":
            agg["not_eligible"] += 1
        l1_flags = any(
            str(row.get(col, "")).lower() == "true"
            for col in (
                "l1_frame_flag_gap_0p2",
                "l1_frame_flag_gap_0p5",
                "l1_frame_flag_artifact_sigma",
                "l1_frame_flag_segment_swap",
            )
        )
        if l1_flags:
            agg["l1_flagged"] += 1
    return dict(by_link)


def _load_l2_link_qc(snapshot: ProjectSnapshot, session_id: str) -> dict[str, dict[str, str]]:
    """link_id -> row from qc_link_manifest for a canonical session id."""
    out: dict[str, dict[str, str]] = {}
    for sess in snapshot.session_index_rows:
        if str(sess.get("session_id", "")).strip() != session_id:
            continue
        l2_dir = str(sess.get("layer2_run_dir", "")).strip()
        if not l2_dir:
            continue
        qc_path = Path(l2_dir) / "07_rotation_vectors" / "qc_link_manifest.csv"
        for row in _read_csv(qc_path):
            lid = str(row.get("link_id", "")).strip()
            if lid:
                out[lid] = row
        break
    return out


def _verdict_from_signals(
    config: AnalysisConfig,
    *,
    jump_fail_frames: int,
    jump_warn_frames: int,
    l1_flagged_frames: int,
    total_frames: int,
    l2_jump_status: str,
    l2_max_jump: str,
    warning_severity: str,
) -> tuple[str, str, list[LinkEvidence]]:
    evidence: list[LinkEvidence] = []
    fail_rad = _fmt_threshold(config, "layer2.rotvec_jump_fail_rad")
    warn_rad = _fmt_threshold(config, "layer2.rotvec_jump_warning_rad")

    if warning_severity == "blocking":
        evidence.append(
            LinkEvidence(
                source="window_warnings",
                field="severity",
                detail="Blocking severity in window_warnings.csv",
                threshold_key="layer2_5.block_if",
                curated_registry=True,
            )
        )
        return LINK_NOT_RECOMMENDED, "Blocking window warning.", evidence

    if l2_jump_status == "fail" or jump_fail_frames > 0:
        detail = f"L2 stage07 jump fail (max_jump={l2_max_jump or '?'})"
        if jump_fail_frames:
            detail += f"; {jump_fail_frames}/{total_frames} window frames flagged fail"
        evidence.append(
            LinkEvidence(
                source="l2_qc_link" if l2_jump_status == "fail" else "flag_log",
                field="stage07_jump_status",
                detail=detail,
                threshold_key="layer2.rotvec_jump_fail_rad",
                curated_registry=True,
            )
        )
        return (
            LINK_NOT_RECOMMENDED,
            "Rotvec jump exceeds fail threshold — JcvPCA axis may be unreliable.",
            evidence,
        )

    if l2_jump_status == "warning" or jump_warn_frames > 0:
        evidence.append(
            LinkEvidence(
                source="l2_qc_link" if l2_jump_status == "warning" else "flag_log",
                field="stage07_jump_status",
                detail=f"Jump warning ({warn_rad}); frames_warn={jump_warn_frames}",
                threshold_key="layer2.rotvec_jump_warning_rad",
                curated_registry=True,
            )
        )
        return LINK_CAUTION, "Jump warning — usable with caution for JcvPCA.", evidence

    if total_frames and l1_flagged_frames / total_frames > 0.05:
        evidence.append(
            LinkEvidence(
                source="flag_log",
                field="l1_frame_flags",
                detail=(
                    f"L1 evidence overlaps {l1_flagged_frames}/{total_frames} window frames "
                    f"(gap/artifact flags; governed tiers in registry)"
                ),
                threshold_key="layer1.max_missing_percent_warn",
                curated_registry=True,
            )
        )
        return LINK_CAUTION, "Elevated L1 gap/artifact overlap in window.", evidence

    if warning_severity in {"warning", "strong_warning"}:
        evidence.append(
            LinkEvidence(
                source="window_warnings",
                field="severity",
                detail=f"Window warning severity={warning_severity}",
                threshold_key="layer2_5.warn_if",
                curated_registry=True,
            )
        )
        return LINK_CAUTION, "Window-level warning — review before trusting link axis.", evidence

    return LINK_USABLE, "No elevated link-level QC flags in indexed artifacts.", evidence


def analyze_export_row(
    snapshot: ProjectSnapshot,
    manifest_row: dict[str, Any],
    config: AnalysisConfig,
) -> list[LinkRecommendation]:
    """Build link recommendations for one L2.5 per-exercise export."""
    participant_id = str(manifest_row.get("participant_id", ""))
    timepoint = str(manifest_row.get("timepoint", ""))
    repetition = str(manifest_row.get("repetition", ""))
    p_phase = str(manifest_row.get("gaga_exercise_label", ""))
    session_id = str(manifest_row.get("session_id", ""))
    export_dir = _export_dir(manifest_row)
    if export_dir is None:
        return []

    warnings = _read_csv(export_dir / "window_warnings.csv")
    flag_rows = _read_csv(export_dir / "window_joint_frame_flag_log.csv")
    flag_agg = _aggregate_flag_log(flag_rows)
    l2_links = _load_l2_link_qc(snapshot, session_id)

    link_ids = sorted(set(flag_agg.keys()) | set(l2_links.keys()))
    if not link_ids and flag_agg:
        link_ids = sorted(flag_agg.keys())

    # Window-level warnings not tied to a single link
    window_level = [w for w in warnings if not str(w.get("canonical_link_name", "")).strip()]
    link_warning_severity: dict[str, str] = {}
    for w in warnings:
        link_name = str(w.get("canonical_link_name", "")).strip()
        if link_name:
            link_warning_severity[link_name] = str(w.get("severity", "warning")).lower()

    recs: list[LinkRecommendation] = []
    for link_id in link_ids:
        agg = flag_agg.get(link_id, {})
        l2_row = l2_links.get(link_id, {})
        parent = str(agg.get("parent") or l2_row.get("parent_canonical", ""))
        child = str(agg.get("child") or l2_row.get("child_canonical", ""))
        label = str(agg.get("link_or_joint") or f"{parent}->{child}" or link_id)
        region = infer_body_region(parent, child, label)
        total_frames = int(agg.get("frames") or 0)
        severity = link_warning_severity.get(label, "")
        if not severity and window_level:
            severity = str(window_level[0].get("severity", "")).lower()

        verdict, summary, evidence = _verdict_from_signals(
            config,
            jump_fail_frames=int(agg.get("jump_fail") or 0),
            jump_warn_frames=int(agg.get("jump_warn") or 0),
            l1_flagged_frames=int(agg.get("l1_flagged") or 0),
            total_frames=total_frames,
            l2_jump_status=str(l2_row.get("stage07_jump_status", "")).lower(),
            l2_max_jump=str(l2_row.get("stage07_max_jump_rad", "")),
            warning_severity=severity,
        )

        scope = str(l2_row.get("feature_scope", ""))
        if scope.startswith("excluded"):
            evidence = tuple(
                list(evidence)
                + [
                    LinkEvidence(
                        source="l2_qc_link",
                        field="feature_scope",
                        detail=f"feature_scope={scope} (non-registered L2 policy metadata)",
                        curated_registry=False,
                    )
                ]
            )
            verdict = LINK_NOT_RECOMMENDED
            summary = "Excluded from core analysis scope."

        jcvpca_note = {
            LINK_USABLE: "Link axis likely interpretable if segment passes inclusion gates.",
            LINK_CAUTION: "Interpret JcvPCA loadings/scores for this link with window QC context.",
            LINK_NOT_RECOMMENDED: "Down-weight or exclude from link-focused JcvPCA interpretation.",
            LINK_UNKNOWN: "Insufficient link artifacts to advise.",
        }[verdict]

        recs.append(
            LinkRecommendation(
                participant_id=participant_id,
                session_id=session_id,
                timepoint=timepoint,
                repetition=repetition,
                p_phase=p_phase,
                link_id=link_id,
                link_label=label,
                body_region=region,
                verdict=verdict,
                summary=summary,
                evidence=tuple(evidence),
                jcvpca_note=jcvpca_note,
            )
        )
    return recs


def build_joint_link_qc_report(
    snapshot: ProjectSnapshot,
    *,
    participant_ids: list[str] | None = None,
    timepoints: list[str] | None = None,
    repetitions: list[str] | None = None,
    p_phases: list[str] | None = None,
    max_exports: int | None = None,
) -> JointLinkQCReport:
    """Analyze link-level QC across L2.5 exports (reads existing CSV/JSON only)."""
    config = snapshot.config
    rows = [
        r
        for r in snapshot.l25_manifest_rows
        if str(r.get("export_granularity")) == "per_exercise"
    ]
    if participant_ids:
        rows = [r for r in rows if str(r.get("participant_id")) in participant_ids]
    if timepoints:
        rows = [r for r in rows if str(r.get("timepoint")) in timepoints]
    if repetitions:
        rows = [r for r in rows if str(r.get("repetition")) in repetitions]
    if p_phases:
        rows = [r for r in rows if str(r.get("gaga_exercise_label")) in p_phases]
    if max_exports is not None:
        rows = rows[:max_exports]

    all_recs: list[LinkRecommendation] = []
    for row in rows:
        all_recs.extend(analyze_export_row(snapshot, row, config))

    region_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"links": [], "caution": 0, "bad": 0}
    )
    for rec in all_recs:
        region_stats[rec.body_region]["links"].append(rec.link_label)
        if rec.verdict == LINK_CAUTION:
            region_stats[rec.body_region]["caution"] += 1
        elif rec.verdict == LINK_NOT_RECOMMENDED:
            region_stats[rec.body_region]["bad"] += 1

    summaries: list[BodyRegionSummary] = []
    for region, stats in sorted(region_stats.items()):
        n = len(stats["links"])
        bad = stats["bad"]
        caution = stats["caution"]
        if bad > 0:
            verdict = LINK_NOT_RECOMMENDED
        elif caution > 0:
            verdict = LINK_CAUTION
        else:
            verdict = LINK_USABLE
        summaries.append(
            BodyRegionSummary(
                body_region=region,
                verdict=verdict,
                n_links=n,
                n_caution=caution,
                n_not_recommended=bad,
                example_links=tuple(sorted(set(stats["links"]))[:5]),
            )
        )

    return JointLinkQCReport(
        link_recommendations=all_recs,
        body_region_summaries=summaries,
    )


def link_recommendations_as_rows(report: JointLinkQCReport) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in report.link_recommendations:
        rows.append(
            {
                "participant": rec.participant_id,
                "timepoint": rec.timepoint,
                "repetition": rec.repetition,
                "P_phase": rec.p_phase,
                "link_id": rec.link_id,
                "link": rec.link_label,
                "body_region": rec.body_region,
                "verdict": rec.verdict,
                "summary": rec.summary,
                "evidence": " | ".join(e.detail for e in rec.evidence[:3]),
                "jcvpca_note": rec.jcvpca_note,
            }
        )
    return rows
