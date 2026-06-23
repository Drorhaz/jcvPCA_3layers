"""Report writers and markdown helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def timestamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def render_stage_report(
    *,
    stage_name: str,
    input_files: list[str],
    detected: list[str],
    assumptions: list[str],
    outputs: list[str],
    warnings: list[str],
    errors: list[str],
    validation_status: str,
    next_action: str,
) -> str:
    lines = [
        f"# {stage_name}",
        "",
        f"Generated: {timestamp_utc()}",
        "",
        "## Input files used",
        "",
    ]
    lines.extend(f"- `{path}`" for path in input_files)
    lines.extend(["", "## What was detected", ""])
    lines.extend(f"- {item}" for item in detected)
    lines.extend(["", "## Assumptions", ""])
    lines.extend(f"- {item}" for item in assumptions)
    lines.extend(["", "## Outputs written", ""])
    lines.extend(f"- `{path}`" for path in outputs)
    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(f"- {item}" for item in warnings)
    else:
        lines.append("- None")
    lines.extend(["", "## Errors", ""])
    if errors:
        lines.extend(f"- {item}" for item in errors)
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Validation status",
            "",
            validation_status,
            "",
            "## Next recommended action",
            "",
            next_action,
            "",
        ]
    )
    return "\n".join(lines)


def append_assumptions_log(output_dir: Path, assumptions: list[str]) -> None:
    path = output_dir / "assumptions_log.md"
    header = "# Layer 2 assumptions log\n\n"
    if not path.exists():
        path.write_text(header, encoding="utf-8")
    existing = path.read_text(encoding="utf-8")
    stamp = timestamp_utc()
    additions = "".join(f"\n- [{stamp}] {item}" for item in assumptions)
    path.write_text(existing.rstrip() + additions + "\n", encoding="utf-8")
