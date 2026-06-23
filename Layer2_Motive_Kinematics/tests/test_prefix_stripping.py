"""Tests for subject prefix stripping (Stage 01)."""

from layer2_motive.hierarchy import restore_subject_prefix, strip_subject_prefix


def test_colon_suffix_prefix_stripping() -> None:
    mapping = strip_subject_prefix("671:Chest", rule="colon_suffix")
    assert mapping.canonical_name == "Chest"
    assert mapping.subject_prefix == "671"
    assert mapping.prefix_rule == "colon_suffix"
    assert restore_subject_prefix(mapping) == "671:Chest"


def test_no_prefix_passthrough() -> None:
    mapping = strip_subject_prefix("Chest", rule="colon_suffix")
    assert mapping.canonical_name == "Chest"
    assert mapping.subject_prefix == ""
    assert restore_subject_prefix(mapping) == "Chest"
