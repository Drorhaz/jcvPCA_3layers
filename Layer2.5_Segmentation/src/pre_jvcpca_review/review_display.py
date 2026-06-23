"""Display review tables in notebook with structured missing-table warnings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from IPython.display import HTML, display

from pre_jvcpca_review.notebook_ui import display_summary_card, display_table
from pre_jvcpca_review.review_output import REVIEW_TABLE_FILES


@dataclass(frozen=True)
class ReviewTableSpec:
    filename: str
    title: str | None = None
    max_rows: int | None = None
    as_summary_card: bool = False


DEFAULT_REVIEW_TABLES: tuple[ReviewTableSpec, ...] = (
    ReviewTableSpec("window_decision_summary.csv", as_summary_card=True),
    ReviewTableSpec("mapping_logic_table.csv"),
    ReviewTableSpec("qc_evidence_summary_table.csv"),
    ReviewTableSpec("link_joint_review_table.csv"),
    ReviewTableSpec("qc_event_review_table.csv", max_rows=200),
    ReviewTableSpec("window_warnings.csv", max_rows=50),
)


def review_table_status(out_dir: Path) -> dict[str, bool]:
    out_dir = Path(out_dir)
    return {name: (out_dir / name).is_file() for name in REVIEW_TABLE_FILES}


def display_review_tables(
    out_dir: Path,
    *,
    specs: tuple[ReviewTableSpec, ...] = DEFAULT_REVIEW_TABLES,
    display_fn: Callable = display,
    display_table_fn: Callable = display_table,
    display_summary_fn: Callable = display_summary_card,
) -> list[str]:
    """Render review CSV tables; return warning messages for missing optional tables."""
    out_dir = Path(out_dir)
    warnings: list[str] = []
    if not out_dir.is_dir():
        display_fn(HTML(f"<p style='color:red'>Review output folder not found: <code>{out_dir}</code></p>"))
        return [f"Review output folder not found: {out_dir}"]

    summary_path = out_dir / "window_decision_summary.csv"
    if not summary_path.is_file():
        display_fn(
            HTML(
                "<p style='color:red'>Run full review first — "
                f"<code>{summary_path}</code> is missing.</p>"
            )
        )
        return [f"Missing required table: {summary_path.name}"]

    for spec in specs:
        path = out_dir / spec.filename
        title = spec.title or spec.filename
        if not path.is_file():
            msg = f"{spec.filename} not available in {out_dir}"
            warnings.append(msg)
            display_fn(HTML(f"<p style='color:#b8860b'><b>Warning:</b> {msg}</p>"))
            continue
        df = pd.read_csv(path)
        if spec.as_summary_card:
            display_summary_fn(df, title)
        else:
            display_table_fn(df, title, max_rows=spec.max_rows)

    display_fn(HTML(f"<p style='color:#666;font-size:11px;'>Review output dir: <code>{out_dir}</code></p>"))
    return warnings
