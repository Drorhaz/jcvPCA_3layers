"""Stage 5 verification gate with optional G6 disk persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise ImportError("verification_gate requires PyYAML.") from exc


@dataclass
class VerificationState:
    verified_segment_ids: set[str] = field(default_factory=set)
    signed_off: bool = False
    notes: str = ""
    science_hash: str = ""
    signed_off_at: str = ""


def stage6_unlocked(
    state: VerificationState | None,
    *,
    disk_state: VerificationState | None = None,
) -> bool:
    for candidate in (state, disk_state):
        if candidate and candidate.signed_off and candidate.verified_segment_ids:
            return True
    return False


def toggle_segment(state: VerificationState, segment_id: str, *, verified: bool) -> None:
    if verified:
        state.verified_segment_ids.add(segment_id)
    else:
        state.verified_segment_ids.discard(segment_id)


def sign_off(state: VerificationState, *, notes: str = "", science_hash: str = "") -> None:
    if not state.verified_segment_ids:
        raise ValueError("Select at least one verified segment before sign-off.")
    state.signed_off = True
    state.notes = notes
    state.science_hash = science_hash
    state.signed_off_at = datetime.now(timezone.utc).isoformat()


def reset_sign_off(state: VerificationState) -> None:
    state.signed_off = False
    state.notes = ""
    state.science_hash = ""
    state.signed_off_at = ""


def verification_state_to_dict(state: VerificationState) -> dict[str, Any]:
    return {
        "version": 1,
        "signed_off": state.signed_off,
        "notes": state.notes,
        "science_hash": state.science_hash,
        "signed_off_at": state.signed_off_at or datetime.now(timezone.utc).isoformat(),
        "verified_segment_ids": sorted(state.verified_segment_ids),
    }


def verification_state_from_dict(data: dict[str, Any]) -> VerificationState:
    return VerificationState(
        verified_segment_ids=set(data.get("verified_segment_ids") or []),
        signed_off=bool(data.get("signed_off")),
        notes=str(data.get("notes") or ""),
        science_hash=str(data.get("science_hash") or ""),
        signed_off_at=str(data.get("signed_off_at") or ""),
    )


def save_verification_snapshot(project_root: Path, state: VerificationState) -> Path:
    from g6_execution import verification_snapshot_path

    path = verification_snapshot_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = verification_state_to_dict(state)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def load_verification_snapshot(project_root: Path) -> VerificationState | None:
    from g6_execution import verification_snapshot_path

    path = verification_snapshot_path(project_root)
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return None
    return verification_state_from_dict(data)


def clear_verification_snapshot(project_root: Path) -> None:
    from g6_execution import verification_snapshot_path

    path = verification_snapshot_path(project_root)
    if path.is_file():
        path.unlink()
