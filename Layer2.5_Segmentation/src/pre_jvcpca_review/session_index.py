"""Participant/session discovery and Layer 1 <-> Layer 2 pairing index.

Scans the Layer 1 and Layer 2 *output roots* (not hand-curated folders), detects
participants and sessions, and pairs matching Layer 1 / Layer 2 runs by the
canonical session key ``<subject>_T<t>_P<p>_R<r>``.

Default roots:
    Layer 1: Layer1_motive_qc/motive_qc/outputs
    Layer 2: Layer2_Motive_Kinematics/outputs

Real output layouts handled:
    Layer 1 run:  <root>/runs/<key>_<timestamp>/layer1_segmentation_notebook_manifest.json
                  + tables/qc_mask.csv, tables/layer1_marker_set.csv, ...
    Layer 2 sess: <root>/<key>_Take_.../08_filtered_rotvecs/filtered_relative_rotation_vectors.parquet
                  + 07_rotation_vectors/qc_link_manifest.csv, qc_session_manifest.csv
Normalized fixtures (single folder) are also handled.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# Repo root = .../Layer2.5_Segmentation/.. (two parents up from src/pre_jvcpca_review)
_PKG_ROOT = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _PKG_ROOT.parent

DEFAULT_LAYER1_ROOT = _PROJECT_ROOT / "Layer1_motive_qc" / "motive_qc" / "outputs"
DEFAULT_LAYER2_ROOT = _PROJECT_ROOT / "Layer2_Motive_Kinematics" / "outputs"

SESSION_KEY_RE = re.compile(r"(?P<subject>\d+)_T(?P<t>\d+)_P(?P<p>\d+)_R(?P<r>\d+)")

SESSION_INDEX_COLUMNS = [
    "participant_id",
    "timepoint",
    "part_id",
    "repetition_id",
    "session_id",
    "layer1_run_dir",
    "layer2_run_dir",
    "layer1_source_file",
    "layer2_source_file",
    "layer1_manifest_path",
    "layer2_provenance_path",
    "n_frames_layer1",
    "n_frames_layer2",
    "frame_start_layer1",
    "frame_end_layer1",
    "frame_start_layer2",
    "frame_end_layer2",
    "time_start_layer1",
    "time_end_layer1",
    "time_start_layer2",
    "time_end_layer2",
    "marker_set_id",
    "layer2_config_hash",
    "layer2_git_commit",
    "is_matched",
    "match_warning",
]

_UNKNOWN = "unknown"


@dataclass(frozen=True)
class SessionKey:
    subject: str
    timepoint: str
    part_id: str
    repetition_id: str

    @property
    def session_id(self) -> str:
        return f"{self.subject}_{self.timepoint}_{self.part_id}_{self.repetition_id}"


def parse_session_key(name: str) -> SessionKey | None:
    m = SESSION_KEY_RE.search(name)
    if not m:
        return None
    return SessionKey(
        subject=m.group("subject"),
        timepoint=f"T{m.group('t')}",
        part_id=f"P{m.group('p')}",
        repetition_id=f"R{m.group('r')}",
    )


def _newest(paths: list[Path]) -> Path:
    return max(paths, key=lambda p: p.stat().st_mtime)


def scan_layer1_runs(root: Path) -> dict[str, list[Path]]:
    """Map session_id -> list of candidate Layer 1 run dirs (newest-last not assumed)."""
    root = Path(root)
    found: dict[str, list[Path]] = {}
    if not root.is_dir():
        return found
    for manifest in root.rglob("layer1_segmentation_notebook_manifest.json"):
        run_dir = manifest.parent
        key = parse_session_key(run_dir.name) or parse_session_key(manifest.parent.name)
        if key is None:
            # Fall back to manifest contents
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                key = parse_session_key(str(data.get("run_key", "")))
            except (OSError, json.JSONDecodeError, ValueError):
                key = None
        if key is None:
            continue
        found.setdefault(key.session_id, []).append(run_dir)
    return found


def scan_layer2_sessions(root: Path) -> dict[str, list[Path]]:
    """Map session_id -> list of candidate Layer 2 session export dirs."""
    root = Path(root)
    found: dict[str, list[Path]] = {}
    if not root.is_dir():
        return found
    seen: set[Path] = set()
    for parquet in list(root.rglob("filtered_relative_rotation_vectors.parquet")) + list(
        root.rglob("layer2_session_filtered_rotvecs.parquet")
    ):
        # session dir is the parquet's dir, or its parent if inside 08_filtered_rotvecs
        sess_dir = parquet.parent
        if sess_dir.name == "08_filtered_rotvecs":
            sess_dir = sess_dir.parent
        if sess_dir in seen:
            continue
        if "archive" in {p.name for p in sess_dir.parents} or sess_dir.name == "archive":
            continue
        key = parse_session_key(sess_dir.name)
        if key is None:
            continue
        seen.add(sess_dir)
        found.setdefault(key.session_id, []).append(sess_dir)
    return found


def _read_layer1_meta(run_dir: Path) -> dict[str, object]:
    out: dict[str, object] = {
        "manifest_path": "",
        "source_file": _UNKNOWN,
        "n_frames": "",
        "fps": "",
        "marker_set_id": _UNKNOWN,
    }
    manifest = run_dir / "layer1_segmentation_notebook_manifest.json"
    if manifest.is_file():
        out["manifest_path"] = str(manifest)
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            out["source_file"] = Path(str(data.get("input_csv", _UNKNOWN))).name
            out["n_frames"] = int(data.get("n_frames", 0)) or ""
            out["fps"] = float(data.get("frame_rate_hz", 0)) or ""
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            pass
    for marker_set in (run_dir / "tables" / "layer1_marker_set.csv", run_dir / "layer1_marker_set.csv"):
        if marker_set.is_file():
            try:
                df = pd.read_csv(marker_set)
                if "marker_set_id_or_hash" in df.columns and len(df):
                    out["marker_set_id"] = str(df.iloc[0]["marker_set_id_or_hash"])
            except (OSError, ValueError):
                pass
            break
    return out


def _read_layer2_meta(sess_dir: Path) -> dict[str, object]:
    out: dict[str, object] = {
        "provenance_path": "",
        "source_file": _UNKNOWN,
        "n_frames": "",
        "fps": "",
        "config_hash": _UNKNOWN,
        "git_commit": _UNKNOWN,
    }
    for cand in (
        sess_dir / "layer2_session_summary.json",
        sess_dir / "07_rotation_vectors" / "qc_session_manifest.csv",
        sess_dir / "layer2_qc_session_manifest.csv",
    ):
        if not cand.is_file():
            continue
        out["provenance_path"] = str(cand)
        try:
            if cand.suffix == ".json":
                data = json.loads(cand.read_text(encoding="utf-8"))
                out["source_file"] = Path(str(data.get("source_stage08_parquet", ""))).name or str(
                    data.get("run_label", _UNKNOWN)
                )
                out["n_frames"] = int(data.get("frame_count", 0)) or ""
                out["fps"] = float(data.get("sampling_rate_hz", 0)) or ""
                out["git_commit"] = str(data.get("git_commit") or _UNKNOWN)
                out["config_hash"] = str(data.get("config_hash") or _UNKNOWN)
            else:
                df = pd.read_csv(cand)
                if len(df):
                    row = df.iloc[0]
                    out["source_file"] = str(row.get("run_label", _UNKNOWN))
                    if "frame_count" in df.columns:
                        out["n_frames"] = int(row["frame_count"])
                    if "sampling_rate_hz" in df.columns:
                        out["fps"] = float(row["sampling_rate_hz"])
                    out["git_commit"] = str(row.get("git_commit", _UNKNOWN) or _UNKNOWN)
                    out["config_hash"] = str(row.get("config_hash", _UNKNOWN) or _UNKNOWN)
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            pass
        break
    return out


def _frame_range(n_frames: object) -> tuple[object, object]:
    if isinstance(n_frames, int) and n_frames > 0:
        return 0, n_frames - 1
    return "", ""


def _time_range(n_frames: object, fps: object) -> tuple[object, object]:
    if isinstance(n_frames, int) and n_frames > 0 and isinstance(fps, float) and fps > 0:
        return 0.0, round((n_frames - 1) / fps, 4)
    return "", ""


def build_session_index(
    layer1_root: Path | None = None,
    layer2_root: Path | None = None,
) -> pd.DataFrame:
    """Build one row per discovered session, pairing Layer 1 and Layer 2 runs."""
    l1_root = Path(layer1_root) if layer1_root else DEFAULT_LAYER1_ROOT
    l2_root = Path(layer2_root) if layer2_root else DEFAULT_LAYER2_ROOT

    l1_runs = scan_layer1_runs(l1_root)
    l2_sessions = scan_layer2_sessions(l2_root)
    all_keys = sorted(set(l1_runs) | set(l2_sessions))

    rows: list[dict[str, object]] = []
    for session_id in all_keys:
        key = parse_session_key(session_id)
        warnings: list[str] = []

        l1_candidates = l1_runs.get(session_id, [])
        l2_candidates = l2_sessions.get(session_id, [])

        if len(l1_candidates) > 1:
            warnings.append(f"multiple_layer1_runs({len(l1_candidates)})")
        if len(l2_candidates) > 1:
            warnings.append(f"multiple_layer2_runs({len(l2_candidates)})")

        l1_dir = _newest(l1_candidates) if l1_candidates else None
        l2_dir = _newest(l2_candidates) if l2_candidates else None

        if l1_dir is None:
            warnings.append("missing_layer1_output")
        if l2_dir is None:
            warnings.append("missing_layer2_output")

        l1_meta = _read_layer1_meta(l1_dir) if l1_dir else {}
        l2_meta = _read_layer2_meta(l2_dir) if l2_dir else {}

        if l1_dir and not (l1_dir / "tables" / "qc_mask.csv").is_file() and not (
            l1_dir / "qc_mask.csv"
        ).is_file():
            warnings.append("missing_layer1_qc_mask")
        if l2_dir and not l2_meta.get("provenance_path"):
            warnings.append("missing_layer2_provenance")
        if l2_meta.get("git_commit", _UNKNOWN) == _UNKNOWN:
            warnings.append("layer2_git_commit_unknown")

        n1 = l1_meta.get("n_frames", "")
        n2 = l2_meta.get("n_frames", "")
        if isinstance(n1, int) and isinstance(n2, int) and n1 != n2:
            warnings.append(f"frame_count_mismatch(l1={n1},l2={n2})")

        is_matched = bool(l1_dir and l2_dir) and not any(
            w.startswith("frame_count_mismatch") for w in warnings
        )

        f1s, f1e = _frame_range(n1)
        f2s, f2e = _frame_range(n2)
        t1s, t1e = _time_range(n1, l1_meta.get("fps", ""))
        t2s, t2e = _time_range(n2, l2_meta.get("fps", ""))

        rows.append(
            {
                "participant_id": key.subject if key else _UNKNOWN,
                "timepoint": key.timepoint if key else _UNKNOWN,
                "part_id": key.part_id if key else _UNKNOWN,
                "repetition_id": key.repetition_id if key else _UNKNOWN,
                "session_id": session_id,
                "layer1_run_dir": str(l1_dir) if l1_dir else "",
                "layer2_run_dir": str(l2_dir) if l2_dir else "",
                "layer1_source_file": l1_meta.get("source_file", _UNKNOWN),
                "layer2_source_file": l2_meta.get("source_file", _UNKNOWN),
                "layer1_manifest_path": l1_meta.get("manifest_path", ""),
                "layer2_provenance_path": l2_meta.get("provenance_path", ""),
                "n_frames_layer1": n1,
                "n_frames_layer2": n2,
                "frame_start_layer1": f1s,
                "frame_end_layer1": f1e,
                "frame_start_layer2": f2s,
                "frame_end_layer2": f2e,
                "time_start_layer1": t1s,
                "time_end_layer1": t1e,
                "time_start_layer2": t2s,
                "time_end_layer2": t2e,
                "marker_set_id": l1_meta.get("marker_set_id", _UNKNOWN),
                "layer2_config_hash": l2_meta.get("config_hash", _UNKNOWN),
                "layer2_git_commit": l2_meta.get("git_commit", _UNKNOWN),
                "is_matched": is_matched,
                "match_warning": "; ".join(warnings),
            }
        )

    return pd.DataFrame(rows, columns=SESSION_INDEX_COLUMNS)


def participants(index: pd.DataFrame) -> list[str]:
    return sorted(index["participant_id"].astype(str).unique())


def sessions_for(index: pd.DataFrame, participant_id: str) -> pd.DataFrame:
    return index[index["participant_id"].astype(str) == str(participant_id)].copy()


def write_session_index(index: pd.DataFrame, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    index.to_csv(out_path, index=False)
    return out_path


def session_row(index: pd.DataFrame, session_id: str) -> pd.Series:
    matches = index[index["session_id"] == session_id]
    if matches.empty:
        raise KeyError(f"Session not in index: {session_id}")
    return matches.iloc[0]
