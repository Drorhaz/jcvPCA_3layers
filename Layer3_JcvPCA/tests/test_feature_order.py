"""Feature name/order match tests."""

from __future__ import annotations

import pytest

from layer3_jcvpca.io import infer_feature_columns
from layer3_jcvpca.validation import ValidationError, validate_feature_schema_match

from conftest import FEATURE_NAMES, make_matrix


def test_identical_schema_passes():
    A = make_matrix(seed=1)
    B = make_matrix(seed=2)
    validate_feature_schema_match({"A": A, "B": B}, FEATURE_NAMES)


def test_feature_order_mismatch_fails():
    A = make_matrix(seed=1)
    reordered = FEATURE_NAMES[::-1]
    B = make_matrix(seed=2, feature_names=reordered)
    # Same names, different order.
    assert set(infer_feature_columns(B)) == set(FEATURE_NAMES)
    with pytest.raises(ValidationError) as exc:
        validate_feature_schema_match({"A": A, "B": B}, FEATURE_NAMES)
    assert "order" in str(exc.value).lower()


def test_feature_name_mismatch_fails():
    A = make_matrix(seed=1)
    renamed = list(FEATURE_NAMES)
    renamed[0] = "J999_Extra_Link_rx"
    B = make_matrix(seed=2, feature_names=renamed)
    with pytest.raises(ValidationError) as exc:
        validate_feature_schema_match({"A": A, "B": B}, FEATURE_NAMES)
    assert "name" in str(exc.value).lower()
