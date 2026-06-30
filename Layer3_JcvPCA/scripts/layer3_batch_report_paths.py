"""Shared path configuration for read-only Layer 3 batch report scripts."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from project_paths import load_project_paths  # noqa: E402


@dataclass(frozen=True)
class BatchReportPaths:
    root: Path
    batch_id: str
    batch_display: str
    config_path: Path


def display_repo_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def resolve_batch_report_paths(
    *,
    config_path: Path | None = None,
    batch_dir: Path | None = None,
) -> BatchReportPaths:
    paths = load_project_paths(config_path=config_path)
    root = (batch_dir or paths.layer3_canonical_batch).resolve()
    if not root.is_dir():
        raise FileNotFoundError(
            f"Required canonical Layer 3 batch missing: {root}\n"
            f"Config: {paths.config_path}"
        )
    return BatchReportPaths(
        root=root,
        batch_id=paths.layer3_canonical_batch_id,
        batch_display=display_repo_path(root, paths.project_root),
        config_path=paths.config_path,
    )


def resolve_layer25_root(*, config_path: Path | None = None) -> Path:
    paths = load_project_paths(config_path=config_path)
    root = paths.layer2_5_pre_jvcpca_review.resolve()
    if not root.is_dir():
        raise FileNotFoundError(
            f"Required Layer 2.5 pre_jvcpca_review root missing: {root}\n"
            f"Config: {paths.config_path}"
        )
    return root


def resolve_default_batch_dir(*, config_path: Path | None = None) -> Path:
    """Return canonical batch directory for analysis scripts."""
    return resolve_batch_report_paths(config_path=config_path).root


def parse_batch_report_cli(description: str, argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config/paths.yaml (default: auto-detect project root).",
    )
    parser.add_argument(
        "--batch-dir",
        type=Path,
        default=None,
        help="Override Layer 3 batch directory (default: layer3.canonical_batch).",
    )
    parser.add_argument(
        "--validate-paths",
        action="store_true",
        help="Check batch root and required inputs exist; do not write report.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned output path only; do not write report.",
    )
    return parser.parse_args(argv)


def missing_required_files(root: Path, required: list[str]) -> list[str]:
    return [name for name in required if not (root / name).is_file()]


def run_path_preflight(
    args: argparse.Namespace,
    *,
    root: Path,
    out: Path,
    required: list[str] | None = None,
    input_root: Path | None = None,
) -> int | None:
    """Return an exit code when handling validate/dry-run; otherwise None."""
    if not (args.validate_paths or args.dry_run):
        return None

    check_root = input_root or root
    missing = missing_required_files(check_root, required or [])
    print(f"Batch root: {root}")
    if input_root is not None and input_root != root:
        print(f"Input root: {input_root}")
    print(f"Output:     {out}")
    if required is not None:
        print(f"Required inputs: {len(required)}; missing: {len(missing)}")
        for name in missing[:15]:
            print(f"  - missing: {name}")
        if len(missing) > 15:
            print(f"  ... and {len(missing) - 15} more")

    if args.validate_paths:
        if missing:
            print("Path/input check FAILED.")
            return 1
        print("Path/input check passed.")
        return 0

    print("Dry run only — no report written.")
    return 0
