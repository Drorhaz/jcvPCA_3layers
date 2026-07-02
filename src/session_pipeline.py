"""Session discovery, index repair, and guarded L1/L2 run planning (G6 preview)."""

from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from pre_jvcpca_review.session_index import (
    DEFAULT_LAYER1_ROOT,
    DEFAULT_LAYER2_ROOT,
    SESSION_INDEX_COLUMNS,
    build_session_index,
    write_session_index,
)
from project_paths import ProjectPaths, load_project_paths

SESSION_KEY_RE = re.compile(r"(?P<subject>\d+)_T(?P<t>\d+)_P(?P<p>\d+)_R(?P<r>\d+)")


@dataclass(frozen=True)
class DiscoverSummary:
    session_index: pd.DataFrame
    index_path: Path
    n_sessions: int
    n_matched: int
    participant_ids: list[str]


@dataclass(frozen=True)
class PlannedCommand:
    layer: str
    session_ids: list[str]
    argv: list[str]
    cwd: Path
    description: str


@dataclass
class RunExecutionResult:
    planned: PlannedCommand
    returncode: int
    stdout: str
    stderr: str
    started_at: str
    finished_at: str


def default_layer1_scan_roots(paths: ProjectPaths | None = None) -> list[Path]:
    roots: list[Path] = []
    if paths is not None:
        roots.extend(
            [
                paths.project_root / "Layer1_motive_qc" / "motive_qc" / "outputs",
                paths.project_root / "Layer2.5_Segmentation" / "input" / "Layer1_QC",
            ]
        )
    else:
        roots.append(DEFAULT_LAYER1_ROOT)
    return [root for root in roots if root.is_dir()]


def default_layer1_root(paths: ProjectPaths | None = None) -> Path:
    roots = default_layer1_scan_roots(paths)
    if roots:
        return roots[0]
    return DEFAULT_LAYER1_ROOT


def default_layer2_root(paths: ProjectPaths | None = None) -> Path:
    if paths is not None:
        for candidate in (
            paths.processed_layer2,
            paths.project_root / "Layer2_Motive_Kinematics" / "outputs",
        ):
            if candidate.is_dir():
                return candidate
    return DEFAULT_LAYER2_ROOT


def processed_session_index_path(paths: ProjectPaths) -> Path:
    return paths.project_root / "processed" / "session_index.csv"


def session_id_to_l1_filter(session_id: str) -> str:
    match = SESSION_KEY_RE.fullmatch(session_id.strip())
    if not match:
        raise ValueError(f"Invalid session_id for Layer 1 filter: {session_id!r}")
    g = match.groupdict()
    return f"T{g['t']}_P{g['p']}_R{g['r']}"


def resolve_raw_layer2_csv(row: dict[str, Any], raw_layer2_root: Path) -> Path | None:
    session_id = str(row.get("session_id", "")).strip()
    participant_id = str(row.get("participant_id", "")).strip()
    timepoint = str(row.get("timepoint", "")).strip()
    if not session_id or not participant_id or not timepoint:
        return None

    tp_dir = raw_layer2_root / participant_id / timepoint
    if not tp_dir.is_dir():
        return None

    layer1_source = str(row.get("layer1_source_file", "")).strip()
    if layer1_source and layer1_source != "unknown" and layer1_source.endswith(".csv"):
        candidate = tp_dir / layer1_source
        if candidate.is_file():
            return candidate

    matches = sorted(tp_dir.glob(f"{session_id}_Take*.csv"))
    if len(matches) == 1:
        return matches[0]
    if matches:
        return matches[0]
    return None


def rebuild_session_index(
    *,
    layer1_root: Path | None = None,
    layer2_root: Path | None = None,
    index_path: Path | None = None,
    project_root: Path | None = None,
) -> DiscoverSummary:
    paths = load_project_paths(project_root=project_root)
    l1 = (layer1_root or default_layer1_root(paths)).resolve()
    l2 = (layer2_root or default_layer2_root(paths)).resolve()
    out = (index_path or processed_session_index_path(paths)).resolve()
    l1_roots = default_layer1_scan_roots(paths)
    if l1.resolve() not in {root.resolve() for root in l1_roots}:
        l1_roots.append(l1)

    index = build_session_index(layer2_root=l2, layer1_roots=l1_roots)
    if index.empty:
        raise ValueError(f"No sessions found under Layer 1 root {l1} and Layer 2 root {l2}.")

    out.parent.mkdir(parents=True, exist_ok=True)
    write_session_index(index, out)

    participant_ids = sorted(index["participant_id"].astype(str).unique().tolist())
    n_matched = int(index["is_matched"].sum())
    return DiscoverSummary(
        session_index=index,
        index_path=out,
        n_sessions=len(index),
        n_matched=n_matched,
        participant_ids=participant_ids,
    )


def load_session_index(index_path: Path) -> pd.DataFrame:
    if not index_path.is_file():
        return pd.DataFrame(columns=SESSION_INDEX_COLUMNS)
    df = pd.read_csv(index_path)
    for col in SESSION_INDEX_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[SESSION_INDEX_COLUMNS]


def plan_layer1_commands(
    rows: list[dict[str, Any]],
    *,
    repo_root: Path,
    config_path: Path | None = None,
) -> list[PlannedCommand]:
    if not rows:
        return []

    cfg = (config_path or repo_root / "Layer1_motive_qc" / "motive_qc" / "config.yaml").resolve()
    runner = repo_root / "scripts" / "run_layer1_qc.py"
    by_participant: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        sid = str(row.get("session_id", "")).strip()
        pid = str(row.get("participant_id", "")).strip()
        if not sid or not pid:
            continue
        by_participant[pid].append(session_id_to_l1_filter(sid))

    planned: list[PlannedCommand] = []
    for participant_id, filters in sorted(by_participant.items()):
        session_ids = [
            str(r.get("session_id", "")).strip()
            for r in rows
            if str(r.get("participant_id", "")).strip() == participant_id
        ]
        argv = [
            str(runner),
            "--config",
            str(cfg),
            "--subject",
            participant_id,
            "--sessions",
            ",".join(sorted(set(filters))),
            "--verbose",
        ]
        planned.append(
            PlannedCommand(
                layer="layer1",
                session_ids=[s for s in session_ids if s],
                argv=argv,
                cwd=repo_root,
                description=f"Layer 1 Motive QC for participant {participant_id}",
            )
        )
    return planned


def _layer2_output_dir_name(csv_path: Path) -> str:
    stem = csv_path.stem.replace(" ", "_").replace(":", ".")
    return stem


def plan_layer2_commands(
    rows: list[dict[str, Any]],
    *,
    repo_root: Path,
    raw_layer2_root: Path,
    config_path: Path | None = None,
    output_root: Path | None = None,
) -> list[PlannedCommand]:
    if not rows:
        return []

    cfg = (config_path or repo_root / "Layer2_Motive_Kinematics" / "configs" / "default_layer2_config.yaml").resolve()
    runner = repo_root / "scripts" / "run_layer2_session.py"
    l2_workdir = repo_root / "Layer2_Motive_Kinematics"
    _ = output_root  # reserved for future non-default output roots
    rel_output_root = Path("outputs")

    planned: list[PlannedCommand] = []
    for row in rows:
        sid = str(row.get("session_id", "")).strip()
        if not sid:
            continue
        csv_path = resolve_raw_layer2_csv(row, raw_layer2_root)
        if csv_path is None:
            planned.append(
                PlannedCommand(
                    layer="layer2",
                    session_ids=[sid],
                    argv=[],
                    cwd=l2_workdir,
                    description=f"Layer 2 blocked — raw CSV not found for {sid}",
                )
            )
            continue

        rel_output = rel_output_root / _layer2_output_dir_name(csv_path)
        run_argv = [
            str(runner),
            "run-until",
            "--input",
            str(csv_path),
            "--stage",
            "08",
            "--output-dir",
            str(rel_output),
            "--config",
            str(cfg),
        ]
        export_argv = [
            str(runner),
            "export-layer2-sessions",
            "--run-pattern",
            sid,
            "--force",
        ]
        planned.append(
            PlannedCommand(
                layer="layer2",
                session_ids=[sid],
                argv=run_argv,
                cwd=l2_workdir,
                description=f"Layer 2 run-until stage 08 for {sid}",
            )
        )
        planned.append(
            PlannedCommand(
                layer="layer2",
                session_ids=[sid],
                argv=export_argv,
                cwd=l2_workdir,
                description=f"Layer 2 export session package for {sid}",
            )
        )
    return planned


def default_layer25_output_root(paths: ProjectPaths) -> Path:
    return paths.processed_pre_jvcpca_review


def plan_layer25_commands(
    rows: list[dict[str, Any]],
    *,
    repo_root: Path,
    output_root: Path,
    export_all_sheet_exercises: bool = False,
) -> list[PlannedCommand]:
    if not rows:
        return []

    runner = repo_root / "scripts" / "run_layer2_5_export.py"
    participant_ids = sorted(
        {str(row.get("participant_id", "")).strip() for row in rows if str(row.get("participant_id", "")).strip()}
    )
    session_ids = [str(row.get("session_id", "")).strip() for row in rows if str(row.get("session_id", "")).strip()]

    argv = [str(runner), "--output-root", str(output_root)]
    for participant_id in participant_ids:
        argv.extend(["--participant", participant_id])
    if export_all_sheet_exercises:
        argv.append("--all-sheet-exercises")

    return [
        PlannedCommand(
            layer="layer2_5",
            session_ids=session_ids,
            argv=argv,
            cwd=repo_root,
            description=(
                f"Layer 2.5 Gaga export for participant(s) {', '.join(participant_ids)} "
                f"→ `{output_root}`"
            ),
        )
    ]


def execute_planned_command(
    planned: PlannedCommand,
    *,
    dry_run: bool = True,
    timeout_s: int | None = None,
) -> RunExecutionResult:
    started = datetime.now(timezone.utc).isoformat()
    if dry_run or not planned.argv:
        return RunExecutionResult(
            planned=planned,
            returncode=0 if dry_run or not planned.argv else 1,
            stdout="(dry-run — command not executed)" if dry_run else "",
            stderr="" if dry_run else "No command argv (blocked plan).",
            started_at=started,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

    proc = subprocess.run(
        planned.argv,
        cwd=str(planned.cwd),
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return RunExecutionResult(
        planned=planned,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        started_at=started,
        finished_at=datetime.now(timezone.utc).isoformat(),
    )


def append_gui_run_log(
    repo_root: Path,
    entries: list[dict[str, Any]],
) -> Path:
    log_dir = repo_root / "processed" / "pre_jvcpca_review" / "_gui_runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"session_pipeline_{stamp}.json"
    log_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return log_path
