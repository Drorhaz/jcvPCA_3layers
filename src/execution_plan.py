"""G5 dry-run execution planning — request-to-runner translation (no execution)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise ImportError("execution_plan requires PyYAML") from exc

from analysis_request import (
    LEVEL_ADVISORY,
    LEVEL_ERROR,
    LEVEL_WARNING,
    STATUS_BLOCKED,
    STATUS_READY,
    STATUS_VALIDATED,
    AnalysisRequestInput,
    ComparisonSpecInput,
    ValidationMessage,
    comparison_spec_from_preset,
    validate_analysis_request,
)
from project_status import ProjectSnapshot, REGISTRY_COVERAGE

EXECUTION_PLAN_VERSION = "G5"
DEFAULT_PLANS_DIR = Path("requests") / "execution_plans"

# Batch-level artifact classes (mirrors gaga_batch_runner output layout).
BATCH_ARTIFACT_CLASSES: tuple[str, ...] = (
    "batch_manifest",
    "batch_summary",
    "comparison_plan",
    "comparison_status",
    "comparison_status_by_focus",
    "data_availability_report",
    "dataset_construction_by_comparison",
    "preflight_by_comparison",
    "pca_stability_by_comparison",
    "selected_m_by_comparison",
    "pc_focus_by_comparison",
    "pc_focus_sensitivity_results",
    "null_space_availability_report",
    "comparable_links_by_comparison",
    "excluded_links_by_comparison",
    "jcvpca_link_results",
    "jcvpca_axis_results",
    "jcvpca_link_results_by_pc_focus",
    "jcvpca_axis_results_by_pc_focus",
    "nv_baseline_results",
    "exploratory_summary_results",
    "plot_index",
    "workbench_export_manifest",
    "comparison_run_directories",
    "comparison_plots",
    "config_snapshot",
)

REQUEST_PC_FOCUS_TO_RUNNER: dict[str, str] = {
    "all": "all",
    "functional": "functional_p2",
    "null_space": "null_space_p2",
}

RUNNER_ENTRYPOINT = "Layer3_JcvPCA/scripts/run_gaga_batch_jcvpca.py"
RUNNER_MODULE = "layer3_jcvpca.gaga_batch_runner"
BATCH_ID_PREFIX = "gaga_batch_jcvpca_"


@dataclass
class PreflightMessage:
    level: str
    code: str
    message: str
    source: str
    field: str = ""


@dataclass
class PreflightResult:
    blockers: list[PreflightMessage] = field(default_factory=list)
    warnings: list[PreflightMessage] = field(default_factory=list)
    advisory_notes: list[PreflightMessage] = field(default_factory=list)

    @property
    def has_blockers(self) -> bool:
        return bool(self.blockers)


def _msg_dict(msg: PreflightMessage | ValidationMessage) -> dict[str, str]:
    d = asdict(msg)
    return {k: v for k, v in d.items() if v}


def parse_request_to_input(request: dict[str, Any]) -> AnalysisRequestInput:
    """Reconstruct AnalysisRequestInput from a saved analysis_request.yaml."""
    selection = request.get("selection") or {}
    blocks = selection.get("blocks") or {}
    outputs = request.get("outputs") or {}
    link_focus = request.get("link_focus") or {}

    comparisons: list[ComparisonSpecInput] = []
    default_reps = tuple(selection.get("repetitions") or ("R1", "R2"))
    for comp in request.get("comparisons") or []:
        cid = str(comp.get("comparison_id", ""))
        ctype = str(comp.get("comparison_type", "longitudinal"))
        if ctype == "longitudinal":
            comparisons.append(
                ComparisonSpecInput(
                    comparison_id=cid,
                    comparison_type=ctype,
                    comparison_label=str(comp.get("comparison_label") or cid),
                    timepoint_a=str(comp.get("timepoint_a") or ""),
                    timepoint_b=str(comp.get("timepoint_b") or ""),
                    repetitions=tuple(comp.get("repetitions") or default_reps),
                )
            )
        else:
            comparisons.append(
                ComparisonSpecInput(
                    comparison_id=cid,
                    comparison_type=ctype,
                    comparison_label=str(comp.get("comparison_label") or cid),
                    timepoint=str(comp.get("timepoint") or ""),
                    repetition_a=str(comp.get("repetition_a") or "R1"),
                    repetition_b=str(comp.get("repetition_b") or "R2"),
                )
            )

    return AnalysisRequestInput(
        participant_id=str(selection.get("participant_id") or ""),
        p_phases=tuple(selection.get("p_phases") or ()),
        repetitions=default_reps,
        comparisons=comparisons,
        segment_preset=selection.get("segment_preset"),
        block_a=tuple(blocks.get("A") or ()) or None,
        block_b=tuple(blocks.get("B") or ()) or None,
        pc_focus_spaces=tuple(outputs.get("pc_focus_spaces") or ("all", "functional", "null_space")),
        generate_comparison_plots=bool(outputs.get("generate_comparison_plots", True)),
        generate_full_numeric_reports=str(outputs.get("generate_full_numeric_reports") or "on_demand"),
        generate_poster_package=str(outputs.get("generate_poster_package") or "on_demand"),
        body_regions=tuple(link_focus.get("body_regions") or ()),
        link_stems=tuple(link_focus.get("link_stems") or ()),
        use_comparable_links_only=bool(link_focus.get("use_comparable_links_only", True)),
        exercise_selection_mode=str(
            selection.get("exercise_selection_mode") or "gaga_p_phases"
        ),
        selected_exercise_ids=tuple(
            int(x) for x in (selection.get("selected_exercise_ids") or [])
        ),
    )


def _load_runner_helpers() -> dict[str, Any]:
    from layer3_jcvpca.gaga_batch_runner import (
        BLOCK_EXERCISES,
        BLOCK_LABELS,
        FOCUS_LABEL_ALL,
        FOCUS_LABEL_FUNCTIONAL,
        FOCUS_LABEL_NULL_SPACE,
        SENSITIVITY_P,
        TARGET_PARTICIPANTS,
        build_comparison_plan,
        build_comparison_specs,
        default_layer25_root,
    )

    return {
        "BLOCK_EXERCISES": BLOCK_EXERCISES,
        "BLOCK_LABELS": BLOCK_LABELS,
        "FOCUS_LABEL_ALL": FOCUS_LABEL_ALL,
        "FOCUS_LABEL_FUNCTIONAL": FOCUS_LABEL_FUNCTIONAL,
        "FOCUS_LABEL_NULL_SPACE": FOCUS_LABEL_NULL_SPACE,
        "SENSITIVITY_P": SENSITIVITY_P,
        "TARGET_PARTICIPANTS": TARGET_PARTICIPANTS,
        "build_comparison_plan": build_comparison_plan,
        "build_comparison_specs": build_comparison_specs,
        "default_layer25_root": default_layer25_root,
    }


def _runner_spec_dict(spec: Any) -> dict[str, Any]:
    return {
        "comparison_id": spec.comparison_id,
        "comparison_label": spec.comparison_label,
        "analysis_mode": spec.analysis_mode,
        "dataset_a_timepoints": list(spec.dataset_a_timepoints),
        "dataset_a_repetitions": list(spec.dataset_a_repetitions),
        "dataset_b_timepoints": list(spec.dataset_b_timepoints),
        "dataset_b_repetitions": list(spec.dataset_b_repetitions),
        "exploratory_timepoint": spec.exploratory_timepoint,
        "exploratory_repetition_a": spec.exploratory_repetition_a,
        "exploratory_repetition_b": spec.exploratory_repetition_b,
    }


def _resolve_blocks_from_request(
    request: dict[str, Any],
    runner: dict[str, Any],
) -> dict[str, list[str]]:
    selection = request.get("selection") or {}
    blocks = selection.get("blocks") or {}
    default_blocks = runner["BLOCK_EXERCISES"]
    resolved: dict[str, list[str]] = {}
    for block_id in ("A", "B"):
        if block_id in blocks and blocks[block_id]:
            resolved[block_id] = [str(x) for x in blocks[block_id]]
        else:
            resolved[block_id] = list(default_blocks[block_id])
    return resolved


def _map_pc_focus_runs(
    request: dict[str, Any],
    runner: dict[str, Any],
) -> list[dict[str, Any]]:
    outputs = request.get("outputs") or {}
    requested = outputs.get("pc_focus_spaces") or ["all", "functional", "null_space"]
    label_map = {
        "all": (runner["FOCUS_LABEL_ALL"], None),
        "functional": (runner["FOCUS_LABEL_FUNCTIONAL"], runner["SENSITIVITY_P"]),
        "null_space": (runner["FOCUS_LABEL_NULL_SPACE"], runner["SENSITIVITY_P"]),
    }
    runs: list[dict[str, Any]] = []
    for space in requested:
        if space not in label_map:
            continue
        focus_label, p = label_map[space]
        runs.append(
            {
                "request_space": space,
                "runner_focus_label": focus_label,
                "sensitivity_p": p,
            }
        )
    return runs


def translate_request_to_runner_plan(
    snapshot: ProjectSnapshot,
    request: dict[str, Any],
    *,
    proposed_batch_id: str | None = None,
) -> dict[str, Any]:
    """Map validated analysis_request.yaml to Layer 3 gaga_batch_runner concepts."""
    runner = _load_runner_helpers()
    inp = parse_request_to_input(request)
    selection = request.get("selection") or {}
    participant_id = str(selection.get("participant_id") or inp.participant_id)

    all_specs = {s.comparison_id: s for s in runner["build_comparison_specs"]()}
    requested_comparison_ids = [str(c.get("comparison_id")) for c in request.get("comparisons") or []]
    unknown = [cid for cid in requested_comparison_ids if cid not in all_specs]
    known_ids = [cid for cid in requested_comparison_ids if cid in all_specs]

    blocks = _resolve_blocks_from_request(request, runner)
    filtered_specs = [all_specs[cid] for cid in known_ids]

    plan_df = runner["build_comparison_plan"](
        participants=[participant_id],
        blocks=blocks,
        specs=filtered_specs,
    )
    requested_jobs: list[dict[str, Any]] = []
    for _, row in plan_df.iterrows():
        block_id = str(row["block_id"])
        comparison_id = str(row["comparison_id"])
        comp_key = f"{participant_id}_{block_id}_{comparison_id}"
        spec = all_specs[comparison_id]
        block_exercises = blocks[block_id]
        requested_jobs.append(
            {
                "comparison_key": comp_key,
                "participant_id": participant_id,
                "block_id": block_id,
                "block_label": runner["BLOCK_LABELS"].get(block_id, block_id),
                "block_exercises": block_exercises,
                "comparison_id": comparison_id,
                "comparison_label": str(row["comparison_label"]),
                "analysis_mode": str(row["analysis_mode"]),
                "runner_spec": _runner_spec_dict(spec),
                "pc_focus_runs": _map_pc_focus_runs(request, runner),
                "comparison_output_dir": f"comparisons/{comp_key}",
                "plot_output_dir": f"plots/{participant_id}/{block_id}/{comparison_id}",
            }
        )

    ts = proposed_batch_id or f"{BATCH_ID_PREFIX}{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    if not ts.startswith(BATCH_ID_PREFIX):
        ts = f"{BATCH_ID_PREFIX}{ts}"
    batch_root = snapshot.paths.get("layer3.outputs_root") / ts

    layer25_root = runner["default_layer25_root"]()
    if not layer25_root.is_absolute():
        layer25_root = (snapshot.project_root / layer25_root).resolve()

    current_runner_defaults = runner["build_comparison_plan"](
        participants=[participant_id],
    )
    default_job_count = len(current_runner_defaults)

    compatibility_gaps: list[dict[str, str]] = [
        {
            "code": "runner_runs_all_comparisons",
            "message": (
                "Current gaga_batch_runner executes all build_comparison_specs() "
                f"({len(all_specs)} comparisons × 2 blocks), not only the "
                f"{len(known_ids)} comparison(s) in this request."
            ),
        },
        {
            "code": "runner_fixed_pc_focus",
            "message": (
                "Current runner always runs all, functional_p2, and null_space_p2 "
                "focus modes (p=2); request pc_focus_spaces are advisory until G6."
            ),
        },
        {
            "code": "runner_no_request_yaml",
            "message": (
                "Current runner does not consume analysis_request.yaml; "
                "mapping is compatibility documentation only."
            ),
        },
    ]
    if participant_id not in snapshot.participants:
        compatibility_gaps.append(
            {
                "code": "participant_not_discovered",
                "message": (
                    f"Participant {participant_id} is not in the discovered cohort "
                    f"{list(snapshot.participants)}. Run Stage 1 discovery after adding data."
                ),
            }
        )
    elif participant_id not in runner["TARGET_PARTICIPANTS"]:
        compatibility_gaps.append(
            {
                "code": "runner_python_defaults_stale",
                "message": (
                    f"Participant {participant_id} is discovered and will run via --participant; "
                    f"Layer 3 Python TARGET_PARTICIPANTS={list(runner['TARGET_PARTICIPANTS'])} "
                    "is informational only."
                ),
            }
        )

    return {
        "entrypoint": RUNNER_ENTRYPOINT,
        "runner_module": RUNNER_MODULE,
        "layer25_root": str(layer25_root),
        "central_manifest": str(layer25_root / "layer25_export_manifest.csv"),
        "participant_ids": [participant_id],
        "target_participants_default": list(snapshot.participants),
        "discovered_participants": list(snapshot.participants),
        "blocks": blocks,
        "block_labels": dict(runner["BLOCK_LABELS"]),
        "requested_comparison_ids": known_ids,
        "unknown_comparison_ids": unknown,
        "requested_job_count": len(requested_jobs),
        "current_runner_default_job_count": default_job_count,
        "requested_jobs": requested_jobs,
        "proposed_batch_id": ts,
        "proposed_batch_root": str(batch_root),
        "batch_id_convention": f"{BATCH_ID_PREFIX}<UTC_YYYYMMDD_HHMMSS>",
        "invocation_preview": {
            "command": (
                f"python {RUNNER_ENTRYPOINT} "
                f"--participant {participant_id} "
                f"--output-dir {batch_root}"
            ),
            "note": "Preview only — G5 does not execute this command.",
        },
        "compatibility_gaps": compatibility_gaps,
        "resolved_segments": request.get("resolved_segments") or [],
        "input_files": _collect_input_files(request),
    }


def _collect_input_files(request: dict[str, Any]) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    seen: set[str] = set()
    for seg in request.get("resolved_segments") or []:
        for key in ("matrix_path", "manifest_path"):
            path = str(seg.get(key) or "")
            if path and path not in seen:
                seen.add(path)
                files.append({"path": path, "role": key, "segment_id": str(seg.get("segment_id", ""))})
    return files


def run_preflight_checks(
    snapshot: ProjectSnapshot,
    request: dict[str, Any],
    *,
    request_path: Path | None = None,
    proposed_batch_root: Path | None = None,
) -> PreflightResult:
    """Preflight for dry-run planning; separates blockers, warnings, advisory."""
    result = PreflightResult()
    status = str(request.get("status") or "")
    if status == STATUS_BLOCKED:
        result.blockers.append(
            PreflightMessage(
                LEVEL_ERROR,
                "request_blocked",
                "Request status is blocked; resolve G4 validation errors first.",
                "g4_request",
                field="status",
            )
        )
    elif status not in {STATUS_VALIDATED, STATUS_READY}:
        result.warnings.append(
            PreflightMessage(
                LEVEL_WARNING,
                "request_not_validated",
                f"Request status is '{status}'; dry-run assumes validated intent.",
                "g4_request",
                field="status",
            )
        )

    prov = request.get("provenance") or {}
    req_hash = str(prov.get("science_hash") or "")
    cur_hash = snapshot.config.science_hash
    if req_hash and req_hash != cur_hash:
        result.blockers.append(
            PreflightMessage(
                LEVEL_ERROR,
                "science_hash_mismatch",
                "Request science_hash differs from current config registry.",
                "provenance",
                field="provenance.science_hash",
            )
        )
    elif not req_hash:
        result.warnings.append(
            PreflightMessage(
                LEVEL_WARNING,
                "missing_science_hash",
                "Request has no frozen science_hash; provenance incomplete.",
                "provenance",
            )
        )

    req_display = str(prov.get("display_hash") or "")
    if req_display and req_display != snapshot.config.display_hash:
        result.warnings.append(
            PreflightMessage(
                LEVEL_WARNING,
                "display_hash_mismatch",
                "Display hash changed since request save (GUI-only; does not block science).",
                "provenance",
                field="provenance.display_hash",
            )
        )

    inp = parse_request_to_input(request)
    messages, validation_payload = validate_analysis_request(
        snapshot,
        inp,
        check_comparable_links=True,
    )
    for msg in messages:
        target = (
            result.blockers
            if msg.level == LEVEL_ERROR
            else result.warnings
            if msg.level == LEVEL_WARNING
            else result.advisory_notes
        )
        if msg.code == "no_execution_g4":
            continue
        target.append(
            PreflightMessage(
                msg.level,
                msg.code,
                msg.message,
                msg.source,
                field=msg.field,
            )
        )

    for fin in _collect_input_files(request):
        p = Path(fin["path"])
        if not p.is_file():
            result.blockers.append(
                PreflightMessage(
                    LEVEL_ERROR,
                    "input_file_missing",
                    f"Missing {fin['role']}: {fin['path']}",
                    "filesystem",
                    field="resolved_segments",
                )
            )

    central = snapshot.paths.layer2_5_pre_jvcpca_review
    manifest_path = central / "layer25_export_manifest.csv"
    if not manifest_path.is_file():
        result.blockers.append(
            PreflightMessage(
                LEVEL_ERROR,
                "central_manifest_missing",
                f"Layer 2.5 manifest not found: {manifest_path}",
                "filesystem",
            )
        )

    batch_root = proposed_batch_root
    if batch_root is None:
        batch_root = Path(
            translate_request_to_runner_plan(snapshot, request)["proposed_batch_root"]
        )
    canonical = snapshot.canonical_batch_path
    if canonical and batch_root.resolve() == canonical.resolve():
        result.blockers.append(
            PreflightMessage(
                LEVEL_ERROR,
                "canonical_batch_guard",
                f"Proposed output path matches canonical batch: {canonical}",
                "paths",
            )
        )
    if snapshot.canonical_batch_id and batch_root.name == snapshot.canonical_batch_id:
        result.blockers.append(
            PreflightMessage(
                LEVEL_ERROR,
                "canonical_batch_id_guard",
                f"Proposed batch_id matches canonical: {snapshot.canonical_batch_id}",
                "paths",
            )
        )

    result.advisory_notes.append(
        PreflightMessage(
            LEVEL_ADVISORY,
            "no_execution_g5",
            "G5 produces a dry-run plan only — execution remains disabled.",
            "execution",
        )
    )
    if request_path:
        result.advisory_notes.append(
            PreflightMessage(
                LEVEL_ADVISORY,
                "request_source",
                f"Plan derived from {request_path}",
                "provenance",
            )
        )

    _ = validation_payload
    return result


def build_reproducibility_package_spec(
    snapshot: ProjectSnapshot,
    request: dict[str, Any],
    *,
    request_path: Path | None = None,
) -> dict[str, Any]:
    """Define what a future _config_snapshot/ would contain (not written to batches)."""
    prov = request.get("provenance") or {}
    layer25 = snapshot.paths.layer2_5_pre_jvcpca_review
    return {
        "target_directory": "_config_snapshot/",
        "write_policy": "future_guarded_runner_only",
        "would_copy": [
            {
                "artifact": "analysis_request.yaml",
                "source": str(request_path) if request_path else "<request at execution time>",
            },
            {
                "artifact": "execution_plan.yaml",
                "source": "generated at dry-run / pre-execution",
            },
            *[
                {"artifact": fname, "source": str(snapshot.config.config_dir / fname)}
                for fname in (
                    "analysis_params.yaml",
                    "qc_rules.yaml",
                    "segment_selection.yaml",
                    "gui_settings.yaml",
                )
            ],
        ],
        "would_generate": [
            "config_hash.json",
            "runner_metadata.json",
            "source_manifest_references.json",
        ],
        "config_hash_json": {
            "science_hash": snapshot.config.science_hash,
            "display_hash": snapshot.config.display_hash,
            "request_science_hash": prov.get("science_hash"),
            "request_display_hash": prov.get("display_hash"),
            "hash_match": prov.get("science_hash") == snapshot.config.science_hash,
            "config_files": list(
                (
                    "analysis_params.yaml",
                    "qc_rules.yaml",
                    "segment_selection.yaml",
                    "gui_settings.yaml",
                )
            ),
        },
        "registry_coverage": prov.get("registry_coverage")
        or {layer: meta["label"] for layer, meta in REGISTRY_COVERAGE.items()},
        "threshold_registry_note": (
            "Threshold values live in copied YAML files; "
            "analysis_config.py validates bounds at load time."
        ),
        "source_manifest_references": {
            "layer25_export_manifest": str(layer25 / "layer25_export_manifest.csv"),
            "layer25_export_attempts": str(layer25 / "layer25_export_attempts_report.csv"),
            "session_index": str(snapshot.project_root / "processed" / "session_index.csv"),
            "resolved_segment_count": len(request.get("resolved_segments") or []),
        },
        "runner_metadata": {
            "entrypoint": RUNNER_ENTRYPOINT,
            "runner_module": RUNNER_MODULE,
            "execution_plan_version": EXECUTION_PLAN_VERSION,
            "batch_id_convention": f"{BATCH_ID_PREFIX}<UTC_YYYYMMDD_HHMMSS>",
            "execution_allowed": False,
        },
        "explicitly_not_written": [
            str(snapshot.canonical_batch_path) if snapshot.canonical_batch_path else "",
            "existing batch directories under layer3.outputs_root",
        ],
    }


def build_output_plan(
    snapshot: ProjectSnapshot,
    request: dict[str, Any],
    runner_plan: dict[str, Any],
) -> dict[str, Any]:
    """Expected output directory layout and invalidation tags."""
    batch_root = runner_plan["proposed_batch_root"]
    jobs = runner_plan.get("requested_jobs") or []
    comparison_dirs = [j["comparison_output_dir"] for j in jobs]
    plot_dirs = [j["plot_output_dir"] for j in jobs if request.get("outputs", {}).get("generate_comparison_plots")]

    invalidated_classes = sorted(snapshot.config.invalidated_by_changes([]))
    return {
        "proposed_batch_root": batch_root,
        "proposed_batch_id": runner_plan["proposed_batch_id"],
        "batch_level_artifacts": list(BATCH_ARTIFACT_CLASSES),
        "batch_root_files": [
            "batch_manifest.csv",
            "batch_summary.md",
            "comparison_plan.csv",
            "comparison_status.csv",
            "data_availability_report.csv",
            "jcvpca_link_results.csv",
            "jcvpca_axis_results.csv",
            "plot_index.csv",
            "workbench_export_manifest.csv",
        ],
        "comparison_directories": comparison_dirs,
        "plot_directories": plot_dirs,
        "on_demand_outputs": {
            "generate_full_numeric_reports": request.get("outputs", {}).get(
                "generate_full_numeric_reports", "on_demand"
            ),
            "generate_poster_package": request.get("outputs", {}).get(
                "generate_poster_package", "on_demand"
            ),
            "note": "Poster/numeric report generators are not invoked by gaga_batch_runner today.",
        },
        "regenerated_artifact_classes": ["layer3_batches"],
        "unchanged_canonical": {
            "batch_id": snapshot.canonical_batch_id,
            "path": str(snapshot.canonical_batch_path or ""),
            "policy": "never_modify_canonical_batch",
        },
        "config_change_invalidation_classes": invalidated_classes,
    }


def build_execution_plan(
    snapshot: ProjectSnapshot,
    request: dict[str, Any],
    *,
    request_path: Path | None = None,
    proposed_batch_id: str | None = None,
) -> dict[str, Any]:
    """Build full dry-run execution plan from a validated analysis request."""
    now = datetime.now(timezone.utc).isoformat()
    runner_plan = translate_request_to_runner_plan(
        snapshot,
        request,
        proposed_batch_id=proposed_batch_id,
    )
    preflight = run_preflight_checks(
        snapshot,
        request,
        request_path=request_path,
        proposed_batch_root=Path(runner_plan["proposed_batch_root"]),
    )
    output_plan = build_output_plan(snapshot, request, runner_plan)
    repro = build_reproducibility_package_spec(snapshot, request, request_path=request_path)

    plan_status = STATUS_BLOCKED if preflight.has_blockers else STATUS_READY
    if not preflight.has_blockers and preflight.warnings:
        plan_status = STATUS_VALIDATED

    return {
        "version": 1,
        "execution_plan_version": EXECUTION_PLAN_VERSION,
        "plan_id": f"plan_{request.get('request_id', 'unknown')}_{now[:10].replace('-', '')}",
        "created_at": now,
        "source_request_id": request.get("request_id"),
        "source_request_path": str(request_path) if request_path else None,
        "source_request_status": request.get("status"),
        "plan_status": plan_status,
        "execution": {
            "allowed": False,
            "blocker_count": len(preflight.blockers),
            "warning_count": len(preflight.warnings),
            "note": "G5 dry-run only — no Layer 3 analysis executed.",
        },
        "preflight": {
            "blockers": [_msg_dict(m) for m in preflight.blockers],
            "warnings": [_msg_dict(m) for m in preflight.warnings],
            "advisory_notes": [_msg_dict(m) for m in preflight.advisory_notes],
        },
        "runner_translation": runner_plan,
        "output_plan": output_plan,
        "reproducibility_package": repro,
    }


def save_execution_plan(
    project_root: Path,
    plan: dict[str, Any],
    *,
    plans_dir: Path | None = None,
) -> Path:
    """Save dry-run plan YAML under requests/execution_plans/ (explicit save only)."""
    out_dir = (plans_dir or (project_root / DEFAULT_PLANS_DIR)).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    rid = str(plan.get("source_request_id") or plan.get("plan_id", "execution_plan")).replace("/", "_")
    path = out_dir / f"{rid}_execution_plan.yaml"
    plan = dict(plan)
    plan["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(
        yaml.safe_dump(plan, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def load_execution_plan(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data
