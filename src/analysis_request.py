"""G4 analysis request builder — validated, agent-runnable YAML (no execution)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise ImportError("analysis_request requires PyYAML") from exc

from comparability import ComparabilityStatus
from comparison_readiness import (
    KNOWN_LONGITUDINAL_COMPARISONS,
    KNOWN_REPETITION_COMPARISONS,
    VERDICT_BLOCKED,
    VERDICT_INSUFFICIENT,
    ComparisonRequest,
    RepetitionComparisonRequest,
    evaluate_comparison_readiness,
    evaluate_repetition_comparison_readiness,
)
from inclusion_recommendations import (
    ADVISORY_LABEL,
    VERDICT_CAUTION,
    VERDICT_MISSING,
    VERDICT_NOT_RECOMMENDED,
    VERDICT_READY,
    build_inclusion_report,
    filter_inclusion_report,
    summarize_inclusion,
)
from joint_link_qc import LINK_CAUTION, LINK_NOT_RECOMMENDED, build_joint_link_qc_report
from project_status import GAGA_P_PHASES, ProjectSnapshot, REGISTRY_COVERAGE
from segmentation_coverage import (
    COVERAGE_REQUESTED_NOT_EXPORTED,
    EXERCISE_SELECTION_ALL_IN_SHEET,
    EXERCISE_SELECTION_EXPLICIT_IDS,
    EXERCISE_SELECTION_GAGA_P_PHASES,
    build_resolved_segments,
    build_segmentation_coverage_rows,
    summarize_segmentation_coverage,
)

REQUEST_BUILDER_VERSION = "G4"
STATUS_DRAFT = "draft"
STATUS_VALIDATED = "validated"
STATUS_BLOCKED = "blocked"
STATUS_READY = "ready_for_execution"

LEVEL_ERROR = "error"
LEVEL_WARNING = "warning"
LEVEL_ADVISORY = "advisory"

DEFAULT_REQUESTS_DIR = Path("requests") / "analysis_requests"


@dataclass
class ValidationMessage:
    level: str
    code: str
    message: str
    source: str
    field: str = ""
    threshold_key: str = ""


@dataclass
class ComparisonSpecInput:
    comparison_id: str
    comparison_type: str = "longitudinal"
    comparison_label: str = ""
    timepoint_a: str | None = None
    timepoint_b: str | None = None
    timepoint: str | None = None
    repetition_a: str = "R1"
    repetition_b: str = "R2"
    repetitions: tuple[str, ...] = ("R1", "R2")


@dataclass
class AnalysisRequestInput:
    participant_id: str
    p_phases: tuple[str, ...] = GAGA_P_PHASES
    repetitions: tuple[str, ...] = ("R1", "R2")
    comparisons: list[ComparisonSpecInput] = field(default_factory=list)
    segment_preset: str | None = None
    block_a: tuple[str, ...] | None = None
    block_b: tuple[str, ...] | None = None
    pc_focus_spaces: tuple[str, ...] = ("all", "functional", "null_space")
    generate_comparison_plots: bool = True
    generate_full_numeric_reports: str = "on_demand"
    generate_poster_package: str = "on_demand"
    body_regions: tuple[str, ...] = ()
    link_stems: tuple[str, ...] = ()
    use_comparable_links_only: bool = True
    exercise_selection_mode: str = EXERCISE_SELECTION_ALL_IN_SHEET
    selected_exercise_ids: tuple[int, ...] = ()


def segment_id_from_row(row: dict[str, Any]) -> str:
    session_id = str(row.get("session_id", ""))
    label = str(
        row.get("exercise_export_label")
        or row.get("p_phase")
        or row.get("gaga_exercise_label")
        or ""
    )
    return f"{session_id}::{label}"


def _resolve_segments(
    snapshot: ProjectSnapshot,
    inp: AnalysisRequestInput,
) -> list[dict[str, Any]]:
    return build_resolved_segments(snapshot, inp)


def _default_blocks(snapshot: ProjectSnapshot) -> tuple[list[str], list[str]]:
    cfg = snapshot.config
    block_a = list(cfg.get("cohort.block_a"))
    block_b = list(cfg.get("cohort.block_b"))
    return block_a, block_b


def _message_dict(msg: ValidationMessage) -> dict[str, str]:
    d = asdict(msg)
    return {k: v for k, v in d.items() if v}


def validate_analysis_request(
    snapshot: ProjectSnapshot,
    inp: AnalysisRequestInput,
    *,
    check_comparable_links: bool = True,
) -> tuple[list[ValidationMessage], dict[str, Any]]:
    """Validate request against G2/G3 logic; return messages + validation payload."""
    messages: list[ValidationMessage] = []
    inclusion_report = build_inclusion_report(snapshot)
    inclusion_summary = summarize_inclusion(inclusion_report)
    comparison_results: list[dict[str, Any]] = []
    comparable_link_count: int | None = None

    if not inp.comparisons:
        messages.append(
            ValidationMessage(
                LEVEL_ERROR,
                "no_comparisons",
                "At least one comparison must be specified.",
                "analysis_request",
                field="comparisons",
            )
        )

    invalid_phases = [p for p in inp.p_phases if p not in GAGA_P_PHASES]
    if invalid_phases:
        messages.append(
            ValidationMessage(
                LEVEL_ERROR,
                "invalid_p_phases",
                f"Unknown P-phases: {invalid_phases}",
                "analysis_request",
                field="selection.p_phases",
            )
        )

    if inp.participant_id and inp.participant_id not in snapshot.participants:
        messages.append(
            ValidationMessage(
                LEVEL_ERROR,
                "participant_not_discovered",
                (
                    f"Participant {inp.participant_id!r} is not in the discovered cohort "
                    f"{snapshot.participants}. Run Stage 1 discovery after adding data."
                ),
                "participant_discovery",
                field="selection.participant_id",
            )
        )

    filtered_inclusion = filter_inclusion_report(
        inclusion_report,
        participant_ids=[inp.participant_id],
        repetitions=list(inp.repetitions),
        p_phases=list(inp.p_phases),
    )
    for rec in filtered_inclusion:
        if rec.verdict == VERDICT_BLOCKED:
            messages.append(
                ValidationMessage(
                    LEVEL_ERROR,
                    "inclusion_blocked",
                    f"{rec.timepoint} {rec.repetition} {rec.p_phase}: {rec.summary}",
                    "g3_inclusion",
                    field="selection",
                    threshold_key=rec.threshold_keys[0] if rec.threshold_keys else "",
                )
            )
        elif rec.verdict == VERDICT_NOT_RECOMMENDED:
            messages.append(
                ValidationMessage(
                    LEVEL_WARNING,
                    "inclusion_not_recommended",
                    f"{rec.timepoint} {rec.repetition} {rec.p_phase}: {rec.summary}",
                    "g3_inclusion",
                    field="selection",
                )
            )
        elif rec.verdict == VERDICT_CAUTION:
            messages.append(
                ValidationMessage(
                    LEVEL_WARNING,
                    "inclusion_caution",
                    f"{rec.timepoint} {rec.repetition} {rec.p_phase}: {rec.summary}",
                    "g3_inclusion",
                    field="selection",
                )
            )
        elif rec.verdict == VERDICT_MISSING:
            messages.append(
                ValidationMessage(
                    LEVEL_ERROR,
                    "segment_missing",
                    f"Missing export: {rec.timepoint} {rec.repetition} {rec.p_phase}",
                    "g2_readiness",
                    field="resolved_segments",
                )
            )

    all_segment_rows: list[dict[str, Any]] = []
    for comp in inp.comparisons:
        if comp.comparison_type == "longitudinal":
            req = ComparisonRequest(
                participant_id=inp.participant_id,
                timepoint_a=comp.timepoint_a or "T1",
                timepoint_b=comp.timepoint_b or "T2",
                p_phases=inp.p_phases,
                repetitions=comp.repetitions or inp.repetitions,
            )
            result = evaluate_comparison_readiness(
                snapshot,
                req,
                inclusion_report=inclusion_report,
                check_comparable_links=False,
            )
            comparison_results.append(
                {
                    "comparison_id": comp.comparison_id,
                    "comparison_type": comp.comparison_type,
                    "verdict": result.verdict,
                    "summary": result.summary,
                    "segment_rows_found": result.segment_rows_found,
                    "segment_rows_expected": result.segment_rows_expected,
                    "feature_schema_ids": list(result.feature_schema_ids),
                }
            )
            if result.verdict == VERDICT_BLOCKED:
                messages.append(
                    ValidationMessage(
                        LEVEL_ERROR,
                        "comparison_blocked",
                        f"{comp.comparison_id}: {result.summary}",
                        "g3_comparison",
                        field=f"comparisons.{comp.comparison_id}",
                    )
                )
            elif result.verdict in {VERDICT_NOT_RECOMMENDED, VERDICT_INSUFFICIENT}:
                level = LEVEL_ERROR if result.verdict == VERDICT_INSUFFICIENT else LEVEL_WARNING
                messages.append(
                    ValidationMessage(
                        level,
                        f"comparison_{result.verdict}",
                        f"{comp.comparison_id}: {result.summary}",
                        "g3_comparison",
                        field=f"comparisons.{comp.comparison_id}",
                    )
                )
            elif result.verdict == VERDICT_CAUTION:
                messages.append(
                    ValidationMessage(
                        LEVEL_WARNING,
                        "comparison_caution",
                        f"{comp.comparison_id}: {result.summary}",
                        "g3_comparison",
                        field=f"comparisons.{comp.comparison_id}",
                    )
                )
            for ev in result.evidence:
                if ev.threshold_key and "feature_schema" in ev.field:
                    messages.append(
                        ValidationMessage(
                            LEVEL_ERROR,
                            "feature_schema_mismatch",
                            ev.detail,
                            "g3_comparison",
                            threshold_key=ev.threshold_key,
                        )
                    )

        elif comp.comparison_type == "within_timepoint_repetition":
            req = RepetitionComparisonRequest(
                participant_id=inp.participant_id,
                timepoint=comp.timepoint or "T1",
                repetition_a=comp.repetition_a,
                repetition_b=comp.repetition_b,
                p_phases=inp.p_phases,
            )
            result = evaluate_repetition_comparison_readiness(
                snapshot,
                req,
                inclusion_report=inclusion_report,
                check_comparable_links=False,
            )
            comparison_results.append(
                {
                    "comparison_id": comp.comparison_id,
                    "comparison_type": comp.comparison_type,
                    "verdict": result.verdict,
                    "summary": result.summary,
                    "segment_rows_found": result.segment_rows_found,
                    "segment_rows_expected": result.segment_rows_expected,
                    "feature_schema_ids": list(result.feature_schema_ids),
                }
            )
            if result.verdict == VERDICT_BLOCKED:
                messages.append(
                    ValidationMessage(
                        LEVEL_ERROR,
                        "comparison_blocked",
                        f"{comp.comparison_id}: {result.summary}",
                        "g3_comparison",
                    )
                )
            elif result.verdict == VERDICT_CAUTION:
                messages.append(
                    ValidationMessage(
                        LEVEL_WARNING,
                        "comparison_caution",
                        f"{comp.comparison_id}: {result.summary}",
                        "g3_comparison",
                    )
                )

    resolved = _resolve_segments(snapshot, inp)
    coverage_rows, seg_path = build_segmentation_coverage_rows(snapshot, inp)
    coverage_summary = summarize_segmentation_coverage(coverage_rows)
    pending_export = [r for r in resolved if r.get("export_status") == COVERAGE_REQUESTED_NOT_EXPORTED]
    if pending_export:
        messages.append(
            ValidationMessage(
                LEVEL_WARNING,
                "segments_not_exported",
                f"{len(pending_export)} requested segment(s) are in segmentation xlsx but not in manifest — run L2.5 export.",
                "segmentation",
                field="resolved_segments",
            )
        )
    if not seg_path or not seg_path.is_file():
        messages.append(
            ValidationMessage(
                LEVEL_WARNING,
                "segmentation_workbook_missing",
                f"No segmentation workbook for participant {inp.participant_id}.",
                "segmentation",
            )
        )
    if not resolved:
        messages.append(
            ValidationMessage(
                LEVEL_ERROR,
                "no_resolved_segments",
                "No manifest segments resolve for this request.",
                "manifest",
                field="resolved_segments",
            )
        )

    schema_ids = sorted({r["feature_schema_id"] for r in resolved if r["feature_schema_id"]})
    if len(schema_ids) > 1:
        messages.append(
            ValidationMessage(
                LEVEL_ERROR,
                "feature_schema_mismatch",
                f"Resolved segments span multiple feature_schema_id values: {schema_ids}",
                "g3_comparison",
                threshold_key="matching.require_same_feature_schema_id",
            )
        )

    if check_comparable_links and resolved:
        comparable_link_count = _try_comparable_link_count(resolved)
        if comparable_link_count is not None:
            if comparable_link_count == 0 and inp.use_comparable_links_only:
                messages.append(
                    ValidationMessage(
                        LEVEL_ERROR,
                        "no_comparable_links",
                        "No comparable links across resolved segments.",
                        "g3_links",
                        field="link_focus",
                    )
                )
            elif comparable_link_count == 0:
                messages.append(
                    ValidationMessage(
                        LEVEL_WARNING,
                        "no_comparable_links",
                        "No comparable links detected (use_comparable_links_only=false).",
                        "g3_links",
                        field="link_focus",
                    )
                )

    link_caution = 0
    link_bad = 0
    if resolved:
        link_report = build_joint_link_qc_report(
            snapshot,
            participant_ids=[inp.participant_id],
            p_phases=list(inp.p_phases),
            repetitions=list(inp.repetitions),
        )
        for rec in link_report.link_recommendations:
            if inp.body_regions and rec.body_region not in inp.body_regions:
                continue
            if rec.verdict == LINK_CAUTION:
                link_caution += 1
            elif rec.verdict == LINK_NOT_RECOMMENDED:
                link_bad += 1
        if link_bad:
            messages.append(
                ValidationMessage(
                    LEVEL_WARNING,
                    "link_not_recommended",
                    f"{link_bad} link(s) flagged not recommended for JcvPCA interpretation.",
                    "g3_links",
                    field="link_focus",
                    threshold_key="layer2.rotvec_jump_fail_rad",
                )
            )
        if link_caution:
            messages.append(
                ValidationMessage(
                    LEVEL_ADVISORY,
                    "link_caution",
                    f"{link_caution} link(s) usable with caution.",
                    "g3_links",
                    field="link_focus",
                )
            )

    if snapshot.canonical_comparability == ComparabilityStatus.PRE_REGISTRY_CANONICAL:
        messages.append(
            ValidationMessage(
                LEVEL_ADVISORY,
                "pre_registry_canonical",
                "Canonical batch predates config snapshots; new requests are not hash-comparable to batch 193319.",
                "provenance",
                field="provenance.canonical_comparability",
            )
        )

    messages.append(
        ValidationMessage(
            LEVEL_ADVISORY,
            "no_execution_g4",
            "G4 saves intent only — execution.allowed remains false until a future guarded runner.",
            "execution",
        )
    )

    validation_payload = {
        "errors": [_message_dict(m) for m in messages if m.level == LEVEL_ERROR],
        "warnings": [_message_dict(m) for m in messages if m.level == LEVEL_WARNING],
        "advisory_notes": [_message_dict(m) for m in messages if m.level == LEVEL_ADVISORY],
        "inclusion_summary": inclusion_summary,
        "comparison_results": comparison_results,
        "comparable_link_count": comparable_link_count,
        "link_focus_caution_count": link_caution,
        "link_focus_not_recommended_count": link_bad,
        "segmentation_coverage": coverage_summary,
    }
    return messages, validation_payload


def _try_comparable_link_count(resolved: list[dict[str, Any]]) -> int | None:
    try:
        import pandas as pd
        from layer3_jcvpca.comparable_links import detect_comparable_links

        rows = []
        for seg in resolved:
            pid = seg["session_id"].split("_")[0] if seg.get("session_id") else ""
            rows.append(
                {
                    "participant_id": pid,
                    "timepoint": seg["timepoint"],
                    "repetition": seg["repetition"],
                    "session_id": seg["session_id"],
                    "gaga_exercise_label": seg["p_phase"],
                    "export_granularity": "per_exercise",
                    "matrix_path": seg["matrix_path"],
                    "manifest_path": seg.get("manifest_path", ""),
                    "layer3_safe": seg["layer3_safe"],
                    "qc_status": seg["qc_status"],
                    "n_frames": "",
                    "n_features": "",
                    "feature_schema_id": seg["feature_schema_id"],
                }
            )
        df = pd.DataFrame(rows)
        report = detect_comparable_links(df, min_rows=1)
        return len(report.comparable_link_stems)
    except Exception:
        return None


def _determine_status(messages: list[ValidationMessage]) -> str:
    if any(m.level == LEVEL_ERROR for m in messages):
        return STATUS_BLOCKED
    if any(m.level == LEVEL_WARNING for m in messages):
        return STATUS_VALIDATED
    return STATUS_READY


def build_analysis_request(
    snapshot: ProjectSnapshot,
    inp: AnalysisRequestInput,
    *,
    request_id: str | None = None,
    check_comparable_links: bool = True,
) -> dict[str, Any]:
    """Build a full analysis_request dict with validation snapshot."""
    now = datetime.now(timezone.utc).isoformat()
    rid = request_id or (
        f"{inp.participant_id}_{now[:10].replace('-', '')}_"
        f"{'-'.join(c.comparison_id for c in inp.comparisons[:2]) or 'draft'}"
    )

    messages, validation_payload = validate_analysis_request(
        snapshot, inp, check_comparable_links=check_comparable_links
    )
    status = _determine_status(messages)
    block_a, block_b = _default_blocks(snapshot)
    if inp.block_a is not None:
        block_a = list(inp.block_a)
    if inp.block_b is not None:
        block_b = list(inp.block_b)

    resolved = _resolve_segments(snapshot, inp)
    coverage_rows, _ = build_segmentation_coverage_rows(snapshot, inp)
    errors = [m for m in messages if m.level == LEVEL_ERROR]
    warnings = [m for m in messages if m.level == LEVEL_WARNING]

    coverage = {
        layer: meta["label"] for layer, meta in REGISTRY_COVERAGE.items()
    }

    comparisons_yaml = []
    for comp in inp.comparisons:
        entry: dict[str, Any] = {
            "comparison_id": comp.comparison_id,
            "comparison_label": comp.comparison_label or comp.comparison_id,
            "comparison_type": comp.comparison_type,
        }
        if comp.comparison_type == "longitudinal":
            entry["timepoint_a"] = comp.timepoint_a
            entry["timepoint_b"] = comp.timepoint_b
            entry["repetitions"] = list(comp.repetitions or inp.repetitions)
        else:
            entry["timepoint"] = comp.timepoint
            entry["repetition_a"] = comp.repetition_a
            entry["repetition_b"] = comp.repetition_b
        comparisons_yaml.append(entry)

    return {
        "version": 1,
        "request_id": rid,
        "status": status,
        "created_at": now,
        "updated_at": now,
        "advisory_label": ADVISORY_LABEL,
        "provenance": {
            "science_hash": snapshot.config.science_hash,
            "display_hash": snapshot.config.display_hash,
            "registry_coverage": coverage,
            "canonical_batch_id": snapshot.canonical_batch_id,
            "canonical_comparability": snapshot.canonical_comparability.value,
            "canonical_science_hash": snapshot.canonical_config_hash,
            "request_builder_version": REQUEST_BUILDER_VERSION,
        },
        "selection": {
            "participant_id": inp.participant_id,
            "repetitions": list(inp.repetitions),
            "p_phases": list(inp.p_phases),
            "segment_preset": inp.segment_preset,
            "exercise_selection_mode": inp.exercise_selection_mode,
            "selected_exercise_ids": list(inp.selected_exercise_ids),
            "blocks": {"A": block_a, "B": block_b},
        },
        "comparisons": comparisons_yaml,
        "outputs": {
            "pc_focus_spaces": list(inp.pc_focus_spaces),
            "generate_comparison_plots": inp.generate_comparison_plots,
            "generate_full_numeric_reports": inp.generate_full_numeric_reports,
            "generate_poster_package": inp.generate_poster_package,
        },
        "link_focus": {
            "body_regions": list(inp.body_regions),
            "link_stems": list(inp.link_stems),
            "use_comparable_links_only": inp.use_comparable_links_only,
        },
        "resolved_segments": resolved,
        "segmentation_coverage": coverage_rows,
        "validation": validation_payload,
        "execution": {
            "allowed": False,
            "blocker_count": len(errors),
            "caution_count": len(warnings),
            "note": "G4 saves intent only — no analysis executed.",
        },
    }


def save_analysis_request(
    project_root: Path,
    request: dict[str, Any],
    *,
    requests_dir: Path | None = None,
) -> Path:
    """Write analysis request YAML (explicit user/agent save — not config mutation)."""
    out_dir = (requests_dir or (project_root / DEFAULT_REQUESTS_DIR)).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    rid = str(request.get("request_id", "analysis_request")).replace("/", "_")
    path = out_dir / f"{rid}.yaml"
    request = dict(request)
    request["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(
        yaml.safe_dump(request, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def load_analysis_request(path: Path) -> dict[str, Any]:
    """Load a saved analysis request YAML."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def comparison_spec_from_preset(
    comparison_id: str,
    repetitions: tuple[str, ...] = ("R1", "R2"),
) -> ComparisonSpecInput:
    """Build ComparisonSpecInput from known Gaga batch comparison IDs."""
    if comparison_id in KNOWN_LONGITUDINAL_COMPARISONS:
        label, tp_a, tp_b = KNOWN_LONGITUDINAL_COMPARISONS[comparison_id]
        return ComparisonSpecInput(
            comparison_id=comparison_id,
            comparison_type="longitudinal",
            comparison_label=label,
            timepoint_a=tp_a,
            timepoint_b=tp_b,
            repetitions=repetitions,
        )
    if comparison_id in KNOWN_REPETITION_COMPARISONS:
        tp = KNOWN_REPETITION_COMPARISONS[comparison_id]
        return ComparisonSpecInput(
            comparison_id=comparison_id,
            comparison_type="within_timepoint_repetition",
            comparison_label=f"{tp}_R1_vs_{tp}_R2",
            timepoint=tp,
            repetition_a="R1",
            repetition_b="R2",
        )
    raise KeyError(f"Unknown comparison preset: {comparison_id}")
