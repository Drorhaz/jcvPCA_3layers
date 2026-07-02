"""Read-only decision summary aggregation for Layer 3 batch folders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from comparability import ComparabilityStatus, comparability_status, load_artifact_science_hash


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def load_batch_decision_summary(
    batch_root: Path,
    *,
    current_science_hash: str | None = None,
    is_canonical: bool = False,
) -> dict[str, Any]:
    """Aggregate key read-only evidence from a Layer 3 batch directory."""
    batch_root = batch_root.resolve()
    status_df = _read_csv(batch_root / "comparison_status.csv")
    link_df = _read_csv(batch_root / "jcvpca_link_results.csv")
    nv_df = _read_csv(batch_root / "nv_baseline_results.csv")

    completed = int((status_df["status"] == "completed").sum()) if not status_df.empty else 0
    total = len(status_df)

    top_links: list[dict[str, Any]] = []
    effect_col = "JcvPCA_link" if "JcvPCA_link" in link_df.columns else "jcvpca_unweighted"
    if not link_df.empty and effect_col in link_df.columns:
        work = link_df.copy()
        work["abs_effect"] = work[effect_col].astype(float).abs()
        link_name_col = "link_id" if "link_id" in work.columns else "link_stem"
        group = work.sort_values(["abs_effect"], ascending=False).head(10)
        for _, row in group.iterrows():
            top_links.append(
                {
                    "link": str(row.get(link_name_col, "?")),
                    "jcvpca": float(row.get(effect_col, 0.0)),
                    "comparison_key": str(row.get("comparison_key", "")),
                }
            )

    body_regions: list[dict[str, Any]] = []
    if not link_df.empty and "body_region" in link_df.columns and effect_col in link_df.columns:
        tmp = link_df.copy()
        tmp["abs_effect"] = tmp[effect_col].astype(float).abs()
        for region, grp in tmp.groupby("body_region"):
            body_regions.append(
                {
                    "body_region": str(region),
                    "n_links": len(grp),
                    "median_abs_effect": float(grp["abs_effect"].median()),
                    "max_abs_effect": float(grp["abs_effect"].max()),
                }
            )
        body_regions.sort(key=lambda r: r["max_abs_effect"], reverse=True)

    request_path = batch_root / "analysis_request.yaml"
    request: dict[str, Any] = {}
    if request_path.is_file():
        loaded = yaml.safe_load(request_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            request = loaded

    config_snap = batch_root / "_config_snapshot" / "config_hash.json"
    batch_hash = None
    comparability = ComparabilityStatus.UNKNOWN
    if config_snap.is_file():
        meta = _read_json(config_snap)
        batch_hash = str(meta.get("science_hash") or "")
        if current_science_hash:
            comparability = comparability_status(
                batch_hash,
                current_science_hash,
                is_canonical_batch=is_canonical,
            )
    elif is_canonical:
        batch_hash = load_artifact_science_hash(batch_root)
        if current_science_hash:
            comparability = comparability_status(
                batch_hash,
                current_science_hash,
                is_canonical_batch=True,
            )

    nv_summary = {}
    if not nv_df.empty:
        if "delta_jrw" in nv_df.columns and "nv_band_half_width" in nv_df.columns:
            nv_summary = {
                "rows": len(nv_df),
                "median_delta_jrw": float(nv_df["delta_jrw"].astype(float).median()),
                "median_nv_band": float(nv_df["nv_band_half_width"].astype(float).median()),
            }

    link_focus_df = _read_csv(batch_root / "link_focus_by_comparison.csv")
    link_focus_ledger_df = _read_csv(batch_root / "link_focus_ledger_by_comparison.csv")
    on_demand_manifest = _read_json(batch_root / "on_demand_reports_manifest.json")

    link_focus_summary: list[dict[str, Any]] = []
    if not link_focus_df.empty:
        link_focus_summary = link_focus_df.to_dict("records")

    return {
        "batch_root": str(batch_root),
        "batch_id": batch_root.name,
        "is_canonical": is_canonical,
        "comparison_status": {
            "completed": completed,
            "total": total,
            "rows": status_df.to_dict("records") if not status_df.empty else [],
        },
        "effect_vs_nv": nv_summary,
        "top_links": top_links,
        "body_regions": body_regions[:12],
        "request_provenance": {
            "request_id": request.get("request_id"),
            "status": request.get("status"),
            "science_hash": (request.get("provenance") or {}).get("science_hash"),
            "participant_id": (request.get("selection") or {}).get("participant_id"),
            "comparisons": [c.get("comparison_id") for c in (request.get("comparisons") or [])],
        },
        "config_hash": batch_hash,
        "comparability": comparability.value,
        "batch_summary_exists": (batch_root / "batch_summary.md").is_file(),
        "link_focus": link_focus_summary,
        "link_focus_excluded_count": int(
            link_focus_ledger_df["status"].astype(str).str.startswith("excluded").sum()
        )
        if not link_focus_ledger_df.empty and "status" in link_focus_ledger_df.columns
        else 0,
        "on_demand_reports": on_demand_manifest,
    }


def compare_batch_summaries(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Compare two batch decision summaries (read-only diff for Stage 6)."""
    base_rows = {
        (
            str(row.get("participant_id", "")),
            str(row.get("block_id", "")),
            str(row.get("comparison_id", "")),
        ): row
        for row in (baseline.get("comparison_status") or {}).get("rows") or []
    }
    cand_rows = {
        (
            str(row.get("participant_id", "")),
            str(row.get("block_id", "")),
            str(row.get("comparison_id", "")),
        ): row
        for row in (candidate.get("comparison_status") or {}).get("rows") or []
    }
    keys = sorted(set(base_rows) | set(cand_rows))
    comparison_diff: list[dict[str, Any]] = []
    for key in keys:
        left = base_rows.get(key, {})
        right = cand_rows.get(key, {})
        comparison_diff.append(
            {
                "participant_id": key[0],
                "block_id": key[1],
                "comparison_id": key[2],
                "baseline_status": left.get("status"),
                "candidate_status": right.get("status"),
                "baseline_n_pca_features": left.get("n_pca_features"),
                "candidate_n_pca_features": right.get("n_pca_features"),
                "baseline_link_focus_mode": left.get("link_focus_mode"),
                "candidate_link_focus_mode": right.get("link_focus_mode"),
                "baseline_n_analysis_links": left.get("n_analysis_links"),
                "candidate_n_analysis_links": right.get("n_analysis_links"),
            }
        )

    return {
        "baseline_batch_id": baseline.get("batch_id"),
        "candidate_batch_id": candidate.get("batch_id"),
        "baseline_completed": (baseline.get("comparison_status") or {}).get("completed"),
        "candidate_completed": (candidate.get("comparison_status") or {}).get("completed"),
        "config_hash_match": baseline.get("config_hash") == candidate.get("config_hash"),
        "comparison_diff": comparison_diff,
        "link_focus_baseline": baseline.get("link_focus") or [],
        "link_focus_candidate": candidate.get("link_focus") or [],
    }
