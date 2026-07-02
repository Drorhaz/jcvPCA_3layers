#!/usr/bin/env python3
"""Smoke-validate link_focus: full-body vs trunk_spine on timestamped batches only."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
L25_SRC = REPO_ROOT / "Layer2.5_Segmentation" / "src"
for entry in (str(SRC), str(L25_SRC)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from g6_execution import assert_non_canonical_batch_path, execute_layer3_batch
from project_status import load_project_snapshot


def _fingerprint(path: Path) -> str:
    if not path.is_file():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _load_base_request() -> dict:
    path = REPO_ROOT / "requests" / "analysis_requests" / "g6_smoke_671_20260701_211132.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Base smoke request missing: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_request(request: dict, stamp: str, label: str) -> Path:
    out_dir = REPO_ROOT / "requests" / "analysis_requests"
    out_dir.mkdir(parents=True, exist_ok=True)
    rid = f"link_focus_smoke_{label}_{stamp}"
    request = copy.deepcopy(request)
    request["request_id"] = rid
    request["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = out_dir / f"{rid}.yaml"
    path.write_text(yaml.safe_dump(request, sort_keys=False), encoding="utf-8")
    return path


def _run_case(
    *,
    snapshot,
    stamp: str,
    label: str,
    request: dict,
    canonical_before: str,
) -> dict:
    batch_root = REPO_ROOT / "Layer3_JcvPCA" / "outputs" / f"gaga_batch_jcvpca_linkfocus_{label}_{stamp}"
    assert_non_canonical_batch_path(batch_root, snapshot)
    request_path = _write_request(request, stamp, label)
    runner_plan = {
        "proposed_batch_root": str(batch_root),
        "layer25_root": str(REPO_ROOT / "processed" / "pre_jvcpca_review"),
        "participant_ids": ["671"],
    }
    print(f"\n=== Running {label} → {batch_root.name} ===")
    result = execute_layer3_batch(
        REPO_ROOT,
        snapshot,
        runner_plan,
        batch_root=batch_root,
        analysis_request_path=request_path,
        smoke=True,
        timeout_s=7200,
    )
    canonical_after = _fingerprint(snapshot.canonical_batch_path / "batch_summary.md")
    status_path = batch_root / "comparison_status.csv"
    link_focus_path = batch_root / "link_focus_by_comparison.csv"
    comp_key = "671_B_L1_T1_vs_T2"
    manifest_path = batch_root / "comparisons" / comp_key / "link_focus_manifest.json"
    ledger_path = batch_root / "comparisons" / comp_key / "link_focus_ledger.csv"
    runner_settings = batch_root / "_config_snapshot" / "runner_settings.json"

    metrics: dict = {
        "label": label,
        "batch_root": str(batch_root),
        "request_path": str(request_path),
        "returncode": result["returncode"],
        "canonical_untouched": canonical_before == canonical_after,
    }
    if status_path.is_file():
        row = pd.read_csv(status_path).iloc[0].to_dict()
        metrics.update(
            {
                "status": row.get("status"),
                "n_comparable_links": row.get("n_comparable_links"),
                "n_analysis_links": row.get("n_analysis_links"),
                "n_pca_features": row.get("n_pca_features"),
                "feature_schema_id": row.get("feature_schema_id"),
                "link_focus_mode": row.get("link_focus_mode"),
                "link_focus_changes_pca_basis": row.get("link_focus_changes_pca_basis"),
            }
        )
    if manifest_path.is_file():
        metrics["link_focus_manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if ledger_path.is_file():
        ledger = pd.read_csv(ledger_path)
        metrics["n_included_ledger"] = int((ledger["status"].astype(str).str.contains("included")).sum())
        metrics["n_excluded_ledger"] = int((ledger["status"].astype(str).str.startswith("excluded")).sum())
        metrics["excluded_reason_codes"] = sorted(
            ledger.loc[ledger["status"].astype(str).str.startswith("excluded"), "reason_code"]
            .astype(str)
            .unique()
            .tolist()
        )
    metrics["artifacts"] = {
        "comparison_status": status_path.is_file(),
        "link_focus_by_comparison": link_focus_path.is_file(),
        "link_focus_manifest": manifest_path.is_file(),
        "link_focus_ledger": ledger_path.is_file(),
        "runner_settings": runner_settings.is_file(),
        "analysis_request_copy": (batch_root / "analysis_request.yaml").is_file(),
    }
    return metrics


def main() -> int:
    snapshot = load_project_snapshot(project_root=REPO_ROOT)
    if snapshot.canonical_batch_path is None:
        print("ERROR: canonical batch not configured")
        return 1
    canonical_before = _fingerprint(snapshot.canonical_batch_path / "batch_summary.md")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = _load_base_request()

    full_body = copy.deepcopy(base)
    full_body["link_focus"] = {
        "body_regions": [],
        "link_stems": [],
        "use_comparable_links_only": True,
    }

    trunk = copy.deepcopy(base)
    trunk["link_focus"] = {
        "body_regions": ["trunk_spine"],
        "link_stems": [],
        "use_comparable_links_only": True,
    }

    full_metrics = _run_case(
        snapshot=snapshot,
        stamp=stamp,
        label="full_body",
        request=full_body,
        canonical_before=canonical_before,
    )
    trunk_metrics = _run_case(
        snapshot=snapshot,
        stamp=stamp,
        label="trunk_spine",
        request=trunk,
        canonical_before=canonical_before,
    )

    checks = {
        "full_body_completed": full_metrics.get("status") == "completed",
        "trunk_completed": trunk_metrics.get("status") == "completed",
        "full_body_no_pca_basis_change": full_metrics.get("link_focus_changes_pca_basis") in (False, "False", 0),
        "trunk_changes_pca_basis": trunk_metrics.get("link_focus_changes_pca_basis") in (True, "True", 1),
        "trunk_fewer_features": (
            int(trunk_metrics.get("n_pca_features") or 0)
            < int(full_metrics.get("n_pca_features") or 0)
        ),
        "trunk_has_exclusions": int(trunk_metrics.get("n_excluded_ledger") or 0) > 0,
        "both_canonical_untouched": full_metrics.get("canonical_untouched")
        and trunk_metrics.get("canonical_untouched"),
        "full_returncode_zero": full_metrics.get("returncode") == 0,
        "trunk_returncode_zero": trunk_metrics.get("returncode") == 0,
    }

    report = {
        "stamp": stamp,
        "checks": checks,
        "full_body": full_metrics,
        "trunk_spine": trunk_metrics,
        "comparison": {
            "n_comparable_links_full": full_metrics.get("n_comparable_links"),
            "n_analysis_links_full": full_metrics.get("n_analysis_links"),
            "n_pca_features_full": full_metrics.get("n_pca_features"),
            "n_comparable_links_trunk": trunk_metrics.get("n_comparable_links"),
            "n_analysis_links_trunk": trunk_metrics.get("n_analysis_links"),
            "n_pca_features_trunk": trunk_metrics.get("n_pca_features"),
            "feature_delta": int(full_metrics.get("n_pca_features") or 0)
            - int(trunk_metrics.get("n_pca_features") or 0),
        },
    }
    report_path = (
        REPO_ROOT / "processed" / "pre_jvcpca_review" / "_gui_runs" / f"link_focus_smoke_report_{stamp}.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("\nlink_focus smoke checks:")
    for key, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {key}")
    print(f"\nReport: {report_path}")
    print(
        "Feature counts: full_body n_pca_features="
        f"{full_metrics.get('n_pca_features')} vs trunk_spine "
        f"{trunk_metrics.get('n_pca_features')}"
    )
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
