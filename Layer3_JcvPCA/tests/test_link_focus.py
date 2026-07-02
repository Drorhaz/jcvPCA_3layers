"""Tests for request link_focus application in the Layer 3 batch runner."""

from __future__ import annotations

import pandas as pd
import pytest

from layer3_jcvpca.comparable_links import (
    COMPARABLE_LINKS_COLUMNS,
    EXCLUDED_LINKS_COLUMNS,
    REASON_MISSING_LINK,
    REASON_ZERO_VARIANCE,
    ComparableLinksReport,
)
from layer3_jcvpca.link_focus import (
    FILTER_STAGE_PCA_INPUT,
    LinkFocusMode,
    LinkFocusSpec,
    apply_link_focus,
    infer_body_region_from_link_stem,
    validate_analysis_feature_schema,
)
from layer3_jcvpca.request_plan import plan_from_analysis_request


def _report(
    *,
    comparable_stems: list[str],
    extra_stems: list[tuple[str, bool, str]] | None = None,
    missing_stems: list[str] | None = None,
) -> ComparableLinksReport:
    rows = []
    for stem in comparable_stems:
        rows.append(
            {
                "link_stem": stem,
                "display_label": stem,
                "rx_column": f"{stem}_rx",
                "ry_column": f"{stem}_ry",
                "rz_column": f"{stem}_rz",
                "comparable": True,
                "n_selected_matrices": 2,
                "exclusion_reason": "",
            }
        )
    for stem, comparable, reason in extra_stems or []:
        rows.append(
            {
                "link_stem": stem,
                "display_label": stem,
                "rx_column": f"{stem}_rx",
                "ry_column": f"{stem}_ry",
                "rz_column": f"{stem}_rz",
                "comparable": comparable,
                "n_selected_matrices": 2,
                "exclusion_reason": reason,
            }
        )
    excluded = []
    for stem in missing_stems or []:
        excluded.append(
            {
                "link_stem": stem,
                "reason_code": REASON_MISSING_LINK,
                "reason_message": "missing in one matrix",
                "missing_in_matrices": "m2",
                "missing_axes": "",
                "affected_matrices": "m2",
            }
        )
    return ComparableLinksReport(
        comparable_links=pd.DataFrame(rows, columns=COMPARABLE_LINKS_COLUMNS),
        excluded_links=pd.DataFrame(excluded, columns=EXCLUDED_LINKS_COLUMNS),
        summary={
            "comparability_status": "pass",
            "feature_schema_consistent": True,
        },
        comparable_link_stems=list(comparable_stems),
    )


STEMS = [
    "J004_Neck_to_Head",
    "J005_Chest_to_Neck",
    "J010_LShoulder_to_Chest",
    "J015_LUArm_to_LShoulder",
    "J020_LThigh_to_Pelvis",
]


def test_default_full_body_uses_comparable_pool():
    report = _report(comparable_stems=STEMS)
    result = apply_link_focus(report, LinkFocusSpec.default(), feature_schema_id="schema_a")
    assert result.mode == LinkFocusMode.FULL_BODY_COMPARABLE
    assert result.filter_stage == FILTER_STAGE_PCA_INPUT
    assert result.changes_pca_basis is False
    assert result.analysis_link_stems == STEMS
    assert result.excluded_ledger == []


def test_body_region_filter_changes_pca_basis_and_ledgers():
    report = _report(comparable_stems=STEMS)
    spec = LinkFocusSpec(body_regions=("trunk_spine",), use_comparable_links_only=True)
    result = apply_link_focus(report, spec, feature_schema_id="schema_a")
    assert result.mode == LinkFocusMode.ANALYSIS_FEATURE_FILTER
    assert result.changes_pca_basis is True
    assert result.analysis_link_stems == ["J004_Neck_to_Head", "J005_Chest_to_Neck"]
    assert len(result.excluded_ledger) == len(STEMS) - 2
    assert all(row["reason_code"] == "link_focus.body_regions" for row in result.excluded_ledger)


def test_link_stems_explicit_filter():
    report = _report(comparable_stems=STEMS)
    spec = LinkFocusSpec(link_stems=("Neck_to_Head", "LUArm_to_LShoulder"), use_comparable_links_only=True)
    result = apply_link_focus(report, spec)
    assert result.analysis_link_stems == ["J004_Neck_to_Head", "J015_LUArm_to_LShoulder"]
    assert result.excluded_ledger


def test_use_comparable_links_only_false_expands_pool():
    report = _report(
        comparable_stems=["J004_Neck_to_Head"],
        extra_stems=[("J005_Chest_to_Neck", False, REASON_ZERO_VARIANCE)],
    )
    strict = apply_link_focus(report, LinkFocusSpec(use_comparable_links_only=True))
    expanded = apply_link_focus(report, LinkFocusSpec(use_comparable_links_only=False))
    assert strict.analysis_link_stems == ["J004_Neck_to_Head"]
    assert expanded.mode == LinkFocusMode.EXPANDED_LINK_POOL
    assert expanded.changes_pca_basis is True
    assert expanded.analysis_link_stems == ["J004_Neck_to_Head", "J005_Chest_to_Neck"]


def test_over_filter_blocks_with_reason():
    report = _report(comparable_stems=STEMS)
    spec = LinkFocusSpec(body_regions=("other",), link_stems=("Neck_to_Head",))
    result = apply_link_focus(report, spec)
    assert not result.ok
    assert "removed all links" in result.blocking_reason


def test_validate_analysis_feature_schema_augmented_id():
    report = _report(comparable_stems=STEMS)
    ok, schema_id, msg = validate_analysis_feature_schema(
        report,
        ["J004_Neck_to_Head"],
        base_schema_id="schema_a",
    )
    assert ok
    assert schema_id == "schema_a::pca_links=1"
    assert msg == ""


def test_plan_from_request_preserves_link_focus():
    request = {
        "selection": {"participant_id": "671", "blocks": {"A": ["P1"], "B": ["P3"]}},
        "comparisons": [{"comparison_id": "L1_T1_vs_T2"}],
        "link_focus": {
            "body_regions": ["trunk_spine"],
            "link_stems": ["Neck_to_Head"],
            "use_comparable_links_only": False,
        },
    }
    plan = plan_from_analysis_request(request)
    assert plan.link_focus.body_regions == ("trunk_spine",)
    assert plan.link_focus.link_stems == ("Neck_to_Head",)
    assert plan.link_focus.use_comparable_links_only is False


def test_infer_body_region_matches_trunk_and_arm():
    assert infer_body_region_from_link_stem("J004_Neck_to_Head") == "trunk_spine"
    assert infer_body_region_from_link_stem("J015_LUArm_to_LShoulder") == "left_arm"
