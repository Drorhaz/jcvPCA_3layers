"""Parse exercise segmentation spreadsheets (xlsx/csv) into frame windows."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

GROUP4_EXERCISE_IDS = (9, 10, 11, 12, 13)
GROUP4_LABEL = "Group 4 — Curvilinear exploration (exercises 9–13)"

SHEET_SESSION_RE = re.compile(
    r"(?P<subject>\d+)\s*[-–]\s*T(?P<t>\d+)P(?P<p>\d+)R(?P<r>\d+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExerciseSegment:
    exercise_id: int
    exercise_name: str
    start_frame: int
    end_frame: int
    session_id: str
    sheet_name: str


def sheet_name_to_session_id(sheet_name: str) -> str | None:
    match = SHEET_SESSION_RE.search(str(sheet_name).strip())
    if not match:
        return None
    return (
        f"{match.group('subject')}_T{match.group('t')}_"
        f"P{match.group('p')}_R{match.group('r')}"
    )


def make_window_label(session_id: str, start_frame: int, end_frame: int, *, tag: str = "") -> str:
    middle = f"_{tag}" if tag else ""
    return f"{session_id}{middle}_s{int(start_frame)}_e{int(end_frame)}"


def _coerce_frame(value: object) -> int | None:
    if pd.isna(value):
        return None
    if isinstance(value, str):
        text = value.strip().lower()
        if not text or text in {"blank", "na", "n/a", "none", "-"}:
            return None
    try:
        frame = int(float(value))
    except (TypeError, ValueError):
        return None
    return frame if frame >= 0 else None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {str(col).strip(): col for col in df.columns}
    out = df.rename(columns={orig: str(name).strip() for name, orig in renamed.items()})
    return out


def _pick_frame_columns(df: pd.DataFrame) -> tuple[str, str]:
    columns = list(df.columns)
    lower_map = {str(col).lower(): col for col in columns}

    start_key = None
    for candidate in ("start_frame", "start frame"):
        if candidate in lower_map:
            start_key = lower_map[candidate]
            break
    if start_key is None:
        for col in columns:
            if str(col).lower().startswith("start_frame"):
                start_key = col
                break

    end_key = None
    for candidate in ("end_frame", "end frame"):
        if candidate in lower_map:
            end_key = lower_map[candidate]
            break
    if end_key is None:
        for candidate in ("end_frame_exclusive", "end frame exclusive"):
            if candidate in lower_map:
                end_key = lower_map[candidate]
                break
    if end_key is None:
        for col in columns:
            lower = str(col).lower()
            if lower.startswith("end_frame"):
                end_key = col
                break

    if start_key is None or end_key is None:
        raise ValueError(
            "Could not find start/end frame columns. "
            f"Available columns: {', '.join(str(c) for c in columns)}"
        )
    return str(start_key), str(end_key)


def _pick_exercise_columns(df: pd.DataFrame) -> tuple[str, str]:
    columns = list(df.columns)
    lower_map = {str(col).lower(): col for col in columns}
    id_key = lower_map.get("exercise_id")
    name_key = lower_map.get("exercise_name")
    if id_key is None or name_key is None:
        raise ValueError("Sheet must include exercise_id and exercise_name columns.")
    return str(id_key), str(name_key)


def parse_exercise_sheet(
    df: pd.DataFrame,
    *,
    sheet_name: str,
    session_id: str,
) -> list[ExerciseSegment]:
    df = _normalize_columns(df)
    id_col, name_col = _pick_exercise_columns(df)
    start_col, end_col = _pick_frame_columns(df)

    segments: list[ExerciseSegment] = []
    for _, row in df.iterrows():
        ex_id_raw = row.get(id_col)
        if pd.isna(ex_id_raw):
            continue
        try:
            exercise_id = int(ex_id_raw)
        except (TypeError, ValueError):
            continue
        start_raw = row.get(start_col)
        end_raw = row.get(end_col)
        if pd.isna(start_raw) or pd.isna(end_raw):
            continue
        start_frame = _coerce_frame(start_raw)
        end_frame = _coerce_frame(end_raw)
        if start_frame is None or end_frame is None:
            continue
        if end_frame < start_frame:
            continue
        name = str(row.get(name_col, "")).strip() or f"exercise_{exercise_id}"
        segments.append(
            ExerciseSegment(
                exercise_id=exercise_id,
                exercise_name=name,
                start_frame=start_frame,
                end_frame=end_frame,
                session_id=session_id,
                sheet_name=sheet_name,
            )
        )
    return segments


def load_exercise_segments(path: Path | str) -> dict[str, list[ExerciseSegment]]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Segmentation file not found: {path}")

    by_session: dict[str, list[ExerciseSegment]] = {}
    if path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        workbook = pd.ExcelFile(path)
        for sheet_name in workbook.sheet_names:
            session_id = sheet_name_to_session_id(sheet_name)
            if session_id is None:
                continue
            df = pd.read_excel(path, sheet_name=sheet_name)
            by_session[session_id] = parse_exercise_sheet(
                df,
                sheet_name=sheet_name,
                session_id=session_id,
            )
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        session_col = None
        for candidate in ("session_id", "session"):
            if candidate in df.columns:
                session_col = candidate
                break
        if session_col is None:
            raise ValueError("CSV must include a session_id column when using a single sheet.")
        for session_id, group in df.groupby(session_col):
            by_session[str(session_id)] = parse_exercise_sheet(
                group,
                sheet_name=str(session_id),
                session_id=str(session_id),
            )
    else:
        raise ValueError(f"Unsupported segmentation file type: {path.suffix}")

    if not by_session:
        raise ValueError(f"No session sheets parsed from {path}")
    return by_session


def load_exercise_segments_bytes(data: bytes, filename: str) -> dict[str, list[ExerciseSegment]]:
    suffix = Path(filename).suffix.lower()
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        workbook = pd.ExcelFile(io.BytesIO(data))
        by_session: dict[str, list[ExerciseSegment]] = {}
        for sheet_name in workbook.sheet_names:
            session_id = sheet_name_to_session_id(sheet_name)
            if session_id is None:
                continue
            df = pd.read_excel(io.BytesIO(data), sheet_name=sheet_name)
            by_session[session_id] = parse_exercise_sheet(
                df,
                sheet_name=sheet_name,
                session_id=session_id,
            )
        if not by_session:
            raise ValueError("Uploaded workbook has no recognizable session sheets.")
        return by_session
    if suffix == ".csv":
        return load_exercise_segments_from_csv_bytes(data)
    raise ValueError(f"Unsupported uploaded file type: {suffix}")


def load_exercise_segments_from_csv_bytes(data: bytes) -> dict[str, list[ExerciseSegment]]:
    df = pd.read_csv(io.BytesIO(data))
    session_col = None
    for candidate in ("session_id", "session"):
        if candidate in df.columns:
            session_col = candidate
            break
    if session_col is None:
        raise ValueError("CSV must include session_id when using a single sheet.")
    by_session: dict[str, list[ExerciseSegment]] = {}
    for session_id, group in df.groupby(session_col):
        by_session[str(session_id)] = parse_exercise_sheet(
            group,
            sheet_name=str(session_id),
            session_id=str(session_id),
        )
    return by_session


def group4_window(segments: list[ExerciseSegment]) -> tuple[int, int] | None:
    selected = [seg for seg in segments if seg.exercise_id in GROUP4_EXERCISE_IDS]
    if not selected:
        return None
    return min(seg.start_frame for seg in selected), max(seg.end_frame for seg in selected)


def exercise_choice_label(segment: ExerciseSegment) -> str:
    return (
        f"Ex {segment.exercise_id:02d}: {segment.exercise_name} "
        f"[{segment.start_frame}–{segment.end_frame}]"
    )
