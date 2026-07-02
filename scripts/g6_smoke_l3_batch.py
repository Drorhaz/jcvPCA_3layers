#!/usr/bin/env python3
"""G6 smoke validation: one timestamped Layer 3 batch + artifact checks."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
L25_SRC = REPO_ROOT / "Layer2.5_Segmentation" / "src"
for entry in (str(SRC), str(L25_SRC)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from analysis_config import load_analysis_config
from analysis_request import (
    AnalysisRequestInput,
    build_analysis_request,
    comparison_spec_from_preset,
    save_analysis_request,
)
from g6_execution import (
    append_change_audit_log,
    assert_non_canonical_batch_path,
    build_layer3_argv,
    execute_layer3_batch,
    verification_snapshot_path,
)
from project_status import load_project_snapshot
from segmentation_coverage import EXERCISE_SELECTION_ALL_IN_SHEET
from verification_gate import VerificationState, save_verification_snapshot, sign_off


def _file_fingerprint(path: Path) -> str:
    if not path.is_file():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main() -> int:
    snapshot = load_project_snapshot(project_root=REPO_ROOT)
    canonical = snapshot.canonical_batch_path
    if canonical is None:
        print("ERROR: canonical batch path not configured")
        return 1
    canonical_before = _file_fingerprint(canonical / "batch_summary.md")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    batch_root = REPO_ROOT / "Layer3_JcvPCA" / "outputs" / f"gaga_batch_jcvpca_g6smoke_{stamp}"
    assert_non_canonical_batch_path(batch_root, snapshot)

    # Stage 5 equivalent: verification snapshot
    vstate = VerificationState()
    vstate.verified_segment_ids.add("671_T1_P1_R1::ex01")
    sign_off(vstate, notes="G6 smoke validation", science_hash=snapshot.config.science_hash)
    vpath = save_verification_snapshot(REPO_ROOT, vstate)
    print(f"verification_snapshot: {vpath}")

    # Stage 6 equivalent: validated analysis request
    inp = AnalysisRequestInput(
        participant_id="671",
        repetitions=("R1", "R2"),
        p_phases=("P3", "P4", "P5"),
        comparisons=[comparison_spec_from_preset("L1_T1_vs_T2", ("R1", "R2"))],
        exercise_selection_mode=EXERCISE_SELECTION_ALL_IN_SHEET,
    )
    request = build_analysis_request(
        snapshot,
        inp,
        request_id=f"g6_smoke_671_{stamp}",
        check_comparable_links=False,
    )
    request_path = save_analysis_request(REPO_ROOT, request)
    print(f"analysis_request: {request_path}")

    runner_plan = {
        "proposed_batch_root": str(batch_root),
        "layer25_root": str(REPO_ROOT / "processed" / "pre_jvcpca_review"),
        "participant_ids": ["671"],
    }

    print(f"Running smoke batch → {batch_root}")
    result = execute_layer3_batch(
        REPO_ROOT,
        snapshot,
        runner_plan,
        batch_root=batch_root,
        analysis_request_path=request_path,
        smoke=True,
        timeout_s=7200,
    )
    print(f"returncode: {result['returncode']}")
    if result["returncode"] != 0:
        print(result.get("stderr", "")[-4000:])
        return result["returncode"] or 1

    cfg = load_analysis_config(project_root=REPO_ROOT)
    snap_dir = cfg.write_snapshot(batch_root)

    gui_log = append_change_audit_log(
        REPO_ROOT,
        {
            "action": "g6_smoke_l3_batch",
            "batch_root": str(batch_root),
            "request_path": str(request_path),
            "verification_snapshot": str(vpath),
            "returncode": result["returncode"],
        },
    )

    canonical_after = _file_fingerprint(canonical / "batch_summary.md")
    checks = {
        "batch_root": batch_root.is_dir(),
        "batch_summary": (batch_root / "batch_summary.md").is_file(),
        "comparison_status": (batch_root / "comparison_status.csv").is_file(),
        "analysis_request_copy": (batch_root / "analysis_request.yaml").is_file(),
        "config_snapshot": snap_dir.is_dir() and (snap_dir / "config_hash.json").is_file(),
        "verification_snapshot": vpath.is_file(),
        "gui_audit_log": gui_log.is_file(),
        "canonical_untouched": canonical_before == canonical_after and canonical_before != "missing",
        "timestamped_name": batch_root.name.startswith("gaga_batch_jcvpca_g6smoke_"),
    }
    report_path = REPO_ROOT / "processed" / "pre_jvcpca_review" / "_gui_runs" / f"g6_smoke_report_{stamp}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"checks": checks, "batch_root": str(batch_root)}, indent=2), encoding="utf-8")

    print("\nG6 smoke artifact checks:")
    for key, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {key}")
    print(f"\nReport: {report_path}")
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
