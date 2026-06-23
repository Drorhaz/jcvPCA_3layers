"""Validate Layer 1 / Layer 2 input contracts, identity, alignment, and joins."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from layer2_motive.segmentation.schemas import (
    CANONICAL_JOIN_KEY,
    LAYER1_MANIFEST_REQUIRED_KEYS,
    LAYER1_QC_MASK_EXPECTED_COLUMNS,
    LAYER1_QC_MASK_REQUIRED_COLUMNS,
    LAYER1_REQUIRED_FILES,
    LAYER2_LINK_MANIFEST_REQUIRED_COLUMNS,
    LAYER2_PARQUET_EXPECTED_COLUMNS,
    LAYER2_PARQUET_REQUIRED_COLUMNS,
    LAYER2_REQUIRED_FILES,
    AlignmentInfo,
    FrameRangeInfo,
    Layer1Bundle,
    Layer2Bundle,
    SessionIdentity,
    ValidationCheck,
    ValidationResult,
    missing_columns,
    validate_columns,
)

# Integrity audit checks that should block if they fail
CRITICAL_INTEGRITY_CHECKS = frozenset(
    {
        "analysis_clean_nan_when_ineligible",
        "no_duplicate_frame_link_rows",
        "excluded_links_not_analysis_eligible",
        "review_links_not_silently_core",
        "link_manifest_joins_to_parquet",
    }
)


def _file_fingerprint(path: Path) -> str:
    stat = path.stat()
    payload = f"{path}|{stat.st_size}|{stat.st_mtime_ns}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def capture_input_fingerprints(l1: Layer1Bundle, l2: Layer2Bundle) -> dict[str, str]:
    """Capture size/mtime fingerprints for input files (mutation detection)."""
    fingerprints: dict[str, str] = {}
    for label, bundle in (("layer1", l1), ("layer2", l2)):
        for name, path in bundle.source_paths.items():
            fingerprints[f"{label}:{name}"] = _file_fingerprint(path)
    return fingerprints


def verify_input_fingerprints(
    l1: Layer1Bundle,
    l2: Layer2Bundle,
    before: dict[str, str],
) -> ValidationCheck:
    after = capture_input_fingerprints(l1, l2)
    changed = [k for k in before if before.get(k) != after.get(k)]
    if changed:
        return ValidationCheck(
            check_name="input_files_not_modified",
            status="fail",
            details=f"Input files changed during validation: {', '.join(sorted(changed))}",
        )
    return ValidationCheck(
        check_name="input_files_not_modified",
        status="pass",
        details=f"Verified {len(before)} input file fingerprints unchanged",
    )


def validate_layer1_contract(bundle: Layer1Bundle) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []

    for name in LAYER1_REQUIRED_FILES:
        path = bundle.source_dir / name
        checks.append(
            ValidationCheck(
                check_name=f"layer1_required_file_{name}",
                status="pass" if path.exists() else "fail",
                details=str(path),
            )
        )

    missing_keys = [k for k in LAYER1_MANIFEST_REQUIRED_KEYS if k not in bundle.manifest]
    checks.append(
        ValidationCheck(
            check_name="layer1_manifest_required_keys",
            status="fail" if missing_keys else "pass",
            details=(
                f"Missing keys: {', '.join(missing_keys)}"
                if missing_keys
                else "All required manifest keys present"
            ),
        )
    )

    col_errors = validate_columns(bundle.qc_mask, LAYER1_QC_MASK_REQUIRED_COLUMNS, "qc_mask")
    checks.append(
        ValidationCheck(
            check_name="layer1_qc_mask_required_columns",
            status="fail" if col_errors else "pass",
            details=col_errors[0] if col_errors else "frame, status present",
        )
    )

    missing_expected = missing_columns(bundle.qc_mask, LAYER1_QC_MASK_EXPECTED_COLUMNS)
    if missing_expected:
        checks.append(
            ValidationCheck(
                check_name="layer1_qc_mask_expected_columns",
                status="warn",
                details=f"Optional expected columns missing: {', '.join(missing_expected)}",
            )
        )
    else:
        checks.append(
            ValidationCheck(
                check_name="layer1_qc_mask_expected_columns",
                status="pass",
                details="All expected qc_mask columns present",
            )
        )

    return checks


def validate_layer2_contract(bundle: Layer2Bundle) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []

    for name in LAYER2_REQUIRED_FILES:
        path = bundle.source_dir / name
        checks.append(
            ValidationCheck(
                check_name=f"layer2_required_file_{name}",
                status="pass" if path.exists() else "fail",
                details=str(path),
            )
        )

    col_errors = validate_columns(
        bundle.parquet_df, LAYER2_PARQUET_REQUIRED_COLUMNS, "layer2_parquet"
    )
    checks.append(
        ValidationCheck(
            check_name="layer2_parquet_required_columns",
            status="fail" if col_errors else "pass",
            details=col_errors[0] if col_errors else "All required parquet columns present",
        )
    )

    missing_expected = missing_columns(bundle.parquet_df, LAYER2_PARQUET_EXPECTED_COLUMNS)
    if missing_expected:
        checks.append(
            ValidationCheck(
                check_name="layer2_parquet_expected_columns",
                status="warn",
                details=(
                    f"Optional expected columns missing: {', '.join(missing_expected)}; "
                    "frame-based operation with reconstructed time allowed"
                ),
            )
        )
    else:
        checks.append(
            ValidationCheck(
                check_name="layer2_parquet_expected_columns",
                status="pass",
                details="time_sec present",
            )
        )

    manifest_errors = validate_columns(
        bundle.link_manifest, LAYER2_LINK_MANIFEST_REQUIRED_COLUMNS, "layer2_link_manifest"
    )
    checks.append(
        ValidationCheck(
            check_name="layer2_link_manifest_required_columns",
            status="fail" if manifest_errors else "pass",
            details=(
                manifest_errors[0]
                if manifest_errors
                else "All required link manifest columns present"
            ),
        )
    )

    dup_count = int(bundle.parquet_df.duplicated(subset=["frame", "link_id"]).sum())
    checks.append(
        ValidationCheck(
            check_name="layer2_no_duplicate_frame_link_rows",
            status="fail" if dup_count else "pass",
            details=f"duplicate_rows={dup_count}",
        )
    )

    return checks


def detect_layer1_frame_range(bundle: Layer1Bundle) -> FrameRangeInfo:
    frame_col = bundle.manifest.get("frame_index_column", "frame")
    time_col = bundle.manifest.get("time_column", "time_s")
    df = bundle.qc_mask

    start_frame = int(df[frame_col].min())
    end_frame = int(df[frame_col].max())
    n_frames = int(end_frame - start_frame + 1)

    time_source = "observed"
    start_time: float | None = None
    end_time: float | None = None

    if time_col in df.columns:
        start_time = float(df[time_col].min())
        end_time = float(df[time_col].max())
    else:
        frame_rate = float(bundle.manifest.get("frame_rate_hz", 120.0))
        start_time = start_frame / frame_rate
        end_time = end_frame / frame_rate
        time_source = "reconstructed"

    return FrameRangeInfo(
        start_frame=start_frame,
        end_frame=end_frame,
        n_frames=n_frames,
        start_time_sec=start_time,
        end_time_sec=end_time,
        time_source=time_source,
    )


def detect_layer2_frame_range(bundle: Layer2Bundle) -> FrameRangeInfo:
    df = bundle.parquet_df
    start_frame = int(df["frame"].min())
    end_frame = int(df["frame"].max())
    n_frames = int(end_frame - start_frame + 1)

    time_source = "observed"
    start_time: float | None = None
    end_time: float | None = None

    if "time_sec" in df.columns:
        start_time = float(df["time_sec"].min())
        end_time = float(df["time_sec"].max())
    else:
        frame_rate = float(bundle.summary.get("sampling_rate_hz", 120.0))
        start_time = start_frame / frame_rate
        end_time = end_frame / frame_rate
        time_source = "reconstructed"

    return FrameRangeInfo(
        start_frame=start_frame,
        end_frame=end_frame,
        n_frames=n_frames,
        start_time_sec=start_time,
        end_time_sec=end_time,
        time_source=time_source,
    )


def resolve_session_identity(
    l1: Layer1Bundle,
    l2: Layer2Bundle,
    force: bool = False,
) -> tuple[SessionIdentity, list[ValidationCheck]]:
    checks: list[ValidationCheck] = []
    l1_run_key = str(l1.manifest["run_key"])
    l2_session_id = str(l2.summary["session_id"])
    l2_run_label = str(l2.summary["run_label"])

    # Explicitly document that run_label is NOT the Layer 1 identity key
    if l1_run_key == l2_run_label:
        checks.append(
            ValidationCheck(
                check_name="run_label_not_used_as_layer1_identity_key",
                status="warn",
                details=(
                    "Layer1 run_key equals Layer2 run_label (unusual); "
                    "identity match should use run_key == session_id, not run_label"
                ),
            )
        )
    else:
        checks.append(
            ValidationCheck(
                check_name="run_label_not_used_as_layer1_identity_key",
                status="pass",
                details=(
                    f"Layer1 run_key ({l1_run_key}) != Layer2 run_label ({l2_run_label}); "
                    "identity resolved via run_key == session_id"
                ),
            )
        )

    identity_match = l1_run_key == l2_session_id
    identity_override = False

    if identity_match:
        checks.append(
            ValidationCheck(
                check_name="session_identity_run_key_equals_session_id",
                status="pass",
                details=f"Layer1 run_key={l1_run_key} == Layer2 session_id={l2_session_id}",
            )
        )
    elif force:
        identity_override = True
        checks.append(
            ValidationCheck(
                check_name="session_identity_run_key_equals_session_id",
                status="warn",
                details=(
                    f"Identity mismatch overridden: Layer1 run_key={l1_run_key} != "
                    f"Layer2 session_id={l2_session_id}; identity_override=true"
                ),
            )
        )
    else:
        checks.append(
            ValidationCheck(
                check_name="session_identity_run_key_equals_session_id",
                status="fail",
                details=(
                    f"Layer1 run_key={l1_run_key} != Layer2 session_id={l2_session_id}; "
                    "use --force to override (logged in metadata)"
                ),
            )
        )

    session_key = l2_session_id if identity_match or force else l1_run_key

    identity = SessionIdentity(
        session_key=session_key,
        layer1_run_key=l1_run_key,
        layer2_session_id=l2_session_id,
        layer2_run_label=l2_run_label,
        layer1_subject_id=l1.manifest.get("subject_id"),
        layer1_session_id=l1.manifest.get("session_id"),
        skeleton_template=l2.summary.get("skeleton_template"),
        identity_override=identity_override,
    )
    return identity, checks


def validate_frame_alignment(
    l1_range: FrameRangeInfo,
    l2_range: FrameRangeInfo,
    l1_manifest_n_frames: int | None = None,
    l2_summary_frame_count: int | None = None,
) -> tuple[AlignmentInfo, list[ValidationCheck]]:
    checks: list[ValidationCheck] = []
    overlap_start = max(l1_range.start_frame, l2_range.start_frame)
    overlap_end = min(l1_range.end_frame, l2_range.end_frame)
    overlap_n = max(0, overlap_end - overlap_start + 1)

    exact = (
        l1_range.start_frame == l2_range.start_frame
        and l1_range.end_frame == l2_range.end_frame
        and l1_range.n_frames == l2_range.n_frames
    )
    frame_mismatch = not exact

    alignment = AlignmentInfo(
        canonical_join_key=CANONICAL_JOIN_KEY,
        layer1_frame_range=l1_range,
        layer2_frame_range=l2_range,
        overlap_start_frame=overlap_start,
        overlap_end_frame=overlap_end,
        overlap_n_frames=overlap_n,
        exact_frame_alignment=exact,
        frame_range_mismatch=frame_mismatch,
    )

    checks.append(
        ValidationCheck(
            check_name="canonical_join_key_is_frame",
            status="pass",
            details=f"Canonical join key: {CANONICAL_JOIN_KEY} (not floating-point time)",
        )
    )

    checks.append(
        ValidationCheck(
            check_name="layer1_frame_range_detected",
            status="pass",
            details=(
                f"frames {l1_range.start_frame}..{l1_range.end_frame}, "
                f"n={l1_range.n_frames}, time_source={l1_range.time_source}"
            ),
        )
    )

    checks.append(
        ValidationCheck(
            check_name="layer2_frame_range_detected",
            status="pass",
            details=(
                f"frames {l2_range.start_frame}..{l2_range.end_frame}, "
                f"n={l2_range.n_frames}, time_source={l2_range.time_source}"
            ),
        )
    )

    if l1_manifest_n_frames is not None and l1_manifest_n_frames != l1_range.n_frames:
        checks.append(
            ValidationCheck(
                check_name="layer1_manifest_frame_count_consistency",
                status="warn",
                details=(
                    f"manifest n_frames={l1_manifest_n_frames} != "
                    f"detected n={l1_range.n_frames}"
                ),
            )
        )

    if l2_summary_frame_count is not None and l2_summary_frame_count != l2_range.n_frames:
        checks.append(
            ValidationCheck(
                check_name="layer2_summary_frame_count_consistency",
                status="warn",
                details=(
                    f"summary frame_count={l2_summary_frame_count} != "
                    f"detected n={l2_range.n_frames}"
                ),
            )
        )

    if overlap_n <= 0:
        checks.append(
            ValidationCheck(
                check_name="frame_range_overlap",
                status="fail",
                details="Layer 1 and Layer 2 frame ranges do not overlap",
            )
        )
        alignment.alignment_uncertainty = "no_overlap"
    elif exact:
        checks.append(
            ValidationCheck(
                check_name="frame_range_overlap",
                status="pass",
                details=f"Exact frame alignment: {overlap_start}..{overlap_end}, n={overlap_n}",
            )
        )
        checks.append(
            ValidationCheck(
                check_name="exact_frame_alignment",
                status="pass",
                details=f"Layer1 and Layer2 frames match exactly: 0..{overlap_end}, n={overlap_n}",
            )
        )
    else:
        checks.append(
            ValidationCheck(
                check_name="frame_range_overlap",
                status="warn",
                details=(
                    f"Frame ranges differ; analysis restricted to overlap "
                    f"{overlap_start}..{overlap_end}, n={overlap_n}"
                ),
            )
        )
        alignment.alignment_uncertainty = "frame_range_mismatch"

    # Time comparison for display/drift warning only
    if (
        l1_range.start_time_sec is not None
        and l2_range.start_time_sec is not None
        and l1_range.end_time_sec is not None
        and l2_range.end_time_sec is not None
    ):
        start_drift = abs(l1_range.start_time_sec - l2_range.start_time_sec)
        end_drift = abs(l1_range.end_time_sec - l2_range.end_time_sec)
        max_drift = max(start_drift, end_drift)
        frame_period = 1.0 / 120.0
        if max_drift > frame_period:
            alignment.time_drift_warning = True
            alignment.time_drift_seconds = max_drift
            checks.append(
                ValidationCheck(
                    check_name="time_range_drift_warning",
                    status="warn",
                    details=(
                        f"Time drift {max_drift:.6f}s exceeds one frame period "
                        f"(display only; frame is canonical join key)"
                    ),
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    check_name="time_range_drift_warning",
                    status="pass",
                    details=(
                        f"Time ranges consistent within one frame period "
                        f"(max drift {max_drift:.6f}s)"
                    ),
                )
            )

    return alignment, checks


def validate_link_manifest_join(l2: Layer2Bundle) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    parquet_keys = l2.parquet_df[["run_label", "link_id"]].drop_duplicates()
    manifest_keys = l2.link_manifest[["run_label", "link_id"]].drop_duplicates()

    parquet_set = set(map(tuple, parquet_keys.to_numpy()))
    manifest_set = set(map(tuple, manifest_keys.to_numpy()))

    parquet_only = sorted(parquet_set - manifest_set)
    manifest_only = sorted(manifest_set - parquet_set)

    if parquet_only or manifest_only:
        checks.append(
            ValidationCheck(
                check_name="layer2_link_manifest_join_run_label_link_id",
                status="fail",
                details=(
                    f"Join by (run_label, link_id) incomplete: "
                    f"parquet_only={parquet_only[:5]}{'...' if len(parquet_only) > 5 else ''}; "
                    f"manifest_only={manifest_only[:5]}{'...' if len(manifest_only) > 5 else ''}"
                ),
            )
        )
    else:
        checks.append(
            ValidationCheck(
                check_name="layer2_link_manifest_join_run_label_link_id",
                status="pass",
                details=(
                    f"Link manifest joins to parquet on (run_label, link_id): "
                    f"{len(parquet_set)} links matched"
                ),
            )
        )

    # Guard: never join by link_id alone (informational pass)
    link_ids_parquet = set(l2.parquet_df["link_id"].unique())
    link_ids_manifest = set(l2.link_manifest["link_id"].unique())
    if link_ids_parquet == link_ids_manifest:
        checks.append(
            ValidationCheck(
                check_name="link_id_alone_insufficient_documented",
                status="pass",
                details="Join validated on (run_label, link_id); link_id alone is not used",
            )
        )

    return checks


def check_layer2_integrity_audit(l2: Layer2Bundle) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    if l2.integrity_audit is None or l2.integrity_audit.empty:
        checks.append(
            ValidationCheck(
                check_name="layer2_integrity_audit_present",
                status="warn",
                details="layer2_session_integrity_audit.csv not present; skipping audit checks",
            )
        )
        return checks

    checks.append(
        ValidationCheck(
            check_name="layer2_integrity_audit_present",
            status="pass",
            details=f"Integrity audit loaded: {len(l2.integrity_audit)} checks",
        )
    )

    for _, row in l2.integrity_audit.iterrows():
        check_name = str(row["check_name"])
        status = str(row["status"]).lower()
        details = str(row.get("details", ""))

        if status == "pass":
            check_status: str = "pass"
        elif check_name in CRITICAL_INTEGRITY_CHECKS:
            check_status = "fail"
        else:
            check_status = "warn"

        checks.append(
            ValidationCheck(
                check_name=f"integrity_audit_{check_name}",
                status=check_status,  # type: ignore[arg-type]
                details=details,
            )
        )

    summary_status = str(l2.summary.get("integrity_status", "")).lower()
    if summary_status == "pass":
        checks.append(
            ValidationCheck(
                check_name="layer2_integrity_status_summary",
                status="pass",
                details="summary integrity_status=pass",
            )
        )
    elif summary_status:
        checks.append(
            ValidationCheck(
                check_name="layer2_integrity_status_summary",
                status="warn",
                details=f"summary integrity_status={summary_status}",
            )
        )

    return checks


def check_review_links_not_silently_core(l2: Layer2Bundle) -> ValidationCheck:
    manifest = l2.link_manifest
    review_as_core = manifest[
        (manifest["feature_scope"] == "review_provisional")
        & (manifest["recommended_segmentation_default"] == "candidate_include")
    ]
    if len(review_as_core):
        return ValidationCheck(
            check_name="review_links_not_silently_core",
            status="fail",
            details=f"Review links marked candidate_include: {review_as_core['link_id'].tolist()}",
        )
    return ValidationCheck(
        check_name="review_links_not_silently_core",
        status="pass",
        details="No review_provisional links marked candidate_include",
    )


def check_excluded_links_not_analysis_eligible(l2: Layer2Bundle) -> ValidationCheck:
    df = l2.parquet_df
    if "stage08_analysis_eligible" not in df.columns or "feature_scope" not in df.columns:
        return ValidationCheck(
            check_name="excluded_links_not_analysis_eligible",
            status="warn",
            details="Skipped: required columns missing (contract validation should report)",
        )
    excluded = df["feature_scope"].isin(["excluded_distal", "excluded_toe"])
    bad = df[excluded & df["stage08_analysis_eligible"]]
    if len(bad):
        return ValidationCheck(
            check_name="excluded_links_not_analysis_eligible",
            status="fail",
            details=f"Excluded links with analysis_eligible rows: {len(bad)}",
        )
    return ValidationCheck(
        check_name="excluded_links_not_analysis_eligible",
        status="pass",
        details="No excluded_distal/excluded_toe links marked analysis eligible",
    )


def check_nan_vs_gap_distinction(l2: Layer2Bundle) -> ValidationCheck:
    """Confirm analysis NaNs align with ineligibility (masked-by-policy, not raw gaps)."""
    df = l2.parquet_df
    analysis_col = "rx_filtered_analysis"
    if "stage08_analysis_eligible" not in df.columns:
        return ValidationCheck(
            check_name="analysis_clean_nan_vs_raw_gap_distinction",
            status="warn",
            details=(
                "Skipped: stage08_analysis_eligible missing "
                "(contract validation should report)"
            ),
        )
    ineligible = ~df["stage08_analysis_eligible"]
    if analysis_col not in df.columns:
        return ValidationCheck(
            check_name="analysis_clean_nan_vs_raw_gap_distinction",
            status="warn",
            details=f"Skipped: missing column {analysis_col}",
        )

    finite_on_ineligible = df[ineligible & df[analysis_col].notna()]
    if len(finite_on_ineligible):
        return ValidationCheck(
            check_name="analysis_clean_nan_vs_raw_gap_distinction",
            status="fail",
            details=(
                f"{len(finite_on_ineligible)} ineligible rows have finite analysis values "
                "(should be NaN masked-by-policy)"
            ),
        )

    nan_on_ineligible = df[ineligible & df[analysis_col].isna()]
    return ValidationCheck(
        check_name="analysis_clean_nan_vs_raw_gap_distinction",
        status="pass",
        details=(
            f"Analysis-clean NaNs ({len(nan_on_ineligible)} ineligible rows) are "
            "masked-by-policy (stage08_analysis_eligible=false), distinct from Layer 1 raw gaps"
        ),
    )


def run_all_validations(
    l1: Layer1Bundle,
    l2: Layer2Bundle,
    force: bool = False,
) -> ValidationResult:
    """Run full validation suite; returns structured result."""
    result = ValidationResult()
    result.input_fingerprints = capture_input_fingerprints(l1, l2)

    for check in validate_layer1_contract(l1):
        result.add_check(check)
    for check in validate_layer2_contract(l2):
        result.add_check(check)

    identity, identity_checks = resolve_session_identity(l1, l2, force=force)
    result.identity = identity
    for check in identity_checks:
        result.add_check(check)

    l1_range = detect_layer1_frame_range(l1)
    l2_range = detect_layer2_frame_range(l2)
    alignment, alignment_checks = validate_frame_alignment(
        l1_range,
        l2_range,
        l1_manifest_n_frames=(
            int(l1.manifest.get("n_frames")) if "n_frames" in l1.manifest else None
        ),
        l2_summary_frame_count=int(l2.summary.get("frame_count"))
        if "frame_count" in l2.summary
        else None,
    )
    result.alignment = alignment
    for check in alignment_checks:
        result.add_check(check)

    for check in validate_link_manifest_join(l2):
        result.add_check(check)

    for check in check_layer2_integrity_audit(l2):
        result.add_check(check)

    result.add_check(check_review_links_not_silently_core(l2))
    result.add_check(check_excluded_links_not_analysis_eligible(l2))
    result.add_check(check_nan_vs_gap_distinction(l2))

    for w in l1.warnings + l2.warnings:
        result.warnings.append(f"load_warning: {w}")

    result.add_check(verify_input_fingerprints(l1, l2, result.input_fingerprints))
    result.finalize()
    return result


def validation_result_to_summary_dict(result: ValidationResult) -> dict:
    """Serialize ValidationResult to JSON-friendly dict."""
    identity = result.identity
    alignment = result.alignment

    return {
        "safe_to_open": result.safe_to_open,
        "blocking_errors": result.blocking_errors,
        "warnings": result.warnings,
        "identity": {
            "session_key": identity.session_key if identity else None,
            "layer1_run_key": identity.layer1_run_key if identity else None,
            "layer2_session_id": identity.layer2_session_id if identity else None,
            "layer2_run_label": identity.layer2_run_label if identity else None,
            "identity_override": identity.identity_override if identity else False,
        },
        "alignment": {
            "canonical_join_key": alignment.canonical_join_key if alignment else CANONICAL_JOIN_KEY,
            "exact_frame_alignment": alignment.exact_frame_alignment if alignment else None,
            "frame_range_mismatch": alignment.frame_range_mismatch if alignment else None,
            "layer1_frames": (
                {
                    "start": alignment.layer1_frame_range.start_frame,
                    "end": alignment.layer1_frame_range.end_frame,
                    "n": alignment.layer1_frame_range.n_frames,
                    "time_source": alignment.layer1_frame_range.time_source,
                }
                if alignment and alignment.layer1_frame_range
                else None
            ),
            "layer2_frames": (
                {
                    "start": alignment.layer2_frame_range.start_frame,
                    "end": alignment.layer2_frame_range.end_frame,
                    "n": alignment.layer2_frame_range.n_frames,
                    "time_source": alignment.layer2_frame_range.time_source,
                }
                if alignment and alignment.layer2_frame_range
                else None
            ),
            "overlap": (
                {
                    "start": alignment.overlap_start_frame,
                    "end": alignment.overlap_end_frame,
                    "n": alignment.overlap_n_frames,
                }
                if alignment
                else None
            ),
            "time_drift_warning": alignment.time_drift_warning if alignment else False,
            "alignment_uncertainty": alignment.alignment_uncertainty if alignment else None,
        },
        "n_checks": len(result.checks),
        "n_pass": sum(1 for c in result.checks if c.status == "pass"),
        "n_warn": sum(1 for c in result.checks if c.status == "warn"),
        "n_fail": sum(1 for c in result.checks if c.status == "fail"),
    }


def write_validation_outputs(result: ValidationResult, out_dir: str | Path) -> Path:
    """Write validation_report.md, validation_summary.json, validation_checks.csv."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # CSV checks
    checks_df = pd.DataFrame(
        [
            {"check_name": c.check_name, "status": c.status, "details": c.details}
            for c in result.checks
        ]
    )
    checks_df.to_csv(out_path / "validation_checks.csv", index=False)

    # JSON summary
    summary = validation_result_to_summary_dict(result)
    with (out_path / "validation_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    # Markdown report
    report_lines = [
        "# Segmentation Input Validation Report",
        "",
        f"**Verdict:** {'SAFE TO OPEN' if result.safe_to_open else 'BLOCKED'}",
        "",
        "## Session identity",
        "",
    ]
    if result.identity:
        ident = result.identity
        report_lines.extend(
            [
                f"- Layer 1 run_key: `{ident.layer1_run_key}`",
                f"- Layer 2 session_id: `{ident.layer2_session_id}`",
                f"- Layer 2 run_label: `{ident.layer2_run_label}`",
                f"- Session key: `{ident.session_key}`",
                f"- Identity override: `{ident.identity_override}`",
                "",
            ]
        )

    report_lines.extend(["## Frame alignment", ""])
    if result.alignment:
        al = result.alignment
        if al.layer1_frame_range:
            r = al.layer1_frame_range
            report_lines.append(
                f"- Layer 1 frames: {r.start_frame}..{r.end_frame}, n={r.n_frames} "
                f"(time_source={r.time_source})"
            )
        if al.layer2_frame_range:
            r = al.layer2_frame_range
            report_lines.append(
                f"- Layer 2 frames: {r.start_frame}..{r.end_frame}, n={r.n_frames} "
                f"(time_source={r.time_source})"
            )
        report_lines.extend(
            [
                f"- Canonical join key: `{al.canonical_join_key}`",
                f"- Exact frame alignment: `{al.exact_frame_alignment}`",
                f"- Frame range mismatch: `{al.frame_range_mismatch}`",
                f"- Overlap: {al.overlap_start_frame}..{al.overlap_end_frame}, "
                f"n={al.overlap_n_frames}",
                "",
            ]
        )

    if result.blocking_errors:
        report_lines.extend(["## Blocking errors", ""])
        for err in result.blocking_errors:
            report_lines.append(f"- {err}")
        report_lines.append("")

    if result.warnings:
        report_lines.extend(["## Warnings", ""])
        for warn in result.warnings:
            report_lines.append(f"- {warn}")
        report_lines.append("")

    report_lines.extend(["## Validation checks", ""])
    report_lines.append("| Check | Status | Details |")
    report_lines.append("|---|---|---|")
    for c in result.checks:
        details = c.details.replace("|", "\\|").replace("\n", " ")
        report_lines.append(f"| {c.check_name} | {c.status} | {details} |")

    report_lines.extend(
        [
            "",
            "## Notebook readiness",
            "",
            (
                "This session **is safe to open** in the segmentation notebook."
                if result.safe_to_open
                else (
                    "This session **must not** be opened for segmentation "
                    "until blocking errors are resolved."
                )
            ),
            "",
        ]
    )

    (out_path / "validation_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    return out_path
