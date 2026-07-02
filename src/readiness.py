"""Data Readiness matrix derivation for G2 (read-only, threshold-provenance)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from analysis_config import AnalysisConfig
from project_status import GAGA_P_PHASES, ProjectSnapshot

READINESS_PASS = "pass"
READINESS_WARN = "warn"
READINESS_FAIL = "fail"
READINESS_BLOCK = "block"
READINESS_STRONG_WARN = "strong_warning"
READINESS_MISSING = "missing"
READINESS_UNKNOWN = "unknown"

_STATUS_RANK = {
    READINESS_PASS: 0,
    READINESS_WARN: 1,
    READINESS_STRONG_WARN: 2,
    READINESS_FAIL: 3,
    READINESS_BLOCK: 4,
    READINESS_MISSING: 5,
    READINESS_UNKNOWN: 6,
}


@dataclass(frozen=True)
class LayerReadiness:
    status: str
    summary: str
    threshold_keys: tuple[str, ...] = ()
    evidence: str = ""


@dataclass(frozen=True)
class ReadinessCell:
    participant_id: str
    timepoint: str
    repetition: str
    p_phase: str
    session_id: str
    l1: LayerReadiness
    l2: LayerReadiness
    l2_5: LayerReadiness
    overall: str
    overall_summary: str


@dataclass
class ReadinessMatrix:
    cells: list[ReadinessCell] = field(default_factory=list)
    threshold_legend: list[dict[str, Any]] = field(default_factory=list)


def _worst(*statuses: str) -> str:
    return max(statuses, key=lambda s: _STATUS_RANK.get(s, 99))


def _derive_overall(l1: LayerReadiness, l2: LayerReadiness, l25: LayerReadiness) -> str:
    """Overall cell status.

    When L2.5 export exists, an empty L1 index entry should not force the whole row
    to ``missing`` — downstream readiness is governed by L2 + L2.5 gates.
    """
    l25_has_export = l25.status not in (READINESS_MISSING, READINESS_UNKNOWN)
    if l1.status == READINESS_MISSING and l25_has_export:
        return _worst(l2.status, l25.status)
    return _worst(l1.status, l2.status, l25.status)


def _fmt_threshold(config: AnalysisConfig, key: str) -> str:
    try:
        t = config.get_threshold(key)
        return f"`{key}` = {t.value!r}"
    except KeyError:
        return f"`{key}` (not in registry)"


def _build_threshold_legend(config: AnalysisConfig) -> list[dict[str, Any]]:
    keys = [
        ("layer1.min_marker_coverage_pct", "L1 readiness gate"),
        ("layer1.max_missing_percent_pass", "L1 marker clean tier"),
        ("layer1.max_missing_percent_warn", "L1 marker minor-issue tier"),
        ("layer1.max_missing_percent_caution", "L1 marker caution tier"),
        ("layer1.max_large_gaps_pass", "L1 clean large-gap limit"),
        ("layer1.max_large_gaps_caution", "L1 caution large-gap limit"),
        ("layer2.rotvec_jump_warning_rad", "L2 rotvec jump warning (stage 07)"),
        ("layer2.rotvec_jump_fail_rad", "L2 rotvec jump fail (stage 07)"),
        ("layer2.rotvec_near_pi_warning_fraction", "L2 branch-cut warning fraction"),
        ("layer2.jump_context_window_frames", "L2 stage-08 mask window (±frames)"),
        ("layer2_5.warn_if", "L2.5 warning severity gate"),
        ("layer2_5.strong_warn_if", "L2.5 strong-warning gate"),
        ("layer2_5.block_if", "L2.5 blocking export gate"),
    ]
    legend: list[dict[str, Any]] = []
    for key, role in keys:
        try:
            t = config.get_threshold(key)
            legend.append(
                {
                    "registry_key": key,
                    "role": role,
                    "value": t.value,
                    "source": t.raw.get("source_config_key", "—"),
                    "description": t.description or t.scientific_meaning,
                }
            )
        except KeyError:
            legend.append({"registry_key": key, "role": role, "value": "—", "source": "—", "description": ""})
    return legend


def _derive_l1(
    session_row: dict[str, Any] | None,
    config: AnalysisConfig,
) -> LayerReadiness:
    keys = (
        "layer1.min_marker_coverage_pct",
        "layer1.max_missing_percent_pass",
        "layer1.max_missing_percent_warn",
        "layer1.max_missing_percent_caution",
    )
    if session_row is None:
        return LayerReadiness(
            READINESS_MISSING,
            "Session not in index.",
            keys,
            "No session_index row.",
        )
    warning = str(session_row.get("match_warning", "")).lower()
    l1_dir = str(session_row.get("layer1_run_dir", "")).strip()
    if "missing_layer1" in warning or not l1_dir:
        return LayerReadiness(
            READINESS_MISSING,
            "L1 QC output not present for this session.",
            keys,
            f"match_warning={session_row.get('match_warning', '') or 'missing_layer1_output'}; "
            f"governed by {_fmt_threshold(config, 'layer1.min_marker_coverage_pct')} and gap tiers "
            f"({_fmt_threshold(config, 'layer1.max_missing_percent_pass')} / "
            f"{_fmt_threshold(config, 'layer1.max_missing_percent_warn')} / "
            f"{_fmt_threshold(config, 'layer1.max_missing_percent_caution')}).",
        )
    matched = str(session_row.get("is_matched", "")).lower() == "true"
    if matched:
        return LayerReadiness(
            READINESS_PASS,
            "L1/L2 paired; L1 run directory resolved.",
            keys,
            "Detailed L1 gap-tier labels require L1 QC tables (not indexed in G2 read-only view).",
        )
    return LayerReadiness(
        READINESS_WARN,
        "L1 present but L1/L2 pairing incomplete.",
        keys,
        f"match_warning={session_row.get('match_warning', '')}",
    )


def _derive_l2(
    session_id: str,
    snapshot: ProjectSnapshot,
    config: AnalysisConfig,
) -> LayerReadiness:
    keys = (
        "layer2.rotvec_jump_warning_rad",
        "layer2.rotvec_jump_fail_rad",
        "layer2.rotvec_near_pi_warning_fraction",
        "layer2.jump_context_window_frames",
    )
    qc = snapshot.l2_qc_by_session.get(session_id)
    if qc is None:
        return LayerReadiness(
            READINESS_UNKNOWN,
            "No L2 QC session manifest for this session.",
            keys,
            "Expected at `07_rotation_vectors/qc_session_manifest.csv` or aggregated manifest.",
        )

    s07 = str(qc.get("stage07_file_status", "")).lower()
    s08 = str(qc.get("stage08_authorization_status", "")).lower()
    notes = str(qc.get("notes", "")).strip()

    if s07 == "fail":
        return LayerReadiness(
            READINESS_FAIL,
            "Stage 07 rotvec jump fail.",
            keys,
            f"{notes or 'jump exceeds fail threshold'}; "
            f"governed by {_fmt_threshold(config, 'layer2.rotvec_jump_fail_rad')} "
            f"(warn at {_fmt_threshold(config, 'layer2.rotvec_jump_warning_rad')}).",
        )
    if s08 == "blocked":
        return LayerReadiness(
            READINESS_BLOCK,
            "Stage 08 filtering blocked.",
            keys,
            f"stage08_authorization_status=blocked; mask window "
            f"{_fmt_threshold(config, 'layer2.jump_context_window_frames')}.",
        )
    if s07 == "warning":
        return LayerReadiness(
            READINESS_WARN,
            "Stage 07 rotvec jump warning.",
            keys,
            f"{notes or 'jump above warning threshold'}; "
            f"{_fmt_threshold(config, 'layer2.rotvec_jump_warning_rad')}.",
        )
    if s08 == "review_required":
        return LayerReadiness(
            READINESS_WARN,
            "Stage 08 authorized with review required.",
            keys,
            notes or "Prior stage 07 fail/warn — manual review before downstream use.",
        )
    if "near_pi" in notes.lower() or "branch" in notes.lower():
        return LayerReadiness(
            READINESS_WARN,
            "Possible branch-cut / near-π warning in notes.",
            keys,
            f"{notes}; fraction gate {_fmt_threshold(config, 'layer2.rotvec_near_pi_warning_fraction')}.",
        )
    if s07 == "pass" and s08 == "authorized":
        return LayerReadiness(
            READINESS_PASS,
            "Stage 07 pass; stage 08 authorized.",
            keys,
            notes or "Within governed L2 jump thresholds.",
        )
    return LayerReadiness(
        READINESS_UNKNOWN,
        f"L2 QC states: stage07={s07 or '?'}, stage08={s08 or '?'}",
        keys,
        notes,
    )


def _derive_l25(
    participant_id: str,
    timepoint: str,
    repetition: str,
    p_phase: str,
    snapshot: ProjectSnapshot,
    config: AnalysisConfig,
) -> LayerReadiness:
    keys = ("layer2_5.warn_if", "layer2_5.strong_warn_if", "layer2_5.block_if")
    matches = [
        r
        for r in snapshot.l25_manifest_rows
        if str(r.get("participant_id")) == participant_id
        and str(r.get("timepoint")) == timepoint
        and str(r.get("repetition")) == repetition
        and str(r.get("gaga_exercise_label")) == p_phase
        and str(r.get("export_granularity")) == "per_exercise"
    ]
    if not matches:
        return LayerReadiness(
            READINESS_MISSING,
            f"No L2.5 export row for {p_phase}.",
            keys,
            "Segment not exported to central manifest.",
        )
    row = matches[0]
    qc = str(row.get("qc_status", "")).lower()
    safe = str(row.get("layer3_safe", "")).lower()
    matrix_path = str(row.get("matrix_path", "")).strip()

    if qc == "blocking" or safe == "false":
        return LayerReadiness(
            READINESS_BLOCK,
            "Export blocked or not layer3_safe.",
            keys,
            f"qc_status={row.get('qc_status')}, layer3_safe={row.get('layer3_safe')}; "
            f"blocking rules in {_fmt_threshold(config, 'layer2_5.block_if')}.",
        )
    if qc == "warning":
        return LayerReadiness(
            READINESS_WARN,
            "Export present with QC warning status.",
            keys,
            f"qc_status=warning; strong-warning policy {_fmt_threshold(config, 'layer2_5.strong_warn_if')}; "
            f"review window_warnings.csv before Layer 3.",
        )
    if qc == "pass":
        return LayerReadiness(
            READINESS_PASS,
            "Export pass; layer3_safe.",
            keys,
            f"matrix={matrix_path or '—'}",
        )
    return LayerReadiness(
        READINESS_UNKNOWN,
        f"qc_status={row.get('qc_status', '?')}",
        keys,
        f"layer3_safe={row.get('layer3_safe')}",
    )


def _session_row_for(
    snapshot: ProjectSnapshot,
    participant_id: str,
    timepoint: str,
    repetition: str,
) -> dict[str, Any] | None:
    for row in snapshot.session_index_rows:
        if (
            str(row.get("participant_id")) == participant_id
            and str(row.get("timepoint")) == timepoint
            and str(row.get("repetition_id")) == repetition
        ):
            return row
    return None


def build_readiness_matrix(snapshot: ProjectSnapshot) -> ReadinessMatrix:
    """Build participant × session × P-phase readiness with threshold provenance."""
    config = snapshot.config
    legend = _build_threshold_legend(config)
    cells: list[ReadinessCell] = []

    keys_seen: set[tuple[str, str, str]] = set()
    for row in snapshot.session_index_rows:
        keys_seen.add(
            (
                str(row.get("participant_id", "")),
                str(row.get("timepoint", "")),
                str(row.get("repetition_id", "")),
            )
        )
    for row in snapshot.l25_manifest_rows:
        if str(row.get("export_granularity")) != "per_exercise":
            continue
        keys_seen.add(
            (
                str(row.get("participant_id", "")),
                str(row.get("timepoint", "")),
                str(row.get("repetition", "")),
            )
        )

    for participant_id, timepoint, repetition in sorted(keys_seen):
        if not participant_id:
            continue
        sess_row = _session_row_for(snapshot, participant_id, timepoint, repetition)
        session_id = str(sess_row.get("session_id", "")) if sess_row else ""
        if not session_id:
            for r in snapshot.l25_manifest_rows:
                if (
                    str(r.get("participant_id")) == participant_id
                    and str(r.get("timepoint")) == timepoint
                    and str(r.get("repetition")) == repetition
                ):
                    session_id = str(r.get("session_id", ""))
                    break

        l1 = _derive_l1(sess_row, config)
        l2 = _derive_l2(session_id, snapshot, config)

        for p_phase in GAGA_P_PHASES:
            l25 = _derive_l25(participant_id, timepoint, repetition, p_phase, snapshot, config)
            overall = _derive_overall(l1, l2, l25)
            summaries = [l1.summary, l2.summary, l25.summary]
            cells.append(
                ReadinessCell(
                    participant_id=participant_id,
                    timepoint=timepoint,
                    repetition=repetition,
                    p_phase=p_phase,
                    session_id=session_id,
                    l1=l1,
                    l2=l2,
                    l2_5=l25,
                    overall=overall,
                    overall_summary=" · ".join(s for s in summaries if s),
                )
            )

    return ReadinessMatrix(cells=cells, threshold_legend=legend)


def readiness_matrix_as_rows(matrix: ReadinessMatrix) -> list[dict[str, Any]]:
    """Flatten matrix for dataframe display."""
    rows: list[dict[str, Any]] = []
    for cell in matrix.cells:
        rows.append(
            {
                "participant": cell.participant_id,
                "timepoint": cell.timepoint,
                "repetition": cell.repetition,
                "P_phase": cell.p_phase,
                "session_id": cell.session_id,
                "L1": cell.l1.status,
                "L2": cell.l2.status,
                "L2.5": cell.l2_5.status,
                "overall": cell.overall,
                "L1_evidence": cell.l1.evidence,
                "L2_evidence": cell.l2.evidence,
                "L2.5_evidence": cell.l2_5.evidence,
            }
        )
    return rows
