"""Map validated ``analysis_request.yaml`` to Gaga batch plan inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from layer3_jcvpca.batch_settings import GagaBatchSettings
from layer3_jcvpca.gaga_batch_runner import BLOCK_EXERCISES, TARGET_PARTICIPANTS, build_comparison_specs
from layer3_jcvpca.link_focus import LinkFocusSpec


@dataclass(frozen=True)
class RequestBatchPlan:
    participants: tuple[str, ...]
    blocks: dict[str, list[str]]
    comparison_ids: tuple[str, ...]
    settings: GagaBatchSettings
    request: dict[str, Any]
    link_focus: LinkFocusSpec
    request_path: Path | None = None


def load_analysis_request_yaml(path: Path | str) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def plan_from_analysis_request(
    request: dict[str, Any],
    *,
    settings: GagaBatchSettings | None = None,
    request_path: Path | None = None,
) -> RequestBatchPlan:
    """Build batch plan fields from a validated analysis request document."""
    selection = request.get("selection") or {}
    participant_id = str(selection.get("participant_id") or "").strip()
    if not participant_id:
        raise ValueError("analysis_request.selection.participant_id is required.")

    blocks = selection.get("blocks") or {}
    block_a = list(blocks.get("A") or BLOCK_EXERCISES["A"])
    block_b = list(blocks.get("B") or BLOCK_EXERCISES["B"])
    block_map = {"A": block_a, "B": block_b}

    comparison_ids = [
        str(item.get("comparison_id")).strip()
        for item in (request.get("comparisons") or [])
        if str(item.get("comparison_id", "")).strip()
    ]
    if not comparison_ids:
        raise ValueError("analysis_request.comparisons must list at least one comparison_id.")

    known = {spec.comparison_id for spec in build_comparison_specs()}
    unknown = [cid for cid in comparison_ids if cid not in known]
    if unknown:
        raise ValueError(f"Unknown comparison_id(s) in request: {unknown}")

    base_settings = settings or GagaBatchSettings.defaults()
    merged_settings = base_settings.merge_request_outputs(request.get("outputs"))

    return RequestBatchPlan(
        participants=(participant_id,),
        blocks=block_map,
        comparison_ids=tuple(comparison_ids),
        settings=merged_settings,
        request=request,
        link_focus=LinkFocusSpec.from_request(request),
        request_path=request_path,
    )


def plan_from_analysis_request_path(
    path: Path | str,
    *,
    project_root: Path | None = None,
) -> RequestBatchPlan:
    request_path = Path(path).resolve()
    request = load_analysis_request_yaml(request_path)
    settings = GagaBatchSettings.from_analysis_config(project_root)
    return plan_from_analysis_request(
        request,
        settings=settings,
        request_path=request_path,
    )


def default_participants_fallback() -> tuple[str, ...]:
    return tuple(TARGET_PARTICIPANTS)
