"""Locate session-specific Motive DataDescriptions CSV files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

_DATADESCRIPTIONS_SUFFIX = "_DataDescriptions.csv"


def normalize_take_key(name: str) -> str:
    """Normalize take / session filenames for fuzzy matching."""
    text = Path(name).name
    lower = text.lower()
    if lower.endswith("_datadescriptions.csv"):
        text = text[: -len(_DATADESCRIPTIONS_SUFFIX)]
    elif lower.endswith(".csv"):
        text = Path(text).stem
    text = text.replace("_Take_", " Take ")
    return re.sub(r"[_\s]+", " ", text).strip().lower()


def is_usable_datadescriptions(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def default_datadescriptions_dir(project_root: Path) -> Path:
    return Path(project_root) / "data_description"


def datadescriptions_search_roots(
    project_root: Path,
    session_row: pd.Series | dict[str, Any] | None = None,
) -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()

    def _add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        roots.append(path)

    _add(default_datadescriptions_dir(project_root))
    _add(Path(project_root) / "reevluate_project")

    if session_row is not None:
        for field in ("layer2_run_dir", "layer1_run_dir"):
            raw = session_row.get(field)
            if not raw or not str(raw).strip():
                continue
            run_path = Path(str(raw))
            _add(run_path)
            _add(run_path.parent)

    return roots


def index_datadescriptions(search_roots: list[Path]) -> dict[str, Path]:
    indexed: dict[str, Path] = {}
    for root in search_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*_DataDescriptions.csv")):
            if not is_usable_datadescriptions(path):
                continue
            indexed.setdefault(normalize_take_key(path.name), path)
    return indexed


def take_keys_from_session_row(session_row: pd.Series | dict[str, Any]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()

    def _add(raw: str | None) -> None:
        if not raw or not str(raw).strip():
            return
        key = normalize_take_key(str(raw))
        if key and key not in seen:
            seen.add(key)
            keys.append(key)

    _add(session_row.get("layer1_source_file"))
    layer2_run_dir = session_row.get("layer2_run_dir")
    if layer2_run_dir and str(layer2_run_dir).strip():
        _add(Path(str(layer2_run_dir)).name)
    return keys


def expected_datadescriptions_filenames(session_row: pd.Series | dict[str, Any]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    source = session_row.get("layer1_source_file")
    if source and str(source).strip():
        name = f"{Path(str(source)).stem}{_DATADESCRIPTIONS_SUFFIX}"
        if name not in seen:
            seen.add(name)
            names.append(name)
    layer2_run_dir = session_row.get("layer2_run_dir")
    if layer2_run_dir and str(layer2_run_dir).strip():
        name = f"{Path(str(layer2_run_dir)).name}{_DATADESCRIPTIONS_SUFFIX}"
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def find_datadescriptions_candidate(
    session_row: pd.Series | dict[str, Any] | None,
    *,
    search_roots: list[Path],
) -> Path | None:
    """Return a matching path even when the file is empty (for UI warnings)."""
    if session_row is None:
        return None
    for root in search_roots:
        if not root.is_dir():
            continue
        for name in expected_datadescriptions_filenames(session_row):
            path = root / name
            if path.is_file():
                return path
    session_id = str(session_row.get("session_id", "")).strip()
    if session_id:
        for root in search_roots:
            if not root.is_dir():
                continue
            matches = sorted(root.glob(f"{session_id}*_DataDescriptions.csv"))
            if len(matches) == 1:
                return matches[0]
    return None


def resolve_datadescriptions_path(
    session_row: pd.Series | dict[str, Any] | None,
    *,
    search_roots: list[Path],
    manual_path: Path | str | None = None,
) -> Path | None:
    """Return a non-empty DataDescriptions CSV for the session, if available."""
    if manual_path:
        path = Path(manual_path)
        if is_usable_datadescriptions(path):
            return path

    if session_row is None:
        return None

    indexed = index_datadescriptions(search_roots)
    for key in take_keys_from_session_row(session_row):
        hit = indexed.get(key)
        if hit is not None:
            return hit

    for root in search_roots:
        if not root.is_dir():
            continue
        for name in expected_datadescriptions_filenames(session_row):
            path = root / name
            if is_usable_datadescriptions(path):
                return path

    session_id = str(session_row.get("session_id", "")).strip().lower().replace("_", " ")
    if session_id:
        prefix_matches = [path for key, path in indexed.items() if key.startswith(session_id)]
        if len(prefix_matches) == 1:
            return prefix_matches[0]

    return None
