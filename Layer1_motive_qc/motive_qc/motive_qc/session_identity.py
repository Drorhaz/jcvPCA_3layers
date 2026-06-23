"""Parse participant / session identity fields from config and filenames."""

from __future__ import annotations

import re
from typing import Any

SESSION_COMPONENTS_RE = re.compile(
    r"^(?P<timepoint>T\d+)_(?P<part_id>P\d+)_(?P<repetition_id>R\d+)$",
    re.IGNORECASE,
)


def parse_session_components(session_id: str) -> dict[str, str]:
    """Return timepoint, part_id, repetition_id parsed from e.g. ``T3_P1_R2``."""
    match = SESSION_COMPONENTS_RE.match(str(session_id).strip())
    if not match:
        return {"timepoint": "", "part_id": "", "repetition_id": ""}
    return {
        "timepoint": match.group("timepoint").upper(),
        "part_id": match.group("part_id").upper(),
        "repetition_id": match.group("repetition_id").upper(),
    }


def session_identity_from_metadata(metadata: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
    """Build identity fields for contract outputs."""
    project = config.get("project", {})
    participant_id = str(project.get("subject_id") or metadata.get("subject_id") or "")
    session_id = str(project.get("session_id") or metadata.get("session_id") or "")
    components = parse_session_components(session_id)
    source_file = str(metadata.get("file_name") or metadata.get("input_file") or "")
    return {
        "participant_id": participant_id,
        "session_id": session_id,
        "timepoint": components["timepoint"],
        "part_id": components["part_id"],
        "repetition_id": components["repetition_id"],
        "source_file": source_file,
    }
