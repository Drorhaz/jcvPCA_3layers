"""Review output paths and pre-flight checks for notebook / CLI review actions."""

from __future__ import annotations

from pathlib import Path

from pre_jvcpca_review.mapping import MappingEntry

REVIEW_TABLE_FILES = (
    "mapping_logic_table.csv",
    "window_decision_summary.csv",
    "qc_evidence_summary_table.csv",
    "link_joint_review_table.csv",
    "qc_event_review_table.csv",
    "window_warnings.csv",
)


def review_base_dir(output_root: Path) -> Path:
    return Path(output_root)


def resolve_review_out_dir(
    output_root: Path,
    participant_id: str,
    session_id: str,
    window_label: str,
) -> Path:
    """Deterministic review folder: ``<root>/<participant>/<session>/<window_label>``."""
    return review_base_dir(output_root) / str(participant_id) / str(session_id) / str(window_label)


def participant_out_dir(output_root: Path, participant_id: str) -> Path:
    return review_base_dir(output_root) / str(participant_id)


def require_review_context(
    *,
    current_row,
    layer1_dir: str | Path,
    layer2_dir: str | Path,
) -> str | None:
    """Return an error message when review actions cannot run, else ``None``."""
    if current_row is None:
        return "Select a participant and session first (run Discover participants/sessions)."
    l1 = Path(layer1_dir) if layer1_dir else None
    l2 = Path(layer2_dir) if layer2_dir else None
    if l1 is None or not str(layer1_dir).strip() or not l1.is_dir():
        return (
            "Layer 1 session directory is missing. Run Discover and select a session "
            "with a matched Layer 1 output."
        )
    if l2 is None or not str(layer2_dir).strip() or not l2.is_dir():
        return (
            "Layer 2 session directory is missing. Run Discover and select a session "
            "with a matched Layer 2 output."
        )
    if not bool(current_row.get("is_matched", False)):
        return (
            f"Session {current_row.get('session_id', '')} is not matched "
            f"({current_row.get('match_warning', '')}). Review requires paired L1/L2 outputs."
        )
    return None


def datadescriptions_meta(path: Path | None) -> dict[str, object]:
    found = path is not None and path.is_file()
    return {
        "datadescriptions_path": str(path.resolve()) if found else (str(path) if path else ""),
        "datadescriptions_found": found,
        "datadescriptions_used": found,
    }


def infer_mapping_mode(datadescriptions_used: bool, entries: list[MappingEntry]) -> str:
    if not datadescriptions_used:
        return "heuristic"
    mapped = sum(1 for entry in entries if entry.mapping_status == "mapped")
    unmapped = sum(1 for entry in entries if entry.mapping_status == "unmapped")
    if mapped and unmapped:
        return "mixed"
    return "datadescriptions"


def unmapped_link_ids(entries: list[MappingEntry], selected_link_ids: list[str]) -> list[str]:
    """Selected link IDs with no mapped marker evidence in the scoped mapping table."""
    covered: set[str] = set()
    for entry in entries:
        if entry.mapping_status != "mapped":
            continue
        covered.update(entry.candidate_link_ids)
    return sorted(set(selected_link_ids) - covered)
