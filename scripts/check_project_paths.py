#!/usr/bin/env python3
"""Validate canonical project paths from config/paths.yaml.

Lightweight check only — does not run analysis pipelines.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from project_paths import (  # noqa: E402
    PathRequirement,
    load_project_paths,
)


def _status_label(requirement: PathRequirement, ok: bool) -> str:
    if ok:
        return "OK"
    if requirement == PathRequirement.REQUIRED:
        return "MISSING (required)"
    return "MISSING (optional)"


def main() -> int:
    paths = load_project_paths()

    print(f"Project root: {paths.project_root}")
    print(f"Config:       {paths.config_path}")
    if paths.used_minimal_yaml_parser:
        print("YAML loader:  minimal fallback (install PyYAML for full YAML support)")
    else:
        print("YAML loader:  PyYAML")
    print()

    section_order = [
        "raw_data",
        "data",
        "processed",
        "layer2",
        "layer2_5",
        "layer3",
        "poster",
        "results",
        "external_archive",
    ]

    entries_by_section: dict[str, list] = {s: [] for s in section_order}
    for key, entry in sorted(paths.entries.items()):
        section = key.split(".", 1)[0]
        entries_by_section.setdefault(section, []).append(entry)

    result = paths.validate()
    issue_by_key = {issue.dotted_key: issue for issue in result.issues}

    for section in section_order:
        section_entries = entries_by_section.get(section, [])
        if not section_entries:
            continue
        print(f"[{section}]")
        for entry in section_entries:
            if entry.is_glob:
                parent = entry.resolved.parent if entry.resolved else None
                pattern = entry.resolved.name if entry.resolved else entry.raw_value
                matches = list(parent.glob(pattern)) if parent and parent.is_dir() else []
                ok = bool(matches)
                status = _status_label(entry.requirement, ok)
                print(f"  {entry.dotted_key}")
                print(f"    raw:      {entry.raw_value}")
                print(f"    resolved: {entry.resolved}")
                print(f"    matches:  {len(matches)}")
                print(f"    status:   {status}")
            else:
                ok = entry.exists()
                status = _status_label(entry.requirement, ok)
                print(f"  {entry.dotted_key}")
                print(f"    raw:      {entry.raw_value}")
                print(f"    resolved: {entry.resolved}")
                print(f"    status:   {status}")
                if not ok and entry.dotted_key in issue_by_key:
                    print(f"    note:     {issue_by_key[entry.dotted_key].message}")
        print()

    print("Metadata:")
    print(f"  layer3.canonical_batch_id = {paths.layer3_canonical_batch_id!r}")
    cohort = paths.data.get("participants", {}).get("batch_cohort", [])
    print(f"  participants.batch_cohort = {cohort}")
    print()

    if result.errors:
        print("Required path errors:")
        for issue in result.errors:
            print(f"  - {issue.dotted_key}: {issue.resolved} ({issue.message})")
        print()

    if result.warnings:
        print("Optional path warnings:")
        for issue in result.warnings:
            print(f"  - {issue.dotted_key}: {issue.resolved} ({issue.message})")
        print()

    if result.ok:
        print("Path check passed (all required paths exist).")
        return 0

    print("Path check FAILED (one or more required paths missing).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
