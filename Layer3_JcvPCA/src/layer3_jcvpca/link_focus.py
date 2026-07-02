"""Link-focus application for Gaga batch runs (PCA input vs reporting).

When ``body_regions`` or ``link_stems`` are set in the analysis request, filtering
happens **before PCA input construction** and changes the PCA feature basis.
This is explicit, snapshotted, and ledgered — links are never silently dropped.

Default (empty ``body_regions`` and ``link_stems``): full-body comparable-link
analysis using the comparable-link pool (historical behavior).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd

from layer3_jcvpca.comparable_links import REASON_MISSING_LINK, ComparableLinksReport

UPPER_TOKENS = ("Head", "Neck", "Chest", "Spine", "Shoulder", "UArm", "FArm", "Hand", "Clavicle")
LOWER_TOKENS = ("Thigh", "Shin", "Foot", "Toe", "Pelvis", "Waist", "Hip", "Knee", "Ankle", "Femur", "Tibia")

MODE_FULL_BODY_COMPARABLE = "full_body_comparable"
MODE_EXPANDED_LINK_POOL = "expanded_link_pool"
MODE_ANALYSIS_FEATURE_FILTER = "analysis_feature_filter"

FILTER_STAGE_PCA_INPUT = "before_pca_input_construction"
FILTER_STAGE_DISPLAY_ONLY = "results_display_only"


class LinkFocusMode(str, Enum):
    FULL_BODY_COMPARABLE = MODE_FULL_BODY_COMPARABLE
    EXPANDED_LINK_POOL = MODE_EXPANDED_LINK_POOL
    ANALYSIS_FEATURE_FILTER = MODE_ANALYSIS_FEATURE_FILTER


@dataclass(frozen=True)
class LinkFocusSpec:
    body_regions: tuple[str, ...] = ()
    link_stems: tuple[str, ...] = ()
    use_comparable_links_only: bool = True

    @classmethod
    def default(cls) -> LinkFocusSpec:
        return cls()

    @classmethod
    def from_request(cls, request: dict[str, Any] | None) -> LinkFocusSpec:
        if not request:
            return cls.default()
        block = request.get("link_focus") or {}
        regions = tuple(str(x).strip() for x in (block.get("body_regions") or []) if str(x).strip())
        stems = tuple(str(x).strip() for x in (block.get("link_stems") or []) if str(x).strip())
        use_only = block.get("use_comparable_links_only")
        if use_only is None:
            use_only = True
        return cls(
            body_regions=regions,
            link_stems=stems,
            use_comparable_links_only=bool(use_only),
        )

    @property
    def requests_explicit_region_or_stem_filter(self) -> bool:
        return bool(self.body_regions or self.link_stems)

    def resolved_mode(self) -> LinkFocusMode:
        if self.requests_explicit_region_or_stem_filter:
            return LinkFocusMode.ANALYSIS_FEATURE_FILTER
        if not self.use_comparable_links_only:
            return LinkFocusMode.EXPANDED_LINK_POOL
        return LinkFocusMode.FULL_BODY_COMPARABLE


@dataclass
class LinkFocusApplicationResult:
    spec: LinkFocusSpec
    mode: LinkFocusMode
    filter_stage: str
    changes_pca_basis: bool
    use_comparable_links_only: bool
    base_pool_stems: list[str]
    analysis_link_stems: list[str]
    included_ledger: list[dict[str, Any]] = field(default_factory=list)
    excluded_ledger: list[dict[str, Any]] = field(default_factory=list)
    feature_schema_id: str = ""
    blocking_reason: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.analysis_link_stems) and not self.blocking_reason

    def to_manifest_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "filter_stage": self.filter_stage,
            "changes_pca_basis": self.changes_pca_basis,
            "use_comparable_links_only": self.use_comparable_links_only,
            "body_regions_requested": list(self.spec.body_regions),
            "link_stems_requested": list(self.spec.link_stems),
            "base_pool_count": len(self.base_pool_stems),
            "analysis_link_count": len(self.analysis_link_stems),
            "feature_schema_id": self.feature_schema_id,
            "blocking_reason": self.blocking_reason,
            "note": (
                "Filtering applied before PCA input construction when mode is "
                f"{MODE_ANALYSIS_FEATURE_FILTER} or {MODE_EXPANDED_LINK_POOL}. "
                "Display-only filtering is NOT used in the batch runner."
            ),
        }


def infer_body_region_from_link_stem(link_stem: str) -> str:
    """Map a Layer 3 link stem to a coarse body region (matches G3 body_regions.py)."""
    stem = str(link_stem).strip()
    if stem.startswith("J") and "_" in stem:
        stem = stem.split("_", 1)[1]
    parent, _, child = stem.partition("_to_")
    bones = f"{parent} {child} {link_stem}"
    is_upper = any(t in bones for t in UPPER_TOKENS)
    is_lower = any(t in bones for t in LOWER_TOKENS)
    if parent.startswith("L") or child.startswith("L") or "LShoulder" in bones or "LUArm" in bones:
        if is_upper and not is_lower:
            return "left_arm"
        if is_lower and not is_upper:
            return "left_leg"
    if parent.startswith("R") or child.startswith("R") or "RShoulder" in bones or "RUArm" in bones:
        if is_upper and not is_lower:
            return "right_arm"
        if is_lower and not is_upper:
            return "right_leg"
    if "Neck" in bones or "Head" in bones or "Chest" in bones or "Spine" in bones:
        return "trunk_spine"
    if is_upper:
        return "upper_body"
    if is_lower:
        return "lower_body"
    return "other"


def _normalize_stem_token(stem: str) -> str:
    text = str(stem).strip()
    if text.startswith("J") and "_" in text:
        return text.split("_", 1)[1]
    return text


def _base_pool_from_report(
    report: ComparableLinksReport,
    *,
    use_comparable_links_only: bool,
) -> list[str]:
    comparable_stems = list(report.comparable_link_stems)
    if use_comparable_links_only:
        return sorted(comparable_stems)

    comparable_df = report.comparable_links
    excluded_df = report.excluded_links
    if comparable_df.empty:
        return sorted(comparable_stems)

    missing_stems: set[str] = set()
    if not excluded_df.empty and "reason_code" in excluded_df.columns:
        missing = excluded_df[excluded_df["reason_code"].astype(str) == REASON_MISSING_LINK]
        missing_stems = set(missing["link_stem"].astype(str).tolist())

    pool: list[str] = []
    for _, row in comparable_df.iterrows():
        stem = str(row.get("link_stem", "")).strip()
        if not stem or stem in missing_stems:
            continue
        pool.append(stem)
    return sorted(set(pool))


def validate_analysis_feature_schema(
    report: ComparableLinksReport,
    analysis_stems: list[str],
    *,
    base_schema_id: str,
) -> tuple[bool, str, str]:
    """Validate PCA input stems against the comparability report feature schema."""
    if not analysis_stems:
        return False, base_schema_id, "Analysis link stem set is empty."

    if not report.summary.get("feature_schema_consistent", True):
        return (
            False,
            base_schema_id,
            "feature_schema_id is inconsistent across selected matrices; "
            "link_focus cannot change the PCA basis until schemas match.",
        )

    known = set(report.comparable_links["link_stem"].astype(str).tolist())
    unknown = [stem for stem in analysis_stems if stem not in known]
    if unknown:
        preview = ", ".join(unknown[:5])
        suffix = "..." if len(unknown) > 5 else ""
        return (
            False,
            base_schema_id,
            f"link_focus analysis stems not present in comparability report: {preview}{suffix}",
        )

    augmented_id = f"{base_schema_id}::pca_links={len(analysis_stems)}"
    return True, augmented_id, ""


def apply_link_focus(
    report: ComparableLinksReport,
    spec: LinkFocusSpec,
    *,
    feature_schema_id: str = "",
) -> LinkFocusApplicationResult:
    """Select PCA input link stems from a comparability report + request link_focus."""
    mode = spec.resolved_mode()
    base_pool = _base_pool_from_report(report, use_comparable_links_only=spec.use_comparable_links_only)

    result = LinkFocusApplicationResult(
        spec=spec,
        mode=mode,
        filter_stage=FILTER_STAGE_PCA_INPUT,
        changes_pca_basis=mode != LinkFocusMode.FULL_BODY_COMPARABLE,
        use_comparable_links_only=spec.use_comparable_links_only,
        base_pool_stems=base_pool,
        analysis_link_stems=list(base_pool),
        feature_schema_id=feature_schema_id,
    )

    for stem in base_pool:
        result.included_ledger.append(
            {
                "link_stem": stem,
                "body_region": infer_body_region_from_link_stem(stem),
                "status": "included_in_base_pool",
                "reason_code": "base_pool",
                "reason_message": (
                    "Comparable link pool"
                    if spec.use_comparable_links_only
                    else "Expanded pool (present across matrices; use_comparable_links_only=false)"
                ),
            }
        )

    if mode == LinkFocusMode.FULL_BODY_COMPARABLE:
        if not result.analysis_link_stems:
            result.blocking_reason = "No comparable links in base pool."
        return result

    # Explicit stem filter
    if spec.link_stems:
        allowed_exact = set(spec.link_stems)
        allowed_norm = {_normalize_stem_token(s) for s in spec.link_stems}
        kept: list[str] = []
        for stem in result.analysis_link_stems:
            norm = _normalize_stem_token(stem)
            if stem in allowed_exact or norm in allowed_norm:
                kept.append(stem)
            else:
                result.excluded_ledger.append(
                    {
                        "link_stem": stem,
                        "body_region": infer_body_region_from_link_stem(stem),
                        "status": "excluded",
                        "reason_code": "link_focus.link_stems",
                        "reason_message": (
                            f"Not listed in request link_focus.link_stems "
                            f"({list(spec.link_stems)})."
                        ),
                    }
                )
        result.analysis_link_stems = kept

    # Body-region filter
    if spec.body_regions:
        allowed_regions = set(spec.body_regions)
        kept = []
        for stem in result.analysis_link_stems:
            region = infer_body_region_from_link_stem(stem)
            if region in allowed_regions:
                kept.append(stem)
            else:
                result.excluded_ledger.append(
                    {
                        "link_stem": stem,
                        "body_region": region,
                        "status": "excluded",
                        "reason_code": "link_focus.body_regions",
                        "reason_message": (
                            f"Body region {region!r} not in request link_focus.body_regions "
                            f"{list(spec.body_regions)}."
                        ),
                    }
                )
        result.analysis_link_stems = kept

    # Refresh included ledger for final analysis set
    included_set = set(result.analysis_link_stems)
    result.included_ledger = [
        {
            **row,
            "status": "included_for_pca_input",
            "reason_code": "link_focus.included",
            "reason_message": f"Used for PCA input construction ({mode.value}).",
        }
        for row in result.included_ledger
        if row["link_stem"] in included_set
    ]

    if not result.analysis_link_stems:
        result.blocking_reason = (
            "link_focus filters removed all links from the PCA input pool. "
            "Relax body_regions/link_stems or use full-body default."
        )

    return result


def write_link_focus_artifacts(
    output_dir: Path,
    result: LinkFocusApplicationResult,
    *,
    participant_id: str,
    block_id: str,
    comparison_id: str,
) -> dict[str, str]:
    """Write per-comparison link_focus manifest + ledger CSVs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = result.to_manifest_dict()
    manifest.update(
        {
            "participant_id": participant_id,
            "block_id": block_id,
            "comparison_id": comparison_id,
        }
    )
    manifest_path = output_dir / "link_focus_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    ledger_rows = result.included_ledger + result.excluded_ledger
    ledger_path = output_dir / "link_focus_ledger.csv"
    pd.DataFrame(ledger_rows).to_csv(ledger_path, index=False)

    included_path = output_dir / "link_focus_included.csv"
    pd.DataFrame(result.included_ledger).to_csv(included_path, index=False)

    excluded_path = output_dir / "link_focus_excluded.csv"
    pd.DataFrame(result.excluded_ledger).to_csv(excluded_path, index=False)

    return {
        "link_focus_manifest": str(manifest_path),
        "link_focus_ledger": str(ledger_path),
        "link_focus_included": str(included_path),
        "link_focus_excluded": str(excluded_path),
    }
