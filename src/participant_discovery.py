"""Discover participant IDs from on-disk data (not hardcoded cohort lists)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from project_paths import ProjectPaths

PARTICIPANT_ID_RE = re.compile(r"^\d+$")
SESSION_PARTICIPANT_RE = re.compile(
    r"(?P<participant>\d+)_T(?P<t>\d+)_P(?P<p>\d+)_R(?P<r>\d+)"
)
SEGMENTATION_XLSX_RE = re.compile(
    r"^(?P<participant>\d+)_ex_segmentatios_frames\.xlsx$",
    re.IGNORECASE,
)


def is_valid_participant_id(participant_id: str) -> bool:
    return bool(PARTICIPANT_ID_RE.fullmatch(str(participant_id).strip()))


def normalize_participant_id(value: object) -> str | None:
    text = str(value or "").strip()
    if is_valid_participant_id(text):
        return text
    return None


@dataclass(frozen=True)
class ParticipantDiscovery:
    """Merged participant inventory with per-source attribution."""

    participant_ids: tuple[str, ...]
    by_source: dict[str, tuple[str, ...]] = field(default_factory=dict)
    default_participant: str = ""
    config_cohort: tuple[str, ...] = ()
    registered_not_discovered: tuple[str, ...] = ()
    discovered_not_registered: tuple[str, ...] = ()

    @property
    def count(self) -> int:
        return len(self.participant_ids)

    def has(self, participant_id: str) -> bool:
        return str(participant_id).strip() in self.participant_ids

    def sources_for(self, participant_id: str) -> list[str]:
        pid = str(participant_id).strip()
        return [source for source, ids in self.by_source.items() if pid in ids]


def _sorted_unique(ids: set[str]) -> tuple[str, ...]:
    return tuple(sorted(ids, key=lambda x: (len(x), x)))


def participants_from_session_rows(rows: list[dict[str, Any]]) -> set[str]:
    found: set[str] = set()
    for row in rows:
        pid = normalize_participant_id(row.get("participant_id"))
        if pid:
            found.add(pid)
            continue
        sid = str(row.get("session_id", "")).strip()
        match = SESSION_PARTICIPANT_RE.fullmatch(sid)
        if match:
            found.add(match.group("participant"))
    return found


def participants_from_manifest_rows(rows: list[dict[str, Any]]) -> set[str]:
    found: set[str] = set()
    for row in rows:
        pid = normalize_participant_id(row.get("participant_id"))
        if pid:
            found.add(pid)
    return found


def scan_raw_layer2_participants(raw_layer2_root: Path) -> set[str]:
    if not raw_layer2_root.is_dir():
        return set()
    found: set[str] = set()
    for child in raw_layer2_root.iterdir():
        if child.is_dir():
            pid = normalize_participant_id(child.name)
            if pid:
                found.add(pid)
    return found


def scan_segmentation_workbooks(segmentation_dir: Path) -> set[str]:
    if not segmentation_dir.is_dir():
        return set()
    found: set[str] = set()
    for path in segmentation_dir.glob("*_ex_segmentatios_frames.xlsx"):
        match = SEGMENTATION_XLSX_RE.match(path.name)
        if match:
            found.add(match.group("participant"))
    return found


def config_batch_cohort(paths: ProjectPaths) -> tuple[str, ...]:
    cohort = paths.data.get("participants", {}).get("batch_cohort", [])
    if not isinstance(cohort, list):
        return ()
    out: list[str] = []
    for item in cohort:
        pid = normalize_participant_id(item)
        if pid:
            out.append(pid)
    return tuple(sorted(set(out)))


def resolve_default_participant(
    participant_ids: tuple[str, ...],
    *,
    paths: ProjectPaths,
    gui_default: str | None = None,
) -> str:
    if not participant_ids:
        return ""
    flagship = normalize_participant_id(paths.data.get("participants", {}).get("flagship"))
    if flagship and flagship in participant_ids:
        return flagship
    if gui_default and gui_default in participant_ids:
        return gui_default
    return participant_ids[0]


def discover_participants(
    paths: ProjectPaths,
    *,
    session_rows: list[dict[str, Any]] | None = None,
    l25_rows: list[dict[str, Any]] | None = None,
    gui_default_participant: str | None = None,
) -> ParticipantDiscovery:
    """Merge participant IDs from session index, raw data, segmentation, manifest, and config."""
    session_rows = session_rows or []
    l25_rows = l25_rows or []

    by_source: dict[str, set[str]] = {
        "session_index": participants_from_session_rows(session_rows),
        "raw_layer2": scan_raw_layer2_participants(paths.data_raw_layer2),
        "segmentation_xlsx": scan_segmentation_workbooks(paths.get("layer2_5.segmentation_xlsx")),
        "l25_manifest": participants_from_manifest_rows(l25_rows),
    }
    registered = set(config_batch_cohort(paths))
    by_source["config_cohort"] = set(registered)

    merged: set[str] = set()
    for ids in by_source.values():
        merged.update(ids)

    participant_ids = _sorted_unique(merged)
    registered_tuple = _sorted_unique(registered)
    discovered_set = set(participant_ids)

    return ParticipantDiscovery(
        participant_ids=participant_ids,
        by_source={key: _sorted_unique(ids) for key, ids in by_source.items() if ids},
        default_participant=resolve_default_participant(
            participant_ids,
            paths=paths,
            gui_default=gui_default_participant,
        ),
        config_cohort=registered_tuple,
        registered_not_discovered=_sorted_unique(registered - discovered_set),
        discovered_not_registered=_sorted_unique(discovered_set - registered),
    )


def discovery_table_rows(discovery: ParticipantDiscovery) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pid in discovery.participant_ids:
        rows.append(
            {
                "participant_id": pid,
                "sources": ", ".join(discovery.sources_for(pid)),
                "segmentation_xlsx": "yes"
                if pid in discovery.by_source.get("segmentation_xlsx", ())
                else "no",
                "raw_layer2_dir": "yes"
                if pid in discovery.by_source.get("raw_layer2", ())
                else "no",
                "session_index": "yes"
                if pid in discovery.by_source.get("session_index", ())
                else "no",
                "in_config_cohort": "yes" if pid in discovery.config_cohort else "no",
                "default": "yes" if pid == discovery.default_participant else "",
            }
        )
    return rows
