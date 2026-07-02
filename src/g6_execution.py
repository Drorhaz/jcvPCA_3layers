"""G6 guarded execution: canonical guards, audit logs, pipeline subprocess runs."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from project_status import ProjectSnapshot
from session_pipeline import PlannedCommand, RunExecutionResult, append_gui_run_log, execute_planned_command


class G6GuardError(ValueError):
    """Raised when a G6 action would touch protected artifacts."""


G6_SESSION_KEY = "g6_execution_enabled"


def change_audit_log_path(project_root: Path) -> Path:
    return project_root / "config" / "change_audit.log"


def verification_snapshot_path(project_root: Path) -> Path:
    return project_root / "processed" / "pre_jvcpca_review" / "verification_snapshot.yaml"


def append_change_audit_log(project_root: Path, record: dict[str, Any]) -> Path:
    """Append one JSON line to ``config/change_audit.log``."""
    path = change_audit_log_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = dict(record)
    entry.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return path


def assert_non_canonical_batch_path(path: Path, snapshot: ProjectSnapshot) -> None:
    """Fail fast if ``path`` resolves to the canonical Layer 3 batch."""
    resolved = path.resolve()
    canonical = snapshot.canonical_batch_path
    if canonical is not None and resolved == canonical.resolve():
        raise G6GuardError(
            f"Refusing to write to canonical batch path: {canonical}"
        )
    if snapshot.canonical_batch_id and resolved.name == snapshot.canonical_batch_id:
        raise G6GuardError(
            f"Refusing to use canonical batch id: {snapshot.canonical_batch_id}"
        )


def prepare_plan_for_g6_execution(plan: dict[str, Any]) -> dict[str, Any]:
    """Return a plan copy with ``execution.allowed`` set from preflight blockers."""
    updated = dict(plan)
    preflight = plan.get("preflight") or {}
    blockers = preflight.get("blockers") or []
    execution = dict(plan.get("execution") or {})
    execution["allowed"] = len(blockers) == 0
    execution["note"] = (
        "G6 guarded execution permitted (no preflight blockers)."
        if execution["allowed"]
        else f"G6 blocked — {len(blockers)} preflight blocker(s)."
    )
    updated["execution"] = execution
    return updated


def execute_pipeline_commands(
    planned: list[PlannedCommand],
    *,
    dry_run: bool = False,
    timeout_s: int | None = 7200,
) -> list[RunExecutionResult]:
    """Run a sequence of planned shell commands (L1/L2/L2.5)."""
    return [
        execute_planned_command(cmd, dry_run=dry_run, timeout_s=timeout_s)
        for cmd in planned
    ]


def log_pipeline_results(
    repo_root: Path,
    results: list[RunExecutionResult],
    *,
    action: str,
    extra: dict[str, Any] | None = None,
) -> Path:
    entries: list[dict[str, Any]] = []
    for result in results:
        entries.append(
            {
                "action": action,
                "layer": result.planned.layer,
                "description": result.planned.description,
                "session_ids": result.planned.session_ids,
                "argv": result.planned.argv,
                "cwd": str(result.planned.cwd),
                "returncode": result.returncode,
                "started_at": result.started_at,
                "finished_at": result.finished_at,
                "stdout_tail": (result.stdout or "")[-4000:],
                "stderr_tail": (result.stderr or "")[-4000:],
                **(extra or {}),
            }
        )
    return append_gui_run_log(repo_root, entries)


def build_layer3_argv(
    repo_root: Path,
    runner_plan: dict[str, Any],
    *,
    batch_root: Path | None = None,
    analysis_request_path: Path | str | None = None,
    smoke: bool = False,
) -> list[str]:
    """Build argv for ``scripts/run_layer3_batch.py`` from a runner translation plan."""
    script = repo_root / "scripts" / "run_layer3_batch.py"
    out = batch_root or Path(runner_plan["proposed_batch_root"])
    layer25 = Path(runner_plan["layer25_root"])
    argv = [
        str(script),
        "--output-dir",
        str(out),
        "--layer25-root",
        str(layer25),
        "--project-root",
        str(repo_root),
    ]
    if analysis_request_path:
        argv.extend(["--request", str(analysis_request_path)])
    if smoke:
        argv.append("--smoke")
    for participant_id in runner_plan.get("participant_ids") or []:
        argv.extend(["--participant", str(participant_id)])
    return argv


def execute_layer3_batch(
    repo_root: Path,
    snapshot: ProjectSnapshot,
    runner_plan: dict[str, Any],
    *,
    batch_root: Path | None = None,
    analysis_request_path: Path | str | None = None,
    smoke: bool = False,
    dry_run: bool = False,
    timeout_s: int | None = 14400,
) -> dict[str, Any]:
    """Run Layer 3 batch via guarded subprocess; never targets canonical batch."""
    out = (batch_root or Path(runner_plan["proposed_batch_root"])).resolve()
    assert_non_canonical_batch_path(out, snapshot)

    argv = build_layer3_argv(
        repo_root,
        runner_plan,
        batch_root=out,
        analysis_request_path=analysis_request_path,
        smoke=smoke,
    )
    started = datetime.now(timezone.utc).isoformat()

    if dry_run:
        return {
            "argv": argv,
            "batch_root": str(out),
            "returncode": 0,
            "stdout": "(dry-run — Layer 3 batch not executed)",
            "stderr": "",
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }

    proc = subprocess.run(
        argv,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    finished = datetime.now(timezone.utc).isoformat()
    result = {
        "argv": argv,
        "batch_root": str(out),
        "returncode": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "started_at": started,
        "finished_at": finished,
    }

    log_pipeline_results(
        repo_root,
        [],
        action="layer3_batch",
        extra={
            "argv": argv,
            "batch_root": str(out),
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-4000:],
            "stderr_tail": (proc.stderr or "")[-4000:],
            "started_at": started,
            "finished_at": finished,
        },
    )
    return result


def execute_on_demand_reports(
    repo_root: Path,
    snapshot: ProjectSnapshot,
    batch_root: Path,
    *,
    generate_full_numeric_reports: str = "on_demand",
    generate_poster_package: str = "on_demand",
) -> dict[str, Any]:
    """Generate heavy Layer 3 reports for a timestamped batch (force on-demand policies)."""
    out = batch_root.resolve()
    assert_non_canonical_batch_path(out, snapshot)
    started = datetime.now(timezone.utc).isoformat()

    layer3_src = repo_root / "Layer3_JcvPCA" / "src"
    entry = str(layer3_src)
    if layer3_src.is_dir() and entry not in sys.path:
        sys.path.insert(0, entry)

    from layer3_jcvpca.on_demand_reports import generate_on_demand_reports

    manifest = generate_on_demand_reports(
        out,
        generate_full_numeric_reports=generate_full_numeric_reports,
        generate_poster_package=generate_poster_package,
        project_root=repo_root,
        force=True,
    )
    finished = datetime.now(timezone.utc).isoformat()
    append_change_audit_log(
        repo_root,
        {
            "action": "g6_on_demand_reports",
            "batch_root": str(out),
            "manifest_path": manifest.get("manifest_path"),
        },
    )
    return {
        "batch_root": str(out),
        "manifest": manifest,
        "started_at": started,
        "finished_at": finished,
    }
