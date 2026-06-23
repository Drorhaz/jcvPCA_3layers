"""Tests for generic batch helpers."""

from pathlib import Path

from layer2_motive.batch import (
    STAGE02_LIMITATION_STATEMENT,
    discover_csv_inputs,
    safe_output_name,
    summarize_stage02_output,
    write_stage02_index,
)

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_motive_header.csv"
STAGE02_FIXTURE_OUT = (
    Path(__file__).parent.parent / "outputs" / "671_T1_P1_R1_Take_2026-01-06_03.57.12_PM_001"
)


def test_safe_output_name_removes_spaces_and_special_chars() -> None:
    path = Path("data/subject/T1 Take 2026-01-06 03.57.12 PM_001.csv")
    assert " " not in safe_output_name(path)
    assert ":" not in safe_output_name(path)


def test_discover_csv_inputs_from_explicit_list() -> None:
    found = discover_csv_inputs(inputs=[FIXTURE])
    assert found == [FIXTURE.resolve()]


def test_stage02_index_includes_limitation_statement(tmp_path: Path) -> None:
    if not STAGE02_FIXTURE_OUT.exists():
        return

    csv_path = Path(
        "data/671/671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001.csv"
    )
    row = summarize_stage02_output(csv_path, STAGE02_FIXTURE_OUT)
    assert row["explicit_limitations"] == STAGE02_LIMITATION_STATEMENT
    assert row["stage02_status"] == "PASS"

    index_path = tmp_path / "stage02_component_order_index"
    write_stage02_index([row], index_path)
    md = index_path.with_suffix(".md").read_text(encoding="utf-8")
    csv = index_path.with_suffix(".csv").read_text(encoding="utf-8")
    assert STAGE02_LIMITATION_STATEMENT in md
    assert STAGE02_LIMITATION_STATEMENT in csv
