"""Importable window-review runner and output loaders for notebook UX."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd

from layer2_motive.segmentation.load_inputs import (
    load_layer1_qc_folder,
    load_layer2_export_folder,
)
from layer2_motive.segmentation.marker_family import build_mapper_from_datadescriptions
from layer2_motive.segmentation.qc_events import (
    build_layer1_event_table,
    gap_files_status,
    looks_like_marker_name,
)
from layer2_motive.segmentation.schemas import (
    COMBINED_QC_EVENT_SUMMARY_COLUMNS,
    DEFAULT_L2_EVIDENCE_TYPES,
    LAYER1_MARKER_FAMILY_RISK_COLUMNS,
    LAYER2_LINK_SCOPE_DISPLAY_COLUMNS,
    QC_EVENT_DISPLAY_COLUMNS,
    WINDOW_QC_SUMMARY_DISPLAY_COLUMNS,
    ExportScopePolicy,
    GapPolicy,
    QCEvidencePolicy,
    _normalize_qc_type_for_policy,
)
from layer2_motive.segmentation.validate_inputs import run_all_validations
from layer2_motive.segmentation.window_summary import (
    build_combined_qc_event_table,
    parse_l1_evidence_arg,
    parse_l2_evidence_arg,
    subset_layer1_events_to_window,
    subset_layer2_to_window,
    summarize_layer1_window,
    summarize_layer2_window,
    write_window_review_outputs,
)

COMPACT_TABLE_FILES = {
    "window_qc_summary": "window_qc_summary_display.csv",
    "qc_event_display": "qc_event_display.csv",
    "layer2_link_scope": "layer2_link_scope_display.csv",
    "layer1_marker_family_risk": "layer1_marker_family_risk.csv",
    "combined_qc_event_summary": "combined_qc_event_summary.csv",
}

AUDIT_FILE = "combined_qc_events.csv"
SUMMARY_JSON = "window_validation_summary.json"
REPORT_MD = "window_review_report.md"

NOTEBOOK_QC_EVIDENCE_OPTIONS = (
    "gap_0p5",
    "gap_0p2",
    "artifact_sigma",
    "segment_swap",
)

SCIENTIST_QC_EVENT_COLUMNS = (
    "Frame start",
    "Frame end",
    "Duration",
    "QC type",
    "Reason",
    "Marker / region",
    "Related joint family",
    "Confidence",
)

SCIENTIST_LINK_JOINT_COLUMNS = (
    "Link / joint",
    "Family",
    "L1 gap_0p5",
    "L1 artifact %",
    "L1 swap %",
    "L2 usable %",
    "Status",
)

UNLABELED_QC_TYPES = frozenset(
    {
        "frame_status",
        "interval_status",
        "edge_effect",
    }
)

QC_TYPE_DISPLAY_MAP = {
    "marker_gap_0p2": "gap_0p2",
    "marker_gap_0p5": "gap_0p5",
    "artifact_sigma": "artifact_sigma",
    "segment_swap": "segment_swap",
}


class ReviewOutputError(FileNotFoundError):
    """Raised when expected review output files are missing."""


@dataclass
class WindowReviewResult:
    out_dir: Path
    safe_to_open: bool
    blocking_errors: list[str]
    warnings: list[str]
    mapper_warnings: list[str]
    requested_start_frame: int
    requested_end_frame: int
    start_frame: int
    end_frame: int
    gap_policy: str
    export_scope: str
    datadescriptions_used: bool
    mapping_version: str
    n_combined_events: int
    n_layer1_events: int
    n_layer2_events: int
    n_total_layer2_links: int = 0
    n_included_layer2_links: int = 0
    n_session_labeled_markers: int = 0
    qc_evidence_selected: tuple[str, ...] = ()


@dataclass
class ReviewOutputs:
    out_dir: Path
    window_qc_summary: pd.DataFrame
    qc_event_display: pd.DataFrame
    layer2_link_scope: pd.DataFrame
    layer1_marker_family_risk: pd.DataFrame
    combined_qc_event_summary: pd.DataFrame


@dataclass
class AuditFileInfo:
    path: Path
    row_count: int
    size_bytes: int


def _normalize_datadescriptions_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    text = str(path).strip()
    return text or None


@dataclass
class ReviewInputSummary:
    frame_start: int
    frame_end: int
    duration_frames: int
    qc_evidence_selected: list[str]
    gap_policy_internal: str
    labeled_markers_total: int
    labeled_markers_mapped: int
    labeled_markers_unmapped: int
    session_labeled_markers: int
    unlabeled_evidence_in_main_ux: bool
    total_layer2_links: int
    included_layer2_links: int
    export_scope: str
    datadescriptions_used: bool
    mapping_source: str | None
    template_mapping_status: str | None
    mapping_version: str | None


def gap_policy_from_qc_evidence(qc_evidence: list[str] | tuple[str, ...]) -> str:
    """Derive internal gap policy from notebook QC evidence selection."""
    return "strict" if "gap_0p2" in qc_evidence else "relaxed"


def normalize_notebook_qc_evidence(
    qc_evidence: list[str] | tuple[str, ...] | None,
) -> tuple[str, ...]:
    if not qc_evidence:
        return NOTEBOOK_QC_EVIDENCE_OPTIONS
    selected = tuple(qc_evidence)
    unknown = set(selected) - set(NOTEBOOK_QC_EVIDENCE_OPTIONS)
    if unknown:
        raise ValueError(f"Unsupported QC evidence types: {', '.join(sorted(unknown))}")
    return selected


def run_review_from_notebook(
    layer1_dir: str | Path,
    layer2_dir: str | Path,
    start_frame: int,
    end_frame: int,
    *,
    qc_evidence: list[str] | tuple[str, ...] | None = None,
    export_scope: str = "core_candidate",
    datadescriptions: str | Path | None = None,
    out: str | Path | None = None,
    force_session_match: bool = False,
) -> WindowReviewResult:
    """Notebook entry point: map QC evidence selection to backend policies."""
    selected = normalize_notebook_qc_evidence(qc_evidence)
    result = run_window_review(
        layer1_dir,
        layer2_dir,
        start_frame,
        end_frame,
        gap_policy=gap_policy_from_qc_evidence(selected),
        export_scope=export_scope,
        l1_evidence=",".join(selected),
        l2_evidence=",".join(sorted(DEFAULT_L2_EVIDENCE_TYPES)),
        datadescriptions=datadescriptions,
        out=out,
        force_session_match=force_session_match,
    )
    return replace(result, qc_evidence_selected=selected)


def _count_included_layer2_links(
    per_link_summary: pd.DataFrame,
    export_scope_policy: ExportScopePolicy,
) -> int:
    if per_link_summary.empty:
        return 0
    count = 0
    for _, link in per_link_summary.iterrows():
        feature_scope = str(link["feature_scope"])
        included = export_scope_policy.link_included(feature_scope)
        if included or export_scope_policy.export_scope == "all_links_audit":
            count += 1
    return count


def _is_labeled_marker_risk_row(row: pd.Series) -> bool:
    marker = row.get("marker_or_entity")
    if looks_like_marker_name(marker):
        return True
    return looks_like_marker_name(row.get("normalized_marker_name"))


def count_labeled_markers(marker_family_risk: pd.DataFrame) -> tuple[int, int, int]:
    """Return unique total, mapped, and unmapped labeled marker counts."""
    if marker_family_risk.empty:
        return 0, 0, 0
    labeled = marker_family_risk.loc[
        marker_family_risk.apply(_is_labeled_marker_risk_row, axis=1)
    ].copy()
    if labeled.empty:
        return 0, 0, 0
    labeled["_marker_key"] = labeled.apply(
        lambda row: str(row["normalized_marker_name"])
        if looks_like_marker_name(row.get("normalized_marker_name"))
        else str(row["marker_or_entity"]),
        axis=1,
    )
    unique = labeled.drop_duplicates(subset=["_marker_key"])
    total = len(unique)
    mapped_mask = (unique["mapping_source"].astype(str) != "unmapped") & (
        unique["joint_family"].astype(str) != "unknown"
    )
    mapped = int(mapped_mask.sum())
    return total, mapped, total - mapped


def _policy_qc_type(qc_type: str) -> str:
    return _normalize_qc_type_for_policy(str(qc_type))


def _is_labeled_marker_event(row: pd.Series) -> bool:
    qc_type = str(row.get("qc_type", ""))
    if _policy_qc_type(qc_type) in UNLABELED_QC_TYPES:
        return False
    for field in ("normalized_marker_name", "marker_or_region"):
        if field in row.index and looks_like_marker_name(row.get(field)):
            return True
    return False


def _format_percent(value: Any) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.1f}%"


def prepare_scientist_qc_event_table(
    qc_event_display: pd.DataFrame,
    *,
    qc_evidence: list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Simplified labeled-marker QC event table for notebook display."""
    selected = set(normalize_notebook_qc_evidence(qc_evidence))
    if qc_event_display.empty:
        return pd.DataFrame(columns=list(SCIENTIST_QC_EVENT_COLUMNS))

    work = qc_event_display.loc[qc_event_display["source_layer"] == "layer1"].copy()
    work = work.loc[work.apply(_is_labeled_marker_event, axis=1)]
    work["_policy_qc_type"] = work["qc_type"].map(_policy_qc_type)
    work = work.loc[work["_policy_qc_type"].isin(selected)]

    out = pd.DataFrame(
        {
            "Frame start": work["frame_start"],
            "Frame end": work["frame_end"],
            "Duration": work["duration_frames"],
            "QC type": work["_policy_qc_type"],
            "Reason": work["reason"],
            "Marker / region": work["marker_or_region"],
            "Related joint family": work["related_joint_family"],
            "Confidence": work["mapping_confidence"],
        }
    )
    return out.loc[:, list(SCIENTIST_QC_EVENT_COLUMNS)]


def prepare_scientist_link_joint_table(layer2_link_scope: pd.DataFrame) -> pd.DataFrame:
    """Simplified link/joint review table for notebook display."""
    if layer2_link_scope.empty:
        return pd.DataFrame(columns=list(SCIENTIST_LINK_JOINT_COLUMNS))

    out = pd.DataFrame(
        {
            "Link / joint": layer2_link_scope["link_or_joint"],
            "Family": layer2_link_scope["family"],
            "L1 gap_0p5": layer2_link_scope["n_gap_0p5_related_frames"],
            "L1 artifact %": layer2_link_scope["artifact_sigma_related_percent"].map(
                _format_percent
            ),
            "L1 swap %": layer2_link_scope["segment_swap_related_percent"].map(_format_percent),
            "L2 usable %": layer2_link_scope["layer2_usable_percent"].map(_format_percent),
            "Status": layer2_link_scope["recommendation_placeholder"],
        }
    )
    return out.loc[:, list(SCIENTIST_LINK_JOINT_COLUMNS)]


def prepare_review_input_summary(
    result: WindowReviewResult,
    outputs: ReviewOutputs,
    summary: dict[str, Any],
) -> ReviewInputSummary:
    """Build structured review input summary for notebook display."""
    total_markers, mapped_markers, unmapped_markers = count_labeled_markers(
        outputs.layer1_marker_family_risk
    )
    selected = list(result.qc_evidence_selected) or list(NOTEBOOK_QC_EVIDENCE_OPTIONS)
    duration = int(result.end_frame - result.start_frame + 1)
    total_links = int(result.n_total_layer2_links)
    included_links = int(result.n_included_layer2_links)
    if included_links == 0 and not outputs.layer2_link_scope.empty:
        included_links = len(outputs.layer2_link_scope)

    return ReviewInputSummary(
        frame_start=result.start_frame,
        frame_end=result.end_frame,
        duration_frames=duration,
        qc_evidence_selected=selected,
        gap_policy_internal=result.gap_policy,
        labeled_markers_total=total_markers,
        labeled_markers_mapped=mapped_markers,
        labeled_markers_unmapped=unmapped_markers,
        session_labeled_markers=int(result.n_session_labeled_markers),
        unlabeled_evidence_in_main_ux=False,
        total_layer2_links=total_links,
        included_layer2_links=included_links,
        export_scope=result.export_scope,
        datadescriptions_used=bool(
            summary.get("datadescriptions_used", result.datadescriptions_used)
        ),
        mapping_source=summary.get("mapping_source"),
        template_mapping_status=summary.get("template_mapping_status"),
        mapping_version=summary.get("mapping_version", result.mapping_version),
    )


def format_review_input_summary_markdown(summary: ReviewInputSummary) -> str:
    """Render the review input summary as markdown."""
    qc_text = ", ".join(summary.qc_evidence_selected)
    mapping_used = "Yes" if summary.datadescriptions_used else "No"
    mapping_source = summary.mapping_source or "n/a"
    template_status = summary.template_mapping_status or "n/a"
    mapping_version = summary.mapping_version or "n/a"
    unlabeled_in_ux = "Yes" if summary.unlabeled_evidence_in_main_ux else "No"
    excluded_links = summary.total_layer2_links - summary.included_layer2_links
    return f"""## Review Input Summary

**Frame window**
- frame_start: {summary.frame_start}
- frame_end: {summary.frame_end}
- duration_frames: {summary.duration_frames}

**QC evidence included**
- {qc_text}

**Labeled marker evidence**
- Markers with QC events in this window: {summary.labeled_markers_total}
- Mapped in review: {summary.labeled_markers_mapped}
- Unmapped / review-unknown: {summary.labeled_markers_unmapped}
- Session labeled-marker inventory: {summary.session_labeled_markers}
- Unlabeled-marker evidence in main UX: {unlabeled_in_ux}

**Layer 2 links/joints**
- Full skeleton manifest: {summary.total_layer2_links} links (includes fingers/toes/distal chain)
- Included by scope ({summary.export_scope}): {summary.included_layer2_links} links
- Excluded from this scope: {excluded_links} links

**Mapping**
- DataDescriptions used: {mapping_used}
- Mapping source: {mapping_source}
- Template mapping status: {template_status}
- Mapping version: {mapping_version}
"""


def _default_out_dir(
    layer1_dir: str | Path,
    start_frame: int,
    end_frame: int,
    gap_policy: str,
    export_scope: str,
) -> Path:
    l1 = Path(layer1_dir).resolve()
    session_key = l1.name.removeprefix("QC_")
    return (
        Path("outputs")
        / "window_review"
        / f"{session_key}_{start_frame}_{end_frame}_{gap_policy}"
    )


def run_window_review(
    layer1_dir: str | Path,
    layer2_dir: str | Path,
    start_frame: int,
    end_frame: int,
    *,
    gap_policy: str = "strict",
    export_scope: str = "core_candidate",
    l1_evidence: str | None = None,
    l2_evidence: str | None = None,
    datadescriptions: str | Path | None = None,
    mapping_version: str | None = None,
    out: str | Path | None = None,
    force_session_match: bool = False,
) -> WindowReviewResult:
    """Run Phase A+ window review and write outputs to disk."""
    requested_start = int(start_frame)
    requested_end = int(end_frame)
    if requested_end < requested_start:
        raise ValueError("end_frame must be >= start_frame")

    l1 = load_layer1_qc_folder(layer1_dir)
    l2 = load_layer2_export_folder(layer2_dir)

    validation = run_all_validations(l1, l2, force=force_session_match)
    if not validation.safe_to_open:
        raise ValueError(
            "Validation blocked. Cannot review window. "
            + "; ".join(validation.blocking_errors)
        )

    assert validation.identity is not None
    assert validation.alignment is not None

    overlap_start = validation.alignment.overlap_start_frame
    overlap_end = validation.alignment.overlap_end_frame
    if overlap_start is None or overlap_end is None:
        raise ValueError("No frame overlap between Layer 1 and Layer 2.")

    effective_start = max(requested_start, overlap_start)
    effective_end = min(requested_end, overlap_end)
    if effective_end < effective_start:
        raise ValueError("Requested window outside overlapping frame range.")

    gap_policy_obj = GapPolicy(policy=gap_policy)
    export_scope_policy = ExportScopePolicy(export_scope=export_scope)
    evidence_policy = QCEvidencePolicy(
        l1_evidence_types=parse_l1_evidence_arg(l1_evidence),
        l2_evidence_types=parse_l2_evidence_arg(l2_evidence),
    )

    review_warnings: list[str] = []
    dd_path = _normalize_datadescriptions_path(datadescriptions)
    mapper = build_mapper_from_datadescriptions(dd_path, review_warnings)
    resolved_mapping_version = mapping_version or mapper.mapping_version

    session_key = validation.identity.session_key
    layer1_events = build_layer1_event_table(l1, session_key, mapper=mapper)
    l1_window_events = subset_layer1_events_to_window(
        layer1_events, effective_start, effective_end
    )
    l2_window_df = subset_layer2_to_window(l2.parquet_df, effective_start, effective_end)

    frame_col = str(l1.manifest.get("frame_index_column", "frame"))
    layer1_summary = summarize_layer1_window(
        l1.qc_mask,
        l1_window_events,
        effective_start,
        effective_end,
        frame_col=frame_col,
        gap_policy=gap_policy_obj,
    )
    layer2_summary = summarize_layer2_window(
        l2.parquet_df,
        l2.link_manifest,
        effective_start,
        effective_end,
    )
    combined = build_combined_qc_event_table(
        l1_window_events,
        l2_window_df,
        l2.link_manifest,
        mapper=mapper,
        mapping_version=resolved_mapping_version,
    )

    all_warnings = list(validation.warnings) + review_warnings
    validation.warnings = all_warnings

    out_path = Path(out) if out is not None else _default_out_dir(
        layer1_dir, effective_start, effective_end, gap_policy, export_scope
    )

    written = write_window_review_outputs(
        out_path,
        validation_result=validation,
        identity=validation.identity,
        layer1_bundle=l1,
        layer2_bundle=l2,
        start_frame=effective_start,
        end_frame=effective_end,
        layer1_summary=layer1_summary,
        layer2_summary=layer2_summary,
        combined_events=combined,
        gap_status=gap_files_status(l1),
        gap_policy=gap_policy_obj,
        export_scope_policy=export_scope_policy,
        evidence_policy=evidence_policy,
        mapper=mapper,
        layer1_window_events=l1_window_events,
    )

    n_l1 = int((combined["source_layer"] == "layer1").sum()) if not combined.empty else 0
    n_l2 = int((combined["source_layer"] == "layer2").sum()) if not combined.empty else 0
    n_total_links = len(l2.link_manifest)
    n_included_links = _count_included_layer2_links(
        layer2_summary["per_link_summary"],
        export_scope_policy,
    )
    session_markers = {
        str(marker).strip()
        for marker in layer1_events.get("marker_raw_name", pd.Series(dtype=object)).dropna()
        if looks_like_marker_name(marker)
    }

    return WindowReviewResult(
        out_dir=written,
        safe_to_open=validation.safe_to_open,
        blocking_errors=list(validation.blocking_errors),
        warnings=all_warnings,
        mapper_warnings=review_warnings,
        requested_start_frame=requested_start,
        requested_end_frame=requested_end,
        start_frame=effective_start,
        end_frame=effective_end,
        gap_policy=gap_policy,
        export_scope=export_scope,
        datadescriptions_used=mapper.datadescriptions_used,
        mapping_version=resolved_mapping_version,
        n_combined_events=len(combined),
        n_layer1_events=n_l1,
        n_layer2_events=n_l2,
        n_total_layer2_links=n_total_links,
        n_included_layer2_links=n_included_links,
        n_session_labeled_markers=len(session_markers),
        qc_evidence_selected=tuple(sorted(evidence_policy.l1_evidence_types)),
    )


def collect_output_paths(out_dir: str | Path) -> dict[str, Path]:
    """Return paths to all known review output files."""
    root = Path(out_dir)
    paths = {key: root / filename for key, filename in COMPACT_TABLE_FILES.items()}
    paths["combined_qc_events"] = root / AUDIT_FILE
    paths["window_validation_summary"] = root / SUMMARY_JSON
    paths["window_review_report"] = root / REPORT_MD
    return paths


def _read_csv_or_raise(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise ReviewOutputError(f"Missing review output file ({label}): {path}")
    return pd.read_csv(path)


def load_review_outputs(out_dir: str | Path) -> ReviewOutputs:
    """Load the five compact display tables from a review output folder."""
    paths = collect_output_paths(out_dir)
    return ReviewOutputs(
        out_dir=Path(out_dir),
        window_qc_summary=_read_csv_or_raise(
            paths["window_qc_summary"], "window_qc_summary_display.csv"
        ),
        qc_event_display=_read_csv_or_raise(paths["qc_event_display"], "qc_event_display.csv"),
        layer2_link_scope=_read_csv_or_raise(
            paths["layer2_link_scope"], "layer2_link_scope_display.csv"
        ),
        layer1_marker_family_risk=_read_csv_or_raise(
            paths["layer1_marker_family_risk"], "layer1_marker_family_risk.csv"
        ),
        combined_qc_event_summary=_read_csv_or_raise(
            paths["combined_qc_event_summary"], "combined_qc_event_summary.csv"
        ),
    )


def load_summary_json(out_dir: str | Path) -> dict[str, Any]:
    """Load window_validation_summary.json from a review output folder."""
    path = Path(out_dir) / SUMMARY_JSON
    if not path.exists():
        raise ReviewOutputError(f"Missing review summary JSON: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _count_csv_rows(path: Path) -> int:
    with path.open(encoding="utf-8") as fh:
        # subtract header line
        return max(sum(1 for _ in fh) - 1, 0)


def audit_file_info(out_dir: str | Path) -> AuditFileInfo:
    """Return metadata for the full audit combined_qc_events.csv file."""
    path = Path(out_dir) / AUDIT_FILE
    if not path.exists():
        raise ReviewOutputError(f"Missing audit file: {path}")
    return AuditFileInfo(
        path=path,
        row_count=_count_csv_rows(path),
        size_bytes=path.stat().st_size,
    )


def load_audit_preview(out_dir: str | Path, *, nrows: int = 200) -> pd.DataFrame:
    """Load the first N rows of the full audit table."""
    info = audit_file_info(out_dir)
    return pd.read_csv(info.path, nrows=nrows)


def validate_compact_table_columns(outputs: ReviewOutputs) -> None:
    """Raise ValueError if compact tables do not match expected schemas."""
    expected = {
        "window_qc_summary": WINDOW_QC_SUMMARY_DISPLAY_COLUMNS,
        "qc_event_display": QC_EVENT_DISPLAY_COLUMNS,
        "layer2_link_scope": LAYER2_LINK_SCOPE_DISPLAY_COLUMNS,
        "layer1_marker_family_risk": LAYER1_MARKER_FAMILY_RISK_COLUMNS,
        "combined_qc_event_summary": COMBINED_QC_EVENT_SUMMARY_COLUMNS,
    }
    for name, cols in expected.items():
        df = getattr(outputs, name)
        if list(df.columns) != list(cols):
            raise ValueError(f"{name} columns do not match expected schema")
