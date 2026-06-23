#!/usr/bin/env python3
"""Quick inspection exports for window_jvcpca_matrix.parquet before JvcPCA modeling."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    PROJECT_ROOT / "outputs/pre_jvcpca_review/session_window/window_jvcpca_matrix.parquet"
)
DEFAULT_XLSX = (
    PROJECT_ROOT / "outputs/pre_jvcpca_review/session_window/window_jvcpca_matrix_preview.xlsx"
)
DEFAULT_SUMMARY = (
    PROJECT_ROOT / "outputs/pre_jvcpca_review/session_window/window_jvcpca_matrix_summary.md"
)

METADATA_QC_KEYWORDS = (
    "subject",
    "session",
    "task",
    "rep",
    "window",
    "frame",
    "time",
    "mask",
    "qc",
    "flag",
    "artifact",
)


def _is_metadata_qc_column(name: str) -> bool:
    lower = name.lower()
    return any(keyword in lower for keyword in METADATA_QC_KEYWORDS)


def _count_infinite(series: pd.Series) -> int:
    if not pd.api.types.is_numeric_dtype(series):
        return 0
    return int(np.isinf(series.to_numpy()).sum())


def _constant_numeric_columns(df: pd.DataFrame) -> list[str]:
    constant: list[str] = []
    for col in df.select_dtypes(include="number").columns:
        if df[col].nunique(dropna=True) <= 1:
            constant.append(col)
    return constant


def _columns_with_missing_values(df: pd.DataFrame) -> list[tuple[str, int]]:
    missing = df.isna().sum()
    return [(col, int(count)) for col, count in missing.items() if count > 0]


def build_summary_markdown(df: pd.DataFrame) -> str:
    n_rows, n_cols = df.shape
    columns = list(df.columns)
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    total_missing = int(df.isna().sum().sum())
    cols_with_missing = _columns_with_missing_values(df)

    numeric_cols = df.select_dtypes(include="number").columns
    total_infinite = sum(_count_infinite(df[col]) for col in numeric_cols)
    constant_numeric = _constant_numeric_columns(df)

    metadata_qc = [col for col in columns if _is_metadata_qc_column(col)]
    metadata_qc_set = set(metadata_qc)
    feature_cols = [
        col
        for col in columns
        if col not in metadata_qc_set and pd.api.types.is_numeric_dtype(df[col])
    ]

    lines = [
        "# window_jvcpca_matrix summary",
        "",
        f"- **Rows:** {n_rows}",
        f"- **Columns:** {n_cols}",
        "",
        "## Column names",
        "",
    ]
    lines.extend(f"- `{col}`" for col in columns)

    lines.extend(["", "## Data types", ""])
    lines.extend(f"- `{col}`: `{dtypes[col]}`" for col in columns)

    lines.extend(
        [
            "",
            "## Missing values",
            "",
            f"- **Total missing values:** {total_missing}",
            "",
        ]
    )
    if cols_with_missing:
        lines.extend(["### Columns with missing values", ""])
        lines.extend(f"- `{col}`: {count}" for col, count in cols_with_missing)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Infinite values (numeric columns)",
            "",
            f"- **Total infinite values:** {total_infinite}",
            "",
            "## Constant numeric columns",
            "",
        ]
    )
    if constant_numeric:
        lines.extend(f"- `{col}`" for col in constant_numeric)
    else:
        lines.append("- None")

    lines.extend(["", "## Likely metadata/QC columns", ""])
    if metadata_qc:
        lines.extend(f"- `{col}`" for col in metadata_qc)
    else:
        lines.append("- None")

    lines.extend(["", "## Likely numeric feature columns", ""])
    if feature_cols:
        lines.extend(f"- `{col}`" for col in feature_cols)
    else:
        lines.append("- None")

    lines.append("")
    return "\n".join(lines)


def export_excel(df: pd.DataFrame, path: Path) -> None:
    try:
        import openpyxl  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Excel export requires openpyxl. Install with: pip install openpyxl"
        ) from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False, engine="openpyxl")


def main() -> None:
    input_path = DEFAULT_INPUT
    xlsx_path = DEFAULT_XLSX
    summary_path = DEFAULT_SUMMARY

    if not input_path.is_file():
        raise SystemExit(f"Input parquet not found: {input_path}")

    df = pd.read_parquet(input_path)

    export_excel(df, xlsx_path)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(build_summary_markdown(df), encoding="utf-8")

    print(f"Saved Excel preview: {xlsx_path}")
    print(f"Saved summary: {summary_path}")


if __name__ == "__main__":
    main()
