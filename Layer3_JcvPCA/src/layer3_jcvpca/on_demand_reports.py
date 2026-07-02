"""On-demand / policy-gated heavy Layer 3 report generation."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTPUT_POLICY_ALWAYS = "always"
OUTPUT_POLICY_ON_DEMAND = "on_demand"
OUTPUT_POLICY_NEVER = "never"
VALID_OUTPUT_POLICIES = frozenset({OUTPUT_POLICY_ALWAYS, OUTPUT_POLICY_ON_DEMAND, OUTPUT_POLICY_NEVER})


def normalize_output_policy(value: str | None, *, default: str = OUTPUT_POLICY_ON_DEMAND) -> str:
    text = str(value or default).strip().lower()
    if text not in VALID_OUTPUT_POLICIES:
        return default
    return text


def _layer3_python(project_root: Path) -> Path:
    candidate = project_root / "Layer3_JcvPCA" / ".venv" / "bin" / "python"
    if candidate.is_file():
        return candidate
    return Path(sys.executable)


def _run_script(
    project_root: Path,
    script_name: str,
    argv: list[str],
) -> dict[str, Any]:
    script = project_root / "Layer3_JcvPCA" / "scripts" / script_name
    cmd = [str(_layer3_python(project_root)), str(script), *argv]
    proc = subprocess.run(
        cmd,
        cwd=project_root / "Layer3_JcvPCA" / "scripts",
        capture_output=True,
        text=True,
    )
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-4000:],
    }


def _should_run(policy: str, *, force: bool) -> bool:
    if force:
        return policy != OUTPUT_POLICY_NEVER
    return policy == OUTPUT_POLICY_ALWAYS


def generate_on_demand_reports(
    batch_root: Path,
    *,
    generate_full_numeric_reports: str = OUTPUT_POLICY_ON_DEMAND,
    generate_poster_package: str = OUTPUT_POLICY_ON_DEMAND,
    project_root: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Apply output policies and optionally generate heavy audit/poster artifacts."""
    batch_root = batch_root.resolve()
    repo_root = project_root.resolve() if project_root else None
    if repo_root is None:
        for candidate in (batch_root, *batch_root.parents):
            if (candidate / "config" / "analysis_params.yaml").is_file():
                repo_root = candidate.resolve()
                break
    if repo_root is None:
        raise FileNotFoundError("Could not locate repository root for on-demand report generation.")
    numeric_policy = normalize_output_policy(generate_full_numeric_reports)
    poster_policy = normalize_output_policy(generate_poster_package)

    manifest: dict[str, Any] = {
        "batch_root": str(batch_root),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "policies": {
            "generate_full_numeric_reports": numeric_policy,
            "generate_poster_package": poster_policy,
            "force": force,
        },
        "artifacts": {},
    }

    numeric_out = batch_root / "Gaga_JcvPCA_MASTER_full_numeric_report.md"
    poster_out = batch_root / "poster_ready_evidence_package"

    if _should_run(numeric_policy, force=force):
        manifest["artifacts"]["full_numeric"] = _run_script(
            repo_root,
            "generate_master_full_numeric_report.py",
            ["--batch-dir", str(batch_root)],
        )
        manifest["artifacts"]["full_numeric"]["output_path"] = str(numeric_out)
        manifest["artifacts"]["full_numeric"]["status"] = (
            "generated" if numeric_out.is_file() and manifest["artifacts"]["full_numeric"]["returncode"] == 0 else "failed"
        )
    else:
        manifest["artifacts"]["full_numeric"] = {
            "status": "skipped",
            "reason": f"policy={numeric_policy}",
            "output_path": str(numeric_out),
            "command": f"{_layer3_python(repo_root)} generate_master_full_numeric_report.py --batch-dir {batch_root}",
        }

    if _should_run(poster_policy, force=force):
        manifest["artifacts"]["poster_package"] = _run_script(
            repo_root,
            "generate_poster_ready_evidence_package.py",
            ["--batch-dir", str(batch_root), "--evidence-dir", str(poster_out)],
        )
        manifest["artifacts"]["poster_package"]["output_path"] = str(poster_out)
        manifest["artifacts"]["poster_package"]["status"] = (
            "generated"
            if poster_out.is_dir() and manifest["artifacts"]["poster_package"]["returncode"] == 0
            else "failed"
        )
    else:
        manifest["artifacts"]["poster_package"] = {
            "status": "skipped",
            "reason": f"policy={poster_policy}",
            "output_path": str(poster_out),
            "command": (
                f"{_layer3_python(repo_root)} generate_poster_ready_evidence_package.py "
                f"--batch-dir {batch_root} --evidence-dir {poster_out}"
            ),
        }

    manifest_path = batch_root / "on_demand_reports_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest
