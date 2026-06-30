"""PC analysis focus selection for Gaga workbench (Phase 9 / Step 9).

Determines which PCs (from A's selected_m) are included in downstream JcvPCA summaries.
Does not project B or run full JcvPCA.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

PC_FOCUS_FUNCTIONAL = "functional"
PC_FOCUS_NULL_SPACE = "null_space"
PC_FOCUS_ALL = "all"
PC_FOCUS_MANUAL = "manual"

PC_FOCUS_MODES: tuple[str, ...] = (
    PC_FOCUS_FUNCTIONAL,
    PC_FOCUS_NULL_SPACE,
    PC_FOCUS_ALL,
    PC_FOCUS_MANUAL,
)

PC_FOCUS_ROLE_FUNCTIONAL = "functional"
PC_FOCUS_ROLE_NULL_SPACE = "null_space"
PC_FOCUS_ROLE_ALL_SELECTED = "all_selected"
PC_FOCUS_ROLE_MANUAL = "manual"
PC_FOCUS_ROLE_EXCLUDED = "excluded"

PC_FOCUS_TABLE_COLUMNS = [
    "pc",
    "explained_variance_ratio",
    "cumulative_explained_variance",
    "role",
    "included",
]


@dataclass
class PcFocusParameters:
    pc_focus_mode: str = PC_FOCUS_ALL
    p: int | None = None
    manual_pcs: list[int] | None = None


@dataclass
class PcFocusResult:
    selected_m: int
    parameters: PcFocusParameters
    focus_table: pd.DataFrame
    included_pcs: list[int]
    selection_reason: str
    validation_errors: list[str] = field(default_factory=list)


def validate_pc_focus_parameters(
    params: PcFocusParameters,
    *,
    selected_m: int,
) -> list[str]:
    """Return validation errors; empty list means parameters are usable."""
    errors: list[str] = []
    if params.pc_focus_mode not in PC_FOCUS_MODES:
        errors.append(f"Unknown pc_focus_mode={params.pc_focus_mode!r}.")

    if selected_m < 1:
        errors.append("selected_m must be >= 1 for PC focus selection.")

    if params.pc_focus_mode in {PC_FOCUS_FUNCTIONAL, PC_FOCUS_NULL_SPACE}:
        if params.p is None:
            errors.append(
                f"p / estimated task DoF is required for pc_focus_mode={params.pc_focus_mode!r}; "
                "p is not inferred silently."
            )
        elif params.p < 1:
            errors.append("p must be >= 1.")
        elif params.p > selected_m:
            errors.append(f"p={params.p} exceeds selected_m={selected_m}.")

    if params.pc_focus_mode == PC_FOCUS_NULL_SPACE:
        if params.p is not None and params.p >= selected_m:
            errors.append(
                f"Null-space focus requires p < selected_m so at least one PC in p+1..selected_m exists "
                f"(p={params.p}, selected_m={selected_m})."
            )

    if params.pc_focus_mode == PC_FOCUS_MANUAL:
        manual = params.manual_pcs or []
        if not manual:
            errors.append("manual_pcs must contain at least one PC for manual focus mode.")
        for pc in manual:
            if pc < 1 or pc > selected_m:
                errors.append(f"manual PC {pc} is outside 1..selected_m={selected_m}.")

    return errors


def _included_pcs_for_mode(params: PcFocusParameters, selected_m: int) -> list[int]:
    if params.pc_focus_mode == PC_FOCUS_ALL:
        return list(range(1, selected_m + 1))

    if params.pc_focus_mode == PC_FOCUS_FUNCTIONAL:
        assert params.p is not None
        return list(range(1, params.p + 1))

    if params.pc_focus_mode == PC_FOCUS_NULL_SPACE:
        assert params.p is not None
        return list(range(params.p + 1, selected_m + 1))

    manual = sorted(set(params.manual_pcs or []))
    return [pc for pc in manual if 1 <= pc <= selected_m]


def _selection_reason(params: PcFocusParameters, selected_m: int, included: list[int]) -> str:
    if params.pc_focus_mode == PC_FOCUS_ALL:
        return f"all selected PCs: PC1..PC{selected_m}"
    if params.pc_focus_mode == PC_FOCUS_FUNCTIONAL:
        return f"functional PCs: PC1..PC{params.p}"
    if params.pc_focus_mode == PC_FOCUS_NULL_SPACE:
        return f"null-space PCs: PC{params.p + 1}..PC{selected_m}"
    return f"manual PCs: {included}"


def build_pc_focus_table(
    *,
    selected_m: int,
    explained_variance: pd.DataFrame,
    cumulative_variance: pd.DataFrame,
    params: PcFocusParameters,
) -> PcFocusResult:
    """Build PC focus table and included PC list from A PCA artifacts."""
    errors = validate_pc_focus_parameters(params, selected_m=selected_m)
    if errors:
        return PcFocusResult(
            selected_m=selected_m,
            parameters=params,
            focus_table=pd.DataFrame(columns=PC_FOCUS_TABLE_COLUMNS),
            included_pcs=[],
            selection_reason="",
            validation_errors=errors,
        )

    included_set = set(_included_pcs_for_mode(params, selected_m))
    included = sorted(included_set)
    if not included:
        errors.append("PC focus selection produced zero included PCs.")
        return PcFocusResult(
            selected_m=selected_m,
            parameters=params,
            focus_table=pd.DataFrame(columns=PC_FOCUS_TABLE_COLUMNS),
            included_pcs=[],
            selection_reason="",
            validation_errors=errors,
        )

    evr_map = {
        int(row["pc"]): float(row["explained_variance_ratio"])
        for _, row in explained_variance.iterrows()
    }
    cum_map = {
        int(row["pc"]): float(row["cumulative_explained_variance"])
        for _, row in cumulative_variance.iterrows()
    }

    rows: list[dict[str, Any]] = []
    for pc in range(1, selected_m + 1):
        is_included = pc in included_set
        if params.pc_focus_mode == PC_FOCUS_FUNCTIONAL:
            if is_included:
                role = PC_FOCUS_ROLE_FUNCTIONAL
            elif pc <= (params.p or 0):
                role = PC_FOCUS_ROLE_EXCLUDED
            else:
                role = PC_FOCUS_ROLE_EXCLUDED
        elif params.pc_focus_mode == PC_FOCUS_NULL_SPACE:
            if is_included:
                role = PC_FOCUS_ROLE_NULL_SPACE
            elif pc <= (params.p or 0):
                role = PC_FOCUS_ROLE_FUNCTIONAL
            else:
                role = PC_FOCUS_ROLE_EXCLUDED
        elif params.pc_focus_mode == PC_FOCUS_MANUAL:
            role = PC_FOCUS_ROLE_MANUAL if is_included else PC_FOCUS_ROLE_EXCLUDED
        else:
            role = PC_FOCUS_ROLE_ALL_SELECTED if is_included else PC_FOCUS_ROLE_EXCLUDED

        rows.append(
            {
                "pc": pc,
                "explained_variance_ratio": evr_map.get(pc),
                "cumulative_explained_variance": cum_map.get(pc),
                "role": role,
                "included": is_included,
            }
        )

    table = pd.DataFrame(rows)[PC_FOCUS_TABLE_COLUMNS]
    reason = _selection_reason(params, selected_m, included)
    return PcFocusResult(
        selected_m=selected_m,
        parameters=params,
        focus_table=table,
        included_pcs=included,
        selection_reason=reason,
        validation_errors=[],
    )


def pc_focus_selection_payload(result: PcFocusResult) -> dict[str, Any]:
    params = result.parameters
    return {
        "pc_focus_mode": params.pc_focus_mode,
        "p": params.p,
        "manual_pcs": params.manual_pcs,
        "selected_m": result.selected_m,
        "included_pcs": result.included_pcs,
        "n_included_pcs": len(result.included_pcs),
        "selection_reason": result.selection_reason,
        "p_inferred_silently": False,
    }
