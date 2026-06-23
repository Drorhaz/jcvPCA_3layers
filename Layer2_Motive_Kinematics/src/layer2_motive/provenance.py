"""Run provenance helpers for Layer 2 exports and downstream validation."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from layer2_motive.reporting import timestamp_utc


def try_get_git_commit(repo_root: Path | None = None) -> str | None:
    """Return current git HEAD hash if available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
            cwd=repo_root,
        )
        commit = result.stdout.strip()
        return commit or None
    except (OSError, subprocess.SubprocessError):
        return None


def get_package_version(package_name: str = "layer2-motive") -> str:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def hash_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_config(config_path: Path | None) -> str | None:
    if config_path is None or not config_path.is_file():
        return None
    return hash_file(config_path)


def file_size_bytes(path: Path) -> int | None:
    if not path.is_file():
        return None
    return path.stat().st_size


def resolve_input_file(run_dir: Path) -> str | None:
    """Best-effort input CSV path from Stage 03 frame/time summary."""
    summary = run_dir / "03_frame_time_validation" / "frame_time_summary.csv"
    if not summary.exists():
        return None
    import pandas as pd

    row = pd.read_csv(summary).iloc[0]
    value = row.get("input_file")
    return str(value) if value is not None else None


def resolve_config_path(run_dir: Path) -> Path | None:
    candidate = run_dir / "config_used.yaml"
    if candidate.exists():
        return candidate
    packaged = Path(__file__).resolve().parents[2] / "configs" / "default_layer2_config.yaml"
    if packaged.exists():
        return packaged
    return None


def pipeline_stage_versions(run_dir: Path) -> dict[str, str]:
    """Record which stage output folders exist (presence-only, not version numbers)."""
    stages = [
        "00_csv_structure",
        "01_joint_mapping",
        "02_component_order",
        "03_frame_time_validation",
        "04_quaternion_qc",
        "05_sign_continuity",
        "06_relative_quaternions",
        "07_rotation_vectors",
        "08_filtered_rotvecs",
    ]
    return {stage: "present" if (run_dir / stage).is_dir() else "missing" for stage in stages}


def build_run_provenance(
    *,
    run_dir: Path,
    source_stage08_parquet: Path | None = None,
    config_path: Path | None = None,
    input_file: str | None = None,
    export_created_at: str | None = None,
) -> dict[str, Any]:
    """Build provenance block for Layer 2 session export."""
    run_dir = run_dir.resolve()
    if input_file is None:
        input_file = resolve_input_file(run_dir)
    if config_path is None:
        config_path = resolve_config_path(run_dir)

    input_path = Path(input_file) if input_file else None
    if input_path is not None and not input_path.is_absolute():
        repo_root = Path(__file__).resolve().parents[2]
        candidate = repo_root / input_path
        if candidate.exists():
            input_path = candidate

    repo_root = run_dir.parent.parent if run_dir.parent.name == "outputs" else None
    git_commit = try_get_git_commit(repo_root)

    provenance: dict[str, Any] = {
        "package_name": "layer2-motive",
        "package_version": get_package_version(),
        "git_commit": git_commit,
        "config_path": str(config_path.resolve()) if config_path else None,
        "config_hash_sha256": hash_config(config_path) if config_path else None,
        "source_input_file": str(input_file) if input_file else None,
        "source_input_file_resolved": str(input_path.resolve()) if input_path and input_path.exists() else None,
        "source_input_file_size_bytes": file_size_bytes(input_path) if input_path and input_path.exists() else None,
        "source_input_file_sha256": hash_file(input_path) if input_path and input_path.exists() else None,
        "source_stage08_parquet": str(source_stage08_parquet.resolve()) if source_stage08_parquet else None,
        "run_dir": str(run_dir),
        "run_timestamp_utc": export_created_at or timestamp_utc(),
        "pipeline_stage_versions": pipeline_stage_versions(run_dir),
    }
    return provenance


def write_provenance_json(path: Path, provenance: dict[str, Any]) -> None:
    path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
