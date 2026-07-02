"""Stage-gate summaries for the integrated GUI workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from comparability import ComparabilityStatus
from project_status import REGISTRY_COVERAGE, ProjectSnapshot
from readiness import build_readiness_matrix
from segmentation_coverage import (
    EXERCISE_SELECTION_ALL_IN_SHEET,
    build_segmentation_coverage_rows,
    summarize_segmentation_coverage,
)
from analysis_request import AnalysisRequestInput, comparison_spec_from_preset


@dataclass(frozen=True)
class StageGateSummary:
    stage: int
    title: str
    exists: int
    missing: int
    ready: int
    risky: int
    blocked: int
    next_action: str
    allowed_g1_g5: str
    allowed_g6: str


def _session_index_stats(snapshot: ProjectSnapshot) -> tuple[int, int, int, int]:
    rows = snapshot.session_index_rows
    if not rows:
        return 0, 0, 0, 0
    exists = len(rows)
    matched = sum(1 for r in rows if str(r.get("is_matched", "")).lower() == "true")
    missing_l1 = sum(
        1
        for r in rows
        if not str(r.get("layer1_run_dir", "")).strip()
        or "missing_layer1" in str(r.get("match_warning", "")).lower()
    )
    risky = sum(1 for r in rows if str(r.get("match_warning", "")).strip())
    blocked = exists - matched if exists else 0
    return exists, missing_l1, matched, max(risky - missing_l1, 0)


def _readiness_stats(snapshot: ProjectSnapshot) -> tuple[int, int, int, int]:
    matrix = build_readiness_matrix(snapshot)
    ready = risky = blocked = missing = 0
    for cell in matrix.cells:
        o = cell.overall.lower()
        if o == "pass":
            ready += 1
        elif o in {"warn", "strong_warning", "unknown"}:
            risky += 1
        elif o in {"fail", "block"}:
            blocked += 1
        elif o == "missing":
            missing += 1
    return len(matrix.cells), ready, risky, blocked + missing


def _segmentation_stats(snapshot: ProjectSnapshot) -> tuple[int, int, int, int, int]:
    if not snapshot.participants:
        return 0, 0, 0, 0, 0
    sheet = exported = need = risky = 0
    for pid in snapshot.participants:
        inp = AnalysisRequestInput(
            participant_id=pid,
            repetitions=("R1", "R2"),
            comparisons=[comparison_spec_from_preset("L2_T1_vs_T3", ("R1", "R2"))],
            exercise_selection_mode=EXERCISE_SELECTION_ALL_IN_SHEET,
        )
        rows, _ = build_segmentation_coverage_rows(snapshot, inp)
        summary = summarize_segmentation_coverage(rows)
        sheet += summary.get("sheet_rows", 0)
        exported += summary.get("exported", 0)
        need += summary.get("requested_not_exported", 0)
        risky += summary.get("available_not_requested", 0)
    ready = exported
    blocked = need
    return sheet, sheet - exported, ready, risky, blocked


def build_stage_gate_summaries(snapshot: ProjectSnapshot) -> list[StageGateSummary]:
    exists, missing_l1, matched, risky_idx = _session_index_stats(snapshot)
    total_cells, ready_r, risky_r, blocked_r = _readiness_stats(snapshot)
    seg_total, seg_missing, seg_ready, seg_risky, seg_blocked = _segmentation_stats(snapshot)

    return [
        StageGateSummary(
            stage=0,
            title="Project Overview",
            exists=snapshot.participants and len(snapshot.session_index_rows) or 0,
            missing=0 if snapshot.session_index_rows else 1,
            ready=1 if snapshot.path_validation_ok else 0,
            risky=0,
            blocked=0 if snapshot.path_validation_ok else 1,
            next_action="Open Stage 1 to discover L1/L2 inventory.",
            allowed_g1_g5="View pipeline status and recommendations.",
            allowed_g6="Same; no writes.",
        ),
        StageGateSummary(
            stage=1,
            title="Discover & Data Inventory",
            exists=exists,
            missing=missing_l1,
            ready=matched,
            risky=risky_idx,
            blocked=exists - matched,
            next_action="Repair session index; review unmatched sessions.",
            allowed_g1_g5="Discover scan + index repair (metadata only).",
            allowed_g6="Re-discover after pipeline runs.",
        ),
        StageGateSummary(
            stage=2,
            title="Layer 1 QC / Run Planning",
            exists=exists - missing_l1,
            missing=missing_l1,
            ready=matched,
            risky=risky_idx,
            blocked=missing_l1,
            next_action="Dry-run L1 QC for sessions missing Layer 1 output.",
            allowed_g1_g5="Dry-run command preview only.",
            allowed_g6="Execute L1 for selected sessions.",
        ),
        StageGateSummary(
            stage=3,
            title="Layer 2 QC / Run Planning",
            exists=exists,
            missing=sum(1 for r in snapshot.session_index_rows if not str(r.get("layer2_run_dir", "")).strip()),
            ready=matched,
            risky=risky_idx,
            blocked=0,
            next_action="Dry-run L2 kinematics for selected sessions.",
            allowed_g1_g5="Dry-run command preview only.",
            allowed_g6="Execute L2 for selected sessions.",
        ),
        StageGateSummary(
            stage=4,
            title="Segmentation & Export Review",
            exists=seg_total,
            missing=seg_missing,
            ready=seg_ready,
            risky=seg_risky,
            blocked=seg_blocked,
            next_action="Export xlsx exercises missing from manifest (G6+).",
            allowed_g1_g5="Full xlsx catalog coverage review.",
            allowed_g6="Run L2.5 export for selected exercises.",
        ),
        StageGateSummary(
            stage=5,
            title="QC Verification",
            exists=total_cells,
            missing=blocked_r,
            ready=ready_r,
            risky=risky_r,
            blocked=blocked_r,
            next_action="Review VerdictCards; sign off verified segments (G6+).",
            allowed_g1_g5="Read-only verification checklist.",
            allowed_g6="Write verification snapshot; unlock Stage 6.",
        ),
        StageGateSummary(
            stage=6,
            title="Analysis & JcvPCA",
            exists=len(snapshot.l25_manifest_rows),
            missing=seg_blocked,
            ready=ready_r,
            risky=risky_r,
            blocked=blocked_r,
            next_action="Build analysis request; dry-run execution plan.",
            allowed_g1_g5="Request builder + dry-run plan; read canonical batch.",
            allowed_g6="Run timestamped JcvPCA batch.",
        ),
        StageGateSummary(
            stage=7,
            title="Config / Thresholds",
            exists=len(REGISTRY_COVERAGE),
            missing=0,
            ready=1,
            risky=0 if snapshot.canonical_comparability == ComparabilityStatus.COMPARABLE else 1,
            blocked=0,
            next_action="Review threshold provenance and config hash vs canonical.",
            allowed_g1_g5="Read-only threshold view.",
            allowed_g6="Guarded threshold editing + audit log.",
        ),
    ]


def gate_for_stage(snapshot: ProjectSnapshot, stage: int) -> StageGateSummary:
    for gate in build_stage_gate_summaries(snapshot):
        if gate.stage == stage:
            return gate
    raise KeyError(f"No gate summary for stage {stage}")
