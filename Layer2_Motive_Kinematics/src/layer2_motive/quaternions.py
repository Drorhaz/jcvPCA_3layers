"""Quaternion component-order helpers and SciPy Rotation utilities (Stage 02+)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation

from layer2_motive.parsing import MOTIVE_COMPONENT_ORDER

SCIPY_QUAT_COMPONENT_ORDER = ("x", "y", "z", "w")
MOTIVE_TO_SCIPY_MAPPING = "Motive X,Y,Z,W -> SciPy x,y,z,w"


@dataclass(frozen=True)
class ConstructabilityResult:
    """Outcome of attempting SciPy Rotation construction for one component order."""

    order_label: str
    sample_size: int
    constructible_count: int
    non_finite_row_count: int
    construction_error_count: int
    first_error_message: str | None

    @property
    def constructible(self) -> bool:
        return self.sample_size > 0 and self.construction_error_count == 0

    @property
    def constructibility_rate(self) -> float:
        if self.sample_size == 0:
            return 0.0
        return self.constructible_count / self.sample_size


def motive_labels_compatible_with_scipy() -> bool:
    """Motive exports label quaternion components X, Y, Z, W matching SciPy scalar-last order."""
    return tuple(label.lower() for label in MOTIVE_COMPONENT_ORDER) == SCIPY_QUAT_COMPONENT_ORDER


def try_construct_rotations(quats: np.ndarray) -> tuple[int, int, str | None]:
    """Attempt SciPy construction row-wise; return (success_count, error_count, first_error)."""
    if quats.ndim != 2 or quats.shape[1] != 4:
        raise ValueError("quats must have shape (n, 4)")

    success = 0
    errors = 0
    first_error: str | None = None
    for row in quats:
        try:
            Rotation.from_quat(row)
            success += 1
        except ValueError as exc:
            errors += 1
            if first_error is None:
                first_error = str(exc)
    return success, errors, first_error


def evaluate_component_order(
    x: pd.Series,
    y: pd.Series,
    z: pd.Series,
    w: pd.Series,
    *,
    order_label: str,
    scipy_order: tuple[int, int, int, int],
) -> ConstructabilityResult:
    """Evaluate constructability for one quaternion component reordering."""
    components = pd.concat([x, y, z, w], axis=1)
    components.columns = ["x", "y", "z", "w"]
    finite_mask = components.notna().all(axis=1)
    non_finite_row_count = int((~finite_mask).sum())
    finite = components.loc[finite_mask]
    sample_size = len(finite)
    if sample_size == 0:
        return ConstructabilityResult(
            order_label=order_label,
            sample_size=0,
            constructible_count=0,
            non_finite_row_count=non_finite_row_count,
            construction_error_count=0,
            first_error_message=None,
        )

    ordered = finite.iloc[:, list(scipy_order)].to_numpy(dtype=float)
    constructible_count, error_count, first_error = try_construct_rotations(ordered)
    return ConstructabilityResult(
        order_label=order_label,
        sample_size=sample_size,
        constructible_count=constructible_count,
        non_finite_row_count=non_finite_row_count,
        construction_error_count=error_count,
        first_error_message=first_error,
    )


def validate_bone_rotation_group(
    x: pd.Series,
    y: pd.Series,
    z: pd.Series,
    w: pd.Series,
) -> dict[str, Any]:
    """Validate one bone's Motive XYZW columns for SciPy component-order compatibility."""
    primary = evaluate_component_order(
        x,
        y,
        z,
        w,
        order_label="motive_xyzw_to_scipy_xyzw",
        scipy_order=(0, 1, 2, 3),
    )
    alternative = evaluate_component_order(
        x,
        y,
        z,
        w,
        order_label="motive_xyzw_as_wxyz_alternative",
        scipy_order=(3, 0, 1, 2),
    )

    missing_components: list[str] = []
    for label, series in zip(MOTIVE_COMPONENT_ORDER, [x, y, z, w], strict=True):
        if series is None:
            missing_components.append(label)

    labels_compatible = motive_labels_compatible_with_scipy() and not missing_components
    selected_order = "x,y,z,w" if labels_compatible else "undetermined"
    constructability_status = "pass" if primary.constructible else "fail"
    if primary.sample_size == 0:
        constructability_status = "fail"

    return {
        "motive_component_labels": ",".join(MOTIVE_COMPONENT_ORDER),
        "scipy_component_order": ",".join(SCIPY_QUAT_COMPONENT_ORDER),
        "selected_scipy_order": selected_order,
        "labels_compatible_with_scipy": labels_compatible,
        "sample_size": primary.sample_size,
        "constructible_count": primary.constructible_count,
        "construction_error_count": primary.construction_error_count,
        "non_finite_row_count": primary.non_finite_row_count,
        "constructability_status": constructability_status,
        "primary_constructibility_rate": round(primary.constructibility_rate, 6),
        "alternative_order_label": alternative.order_label,
        "alternative_constructible_count": alternative.constructible_count,
        "alternative_construction_error_count": alternative.construction_error_count,
        "alternative_constructibility_rate": round(alternative.constructibility_rate, 6),
        "first_construction_error": primary.first_error_message,
        "missing_components": ",".join(missing_components),
    }


def construct_identity_rotation() -> Rotation:
    """Construct identity rotation from known SciPy-order quaternion [0, 0, 0, 1]."""
    return Rotation.from_quat([0.0, 0.0, 0.0, 1.0])
