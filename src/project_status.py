"""Read-only project snapshot for G2 GUI (paths + manifests + registry)."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from analysis_config import AnalysisConfig, load_analysis_config
from comparability import ComparabilityStatus, comparability_status, load_artifact_science_hash
from participant_discovery import ParticipantDiscovery, discover_participants
from project_paths import ProjectPaths, load_project_paths

SESSION_KEY_RE = re.compile(r"(?P<subject>\d+)_T(?P<t>\d+)_P(?P<p>\d+)_R(?P<r>\d+)")

GAGA_P_PHASES: tuple[str, ...] = ("P1", "P2", "P3", "P4", "P5")

REGISTRY_COVERAGE = {
    "layer3": {"mirrored": "full", "count": None, "label": "L3 fully registered"},
    "layer1": {"mirrored": "curated", "count": 15, "label": "L1 curated high-impact (15)"},
    "layer2": {"mirrored": "curated", "count": 7, "label": "L2 curated high-impact (7)"},
    "layer2_5": {"mirrored": "curated", "count": 6, "label": "L2.5 curated (6)"},
}


@dataclass(frozen=True)
class LayerStatusRow:
    layer: str
    status: str
    summary: str
    detail: str = ""


@dataclass
class ProjectSnapshot:
    project_root: Path
    paths: ProjectPaths
    config: AnalysisConfig
    session_index_rows: list[dict[str, Any]] = field(default_factory=list)
    l2_qc_by_session: dict[str, dict[str, Any]] = field(default_factory=dict)
    l25_manifest_rows: list[dict[str, Any]] = field(default_factory=list)
    path_validation_ok: bool = True
    path_validation_errors: list[str] = field(default_factory=list)
    canonical_batch_id: str = ""
    canonical_batch_path: Path | None = None
    canonical_batch_exists: bool = False
    canonical_config_hash: str | None = None
    canonical_comparability: ComparabilityStatus = ComparabilityStatus.UNKNOWN
    batch_dirs: list[str] = field(default_factory=list)
    participant_discovery: ParticipantDiscovery | None = None

    @property
    def participants(self) -> list[str]:
        if self.participant_discovery and self.participant_discovery.participant_ids:
            return list(self.participant_discovery.participant_ids)
        ids = {
            str(r.get("participant_id", "")).strip()
            for r in self.session_index_rows
            if str(r.get("participant_id", "")).strip()
        }
        if ids:
            return sorted(ids)
        cohort = self.paths.data.get("participants", {}).get("batch_cohort", [])
        return sorted(str(p) for p in cohort) if isinstance(cohort, list) else []

    @property
    def default_participant(self) -> str:
        if self.participant_discovery and self.participant_discovery.default_participant:
            return self.participant_discovery.default_participant
        flagship = str(self.paths.data.get("participants", {}).get("flagship", "")).strip()
        if flagship in self.participants:
            return flagship
        try:
            gui_default = str(self.config.get("default_participant")).strip()
            if gui_default in self.participants:
                return gui_default
        except KeyError:
            pass
        return self.participants[0] if self.participants else ""

    @property
    def registry_coverage(self) -> dict[str, dict[str, Any]]:
        return dict(REGISTRY_COVERAGE)


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _first_existing(*candidates: Path) -> Path | None:
    for path in candidates:
        if path.is_file():
            return path
    return None


def _resolve_session_index_path(paths: ProjectPaths) -> Path | None:
    return _first_existing(
        paths.project_root / "processed" / "session_index.csv",
        paths.project_root / "Layer2.5_Segmentation" / "outputs" / "session_index.csv",
    )


def _resolve_l25_manifest_path(paths: ProjectPaths) -> Path | None:
    return _first_existing(
        paths.layer2_5_pre_jvcpca_review / "layer25_export_manifest.csv",
        paths.processed_pre_jvcpca_review / "layer25_export_manifest.csv",
        paths.project_root
        / "Layer2.5_Segmentation"
        / "outputs"
        / "pre_jvcpca_review"
        / "layer25_export_manifest.csv",
    )


def _canonical_session_id(text: str) -> str | None:
    match = SESSION_KEY_RE.search(text)
    if not match:
        return None
    g = match.groupdict()
    return f"{g['subject']}_T{g['t']}_P{g['p']}_R{g['r']}"


def _load_l2_qc_index(paths: ProjectPaths, session_rows: list[dict[str, Any]]) -> dict[str, dict]:
    by_session: dict[str, dict[str, Any]] = {}
    for rel in (
        paths.processed_layer2 / "layer2_qc_session_manifest.csv",
        paths.project_root / "processed" / "layer2_outputs_root" / "layer2_qc_session_manifest.csv",
    ):
        for row in _read_csv_rows(rel):
            sid = str(row.get("session_id", "")).strip()
            key = _canonical_session_id(sid) or sid
            if key:
                by_session[key] = row

    scan_roots = [
        paths.processed_layer2,
        paths.project_root / "processed" / "layer2_outputs_root",
        paths.project_root / "Layer2_Motive_Kinematics" / "outputs",
    ]
    seen_paths: set[Path] = set()
    for root in scan_roots:
        if not root.is_dir():
            continue
        for qc_path in root.glob("**/07_rotation_vectors/qc_session_manifest.csv"):
            if qc_path in seen_paths:
                continue
            seen_paths.add(qc_path)
            rows = _read_csv_rows(qc_path)
            if not rows:
                continue
            key = _canonical_session_id(qc_path.parts[-3]) or _canonical_session_id(
                str(rows[0].get("session_id", ""))
            )
            if key and key not in by_session:
                by_session[key] = rows[0]

    for sess in session_rows:
        sid = str(sess.get("session_id", "")).strip()
        if not sid or sid in by_session:
            continue
        l2_dir = str(sess.get("layer2_run_dir", "")).strip()
        if not l2_dir:
            continue
        qc_path = Path(l2_dir) / "07_rotation_vectors" / "qc_session_manifest.csv"
        rows = _read_csv_rows(qc_path)
        if rows:
            by_session[sid] = rows[0]
    return by_session


def _list_layer3_batches(outputs_root: Path) -> list[str]:
    if not outputs_root.is_dir():
        return []
    batches = sorted(
        p.name
        for p in outputs_root.iterdir()
        if p.is_dir() and p.name.startswith("gaga_batch_jcvpca_")
    )
    return batches


def load_project_snapshot(
    project_root: Path | None = None,
    config_dir: Path | None = None,
) -> ProjectSnapshot:
    """Load paths, registry, session index, L2 QC, L2.5 manifest (read-only)."""
    paths = load_project_paths(project_root=project_root)
    config = load_analysis_config(config_dir=config_dir, project_root=paths.project_root)
    validation = paths.validate()

    session_index_path = _resolve_session_index_path(paths)
    session_rows = _read_csv_rows(session_index_path) if session_index_path else []

    l25_path = _resolve_l25_manifest_path(paths)
    l25_rows = _read_csv_rows(l25_path) if l25_path else []

    l2_qc = _load_l2_qc_index(paths, session_rows)

    canonical_id = paths.layer3_canonical_batch_id
    canonical_path = paths.layer3_canonical_batch
    canonical_exists = canonical_path.is_dir()
    canonical_hash = (
        load_artifact_science_hash(canonical_path) if canonical_exists else None
    )
    canonical_comp = comparability_status(
        canonical_hash,
        config.science_hash,
        is_canonical_batch=True,
    )

    outputs_root = paths.get("layer3.outputs_root")
    batches = _list_layer3_batches(outputs_root)

    gui_default: str | None = None
    try:
        gui_default = str(config.get("default_participant"))
    except KeyError:
        gui_default = None

    discovery = discover_participants(
        paths,
        session_rows=session_rows,
        l25_rows=l25_rows,
        gui_default_participant=gui_default,
    )

    return ProjectSnapshot(
        project_root=paths.project_root,
        paths=paths,
        config=config,
        session_index_rows=session_rows,
        l2_qc_by_session=l2_qc,
        l25_manifest_rows=l25_rows,
        path_validation_ok=validation.ok,
        path_validation_errors=[f"{i.dotted_key}: {i.message}" for i in validation.errors],
        canonical_batch_id=canonical_id,
        canonical_batch_path=canonical_path,
        canonical_batch_exists=canonical_exists,
        canonical_config_hash=canonical_hash,
        canonical_comparability=canonical_comp,
        batch_dirs=batches,
        participant_discovery=discovery,
    )


def pipeline_layer_status(snapshot: ProjectSnapshot) -> list[LayerStatusRow]:
    """High-level per-layer pipeline status for Project Overview."""
    rows: list[LayerStatusRow] = []

    n_sessions = len(snapshot.session_index_rows)
    n_matched = sum(1 for r in snapshot.session_index_rows if str(r.get("is_matched")).lower() == "true")
    l1_missing = sum(
        1
        for r in snapshot.session_index_rows
        if "missing_layer1" in str(r.get("match_warning", "")).lower()
    )
    if n_sessions == 0:
        l1_status, l1_summary = "missing", "No session index — run discovery or check paths."
    elif l1_missing == n_sessions:
        l1_status, l1_summary = "partial", f"{n_sessions} sessions indexed; L1 outputs missing for all."
    elif l1_missing > 0:
        l1_status, l1_summary = "partial", f"{l1_missing}/{n_sessions} sessions missing L1 outputs."
    else:
        l1_status, l1_summary = "ok", f"{n_matched}/{n_sessions} L1/L2 paired sessions."

    rows.append(
        LayerStatusRow(
            layer="Layer 1 — Motive QC",
            status=l1_status,
            summary=l1_summary,
            detail="Registry: curated 15 high-impact thresholds (not complete L1 coverage).",
        )
    )

    n_l2_qc = len(snapshot.l2_qc_by_session)
    if n_l2_qc == 0:
        l2_status, l2_summary = "missing", "No L2 QC session manifest found."
    else:
        fails = sum(
            1
            for r in snapshot.l2_qc_by_session.values()
            if str(r.get("stage07_file_status", "")).lower() == "fail"
        )
        warns = sum(
            1
            for r in snapshot.l2_qc_by_session.values()
            if str(r.get("stage07_file_status", "")).lower() == "warning"
        )
        l2_status = "ok" if fails == 0 and warns == 0 else "partial"
        l2_summary = f"{n_l2_qc} sessions with QC manifests ({warns} warn, {fails} fail at stage 07)."
    rows.append(
        LayerStatusRow(
            layer="Layer 2 — Kinematics",
            status=l2_status,
            summary=l2_summary,
            detail="Registry: curated 7 high-impact thresholds.",
        )
    )

    n_l25 = len(snapshot.l25_manifest_rows)
    if n_l25 == 0:
        l25_status, l25_summary = "missing", "No central L2.5 export manifest."
    else:
        blocking = sum(
            1
            for r in snapshot.l25_manifest_rows
            if str(r.get("qc_status", "")).lower() == "blocking"
            or str(r.get("layer3_safe", "")).lower() == "false"
        )
        warnings = sum(
            1 for r in snapshot.l25_manifest_rows if str(r.get("qc_status", "")).lower() == "warning"
        )
        l25_status = "ok" if blocking == 0 and warnings == 0 else "partial"
        l25_summary = f"{n_l25} export rows ({warnings} QC warnings, {blocking} blocking)."
    rows.append(
        LayerStatusRow(
            layer="Layer 2.5 — Segmentation / export",
            status=l25_status,
            summary=l25_summary,
            detail="Registry: curated scope + severity gates (6 entries).",
        )
    )

    if snapshot.canonical_batch_exists:
        l3_status = "ok"
        l3_summary = f"Canonical batch `{snapshot.canonical_batch_id}` present."
        if snapshot.canonical_comparability == ComparabilityStatus.PRE_REGISTRY_CANONICAL:
            l3_detail = "Pre-registry canonical (no `_config_snapshot/`); hash comparison N/A."
        else:
            l3_detail = f"Science hash: {snapshot.canonical_config_hash or 'unknown'}."
    else:
        l3_status, l3_summary = "missing", f"Canonical batch `{snapshot.canonical_batch_id}` not found."
        l3_detail = "Check `config/paths.yaml` layer3.canonical_batch."

    rows.append(
        LayerStatusRow(
            layer="Layer 3 — JcvPCA",
            status=l3_status,
            summary=l3_summary,
            detail=f"{l3_detail} Registry: full L3 coverage (~{sum(1 for t in snapshot.config.thresholds.values() if t.file == 'analysis_params.yaml')} params).",
        )
    )
    return rows


def participant_coverage_table(snapshot: ProjectSnapshot) -> list[dict[str, Any]]:
    """Participant × timepoint × repetition coverage from session index + L2.5 manifest."""
    records: dict[tuple[str, str, str], dict[str, Any]] = {}

    for row in snapshot.session_index_rows:
        key = (
            str(row.get("participant_id", "")),
            str(row.get("timepoint", "")),
            str(row.get("repetition_id", "")),
        )
        if not key[0]:
            continue
        rec = records.setdefault(
            key,
            {
                "participant_id": key[0],
                "timepoint": key[1],
                "repetition": key[2],
                "session_id": str(row.get("session_id", "")),
                "l1_l2_matched": str(row.get("is_matched", "")).lower() == "true",
                "match_warning": str(row.get("match_warning", "")),
                "p_phases_exported": set(),
            },
        )
        rec["session_id"] = str(row.get("session_id", ""))

    for row in snapshot.l25_manifest_rows:
        if str(row.get("export_granularity", "")) != "per_exercise":
            continue
        label = str(row.get("gaga_exercise_label", ""))
        if label not in GAGA_P_PHASES:
            continue
        key = (
            str(row.get("participant_id", "")),
            str(row.get("timepoint", "")),
            str(row.get("repetition", "")),
        )
        if key not in records:
            records[key] = {
                "participant_id": key[0],
                "timepoint": key[1],
                "repetition": key[2],
                "session_id": str(row.get("session_id", "")),
                "l1_l2_matched": False,
                "match_warning": "",
                "p_phases_exported": set(),
            }
        records[key]["p_phases_exported"].add(label)

    out: list[dict[str, Any]] = []
    for rec in sorted(records.values(), key=lambda r: (r["participant_id"], r["timepoint"], r["repetition"])):
        phases = sorted(rec["p_phases_exported"])
        out.append(
            {
                **{k: v for k, v in rec.items() if k != "p_phases_exported"},
                "p_phases_exported": ",".join(phases) if phases else "—",
                "p_phase_count": len(phases),
                "p_phase_complete": len(phases) == len(GAGA_P_PHASES),
            }
        )
    return out
