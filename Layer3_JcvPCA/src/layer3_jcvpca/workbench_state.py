"""Workbench run state and step status persistence (Phase 6)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STEP_NOT_STARTED = "not_started"
STEP_READY = "ready"
STEP_RUNNING = "running"
STEP_COMPLETED = "completed"
STEP_WARNING = "warning"
STEP_BLOCKING = "blocking"
STEP_INVALIDATED = "invalidated"

STEP_STATUSES: tuple[str, ...] = (
    STEP_NOT_STARTED,
    STEP_READY,
    STEP_RUNNING,
    STEP_COMPLETED,
    STEP_WARNING,
    STEP_BLOCKING,
    STEP_INVALIDATED,
)

STEP_6A_LOAD = "6A_load_dataset"
STEP_6B_RAW_PREVIEW = "6B_raw_preview"
STEP_6C_CENTERING = "6C_independent_centering"
STEP_7A_PCA_A = "7A_pca_on_dataset_a"
STEP_9A_PC_FOCUS = "9A_pc_focus_selection"
STEP_10A_B_PROJECTION = "10A_project_b_into_a"
STEP_11A_PCA_B = "11A_pca_on_projected_b"
STEP_12A_REEXPRESS = "12A_reexpress_b_loadings"
STEP_13A_AXIS_JCVPCA = "13A_axis_level_jcvpca"
STEP_14A_RSS = "14A_rss_link_aggregation"
STEP_15A_WEIGHTING = "15A_explained_variance_weighting"
STEP_16A_NV = "16A_nv_descriptive_baseline"
STEP_17A_EXPLORATORY = "17A_exploratory_summary"
STEP_18A_EXPORT = "18A_export_package"

WORKBENCH_STEP_ORDER: tuple[str, ...] = (
    STEP_6A_LOAD,
    STEP_6B_RAW_PREVIEW,
    STEP_6C_CENTERING,
    STEP_7A_PCA_A,
    STEP_9A_PC_FOCUS,
    STEP_10A_B_PROJECTION,
    STEP_11A_PCA_B,
    STEP_12A_REEXPRESS,
    STEP_13A_AXIS_JCVPCA,
    STEP_14A_RSS,
    STEP_15A_WEIGHTING,
    STEP_16A_NV,
    STEP_17A_EXPLORATORY,
    STEP_18A_EXPORT,
)

# Backward-compatible alias
PHASE6_STEP_ORDER = WORKBENCH_STEP_ORDER[:3]

STEP_DISPLAY_NAMES: dict[str, str] = {
    STEP_6A_LOAD: "Load full constructed dataset",
    STEP_6B_RAW_PREVIEW: "Raw data preview",
    STEP_6C_CENTERING: "Independent centering",
    STEP_7A_PCA_A: "PCA on Dataset A",
    STEP_9A_PC_FOCUS: "PC analysis focus selection",
    STEP_10A_B_PROJECTION: "Project B into A PCA space",
    STEP_11A_PCA_B: "PCA on projected B",
    STEP_12A_REEXPRESS: "Re-express B loadings",
    STEP_13A_AXIS_JCVPCA: "Axis-level JcvPCA",
    STEP_14A_RSS: "RSS link-level aggregation",
    STEP_15A_WEIGHTING: "Optional explained-variance weighting",
    STEP_16A_NV: "NV descriptive baseline (longitudinal)",
    STEP_17A_EXPLORATORY: "Exploratory numeric summary",
    STEP_18A_EXPORT: "Export reproducibility package",
}


@dataclass
class StepState:
    step_id: str
    name: str
    status: str = STEP_NOT_STARTED
    upstream_fingerprint: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    artifact_paths: dict[str, str] = field(default_factory=dict)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    blocking_errors: list[dict[str, Any]] = field(default_factory=list)
    completed_at: str = ""
    user_can_continue: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepState:
        return cls(
            step_id=str(data.get("step_id") or ""),
            name=str(data.get("name") or ""),
            status=str(data.get("status") or STEP_NOT_STARTED),
            upstream_fingerprint=str(data.get("upstream_fingerprint") or ""),
            parameters=dict(data.get("parameters") or {}),
            artifact_paths={str(k): str(v) for k, v in (data.get("artifact_paths") or {}).items()},
            warnings=list(data.get("warnings") or []),
            blocking_errors=list(data.get("blocking_errors") or []),
            completed_at=str(data.get("completed_at") or ""),
            user_can_continue=bool(data.get("user_can_continue")),
        )


@dataclass
class WorkbenchRunState:
    run_id: str = ""
    upstream_fingerprint: str = ""
    construction_artifact_dir: str = ""
    preflight_artifact_dir: str = ""
    output_dir: str = ""
    preflight_gate_passed: bool = False
    steps: dict[str, StepState] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "upstream_fingerprint": self.upstream_fingerprint,
            "construction_artifact_dir": self.construction_artifact_dir,
            "preflight_artifact_dir": self.preflight_artifact_dir,
            "output_dir": self.output_dir,
            "preflight_gate_passed": self.preflight_gate_passed,
            "steps": {k: v.to_dict() for k, v in self.steps.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkbenchRunState:
        steps = {
            str(k): StepState.from_dict(v)
            for k, v in (data.get("steps") or {}).items()
        }
        return cls(
            run_id=str(data.get("run_id") or ""),
            upstream_fingerprint=str(data.get("upstream_fingerprint") or ""),
            construction_artifact_dir=str(data.get("construction_artifact_dir") or ""),
            preflight_artifact_dir=str(data.get("preflight_artifact_dir") or ""),
            output_dir=str(data.get("output_dir") or ""),
            preflight_gate_passed=bool(data.get("preflight_gate_passed")),
            steps=steps,
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_workbench_run_state(
    *,
    run_id: str,
    upstream_fingerprint: str,
    construction_artifact_dir: Path | str,
    preflight_artifact_dir: Path | str,
    output_dir: Path | str,
    preflight_gate_passed: bool,
) -> WorkbenchRunState:
    now = utc_now_iso()
    steps = {
        step_id: StepState(
            step_id=step_id,
            name=STEP_DISPLAY_NAMES[step_id],
            status=STEP_READY if step_id == STEP_6A_LOAD and preflight_gate_passed else STEP_NOT_STARTED,
            upstream_fingerprint=upstream_fingerprint,
        )
        for step_id in WORKBENCH_STEP_ORDER
    }
    if not preflight_gate_passed:
        for step in steps.values():
            step.status = STEP_BLOCKING
            step.blocking_errors = [
                {
                    "reason_code": "preflight_gate_blocked",
                    "message": "Phase 6 blocked until preflight gate passes.",
                }
            ]
    return WorkbenchRunState(
        run_id=run_id,
        upstream_fingerprint=upstream_fingerprint,
        construction_artifact_dir=str(construction_artifact_dir),
        preflight_artifact_dir=str(preflight_artifact_dir),
        output_dir=str(output_dir),
        preflight_gate_passed=preflight_gate_passed,
        steps=steps,
        created_at=now,
        updated_at=now,
    )


def check_phase6_gate(preflight_artifact_dir: Path | str) -> tuple[bool, dict[str, Any]]:
    """Return (gate_passed, gate_report) from Phase 5 preflight artifacts."""
    root = Path(preflight_artifact_dir)
    report: dict[str, Any] = {
        "gate_passed": False,
        "preflight_status": "",
        "can_continue_to_phase6": False,
        "warnings_acknowledged": False,
        "n_blocking_errors": 0,
        "messages": [],
    }

    summary_path = root / "preflight_summary.json"
    if not summary_path.is_file():
        report["messages"].append("Missing preflight_summary.json.")
        return False, report

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    report["preflight_status"] = str(summary.get("preflight_status") or "")
    report["can_continue_to_phase6"] = bool(summary.get("can_continue_to_phase6"))
    report["n_blocking_errors"] = int(summary.get("n_blocking_errors") or 0)
    report["warnings_acknowledged"] = bool(summary.get("warnings_acknowledged"))

    ack_path = root / "preflight_acknowledgment.json"
    if ack_path.is_file():
        ack = json.loads(ack_path.read_text(encoding="utf-8"))
        report["warnings_acknowledged"] = bool(ack.get("warnings_acknowledged"))

    blocking_path = root / "preflight_blocking_errors.csv"
    if blocking_path.is_file():
        import pandas as pd

        blocking_df = pd.read_csv(blocking_path)
        if not blocking_df.empty:
            report["n_blocking_errors"] = len(blocking_df)
            report["messages"].append("Preflight has blocking errors.")
            return False, report

    if report["preflight_status"] == "blocking" or report["n_blocking_errors"] > 0:
        report["messages"].append("Preflight status is blocking.")
        return False, report

    if report["preflight_status"] == "warning" and not report["warnings_acknowledged"]:
        report["messages"].append("Preflight warnings not acknowledged.")
        return False, report

    if not report["can_continue_to_phase6"]:
        report["messages"].append("preflight_summary.json reports can_continue_to_phase6=false.")
        return False, report

    report["gate_passed"] = True
    return True, report


def load_run_state(output_dir: Path | str) -> WorkbenchRunState | None:
    path = Path(output_dir) / "run_manifest.json"
    if not path.is_file():
        return None
    state = WorkbenchRunState.from_dict(json.loads(path.read_text(encoding="utf-8")))
    ensure_workbench_step_registry(state)
    return state


def save_run_state(state: WorkbenchRunState, output_dir: Path | str) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    state.updated_at = utc_now_iso()
    manifest_path = root / "run_manifest.json"
    manifest_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
    step_status_path = root / "step_status.json"
    step_status = {
        step_id: state.steps[step_id].to_dict()
        for step_id in WORKBENCH_STEP_ORDER
        if step_id in state.steps
    }
    step_status_path.write_text(json.dumps(step_status, indent=2), encoding="utf-8")
    return manifest_path


def invalidate_downstream_steps(state: WorkbenchRunState, from_step_id: str) -> None:
    """Mark downstream steps invalidated when upstream fingerprint changes."""
    try:
        start_idx = WORKBENCH_STEP_ORDER.index(from_step_id)
    except ValueError:
        return
    for step_id in WORKBENCH_STEP_ORDER[start_idx:]:
        step = state.steps.get(step_id)
        if step is None:
            continue
        if step.status in {STEP_COMPLETED, STEP_WARNING, STEP_READY, STEP_RUNNING}:
            step.status = STEP_INVALIDATED
            step.user_can_continue = False
            step.completed_at = ""


def sync_upstream_invalidation(
    state: WorkbenchRunState,
    current_fingerprint: str,
) -> bool:
    """Invalidate steps if upstream fingerprint changed. Returns True if invalidated."""
    ensure_workbench_step_registry(state)
    if state.upstream_fingerprint and state.upstream_fingerprint != current_fingerprint:
        invalidate_downstream_steps(state, STEP_6A_LOAD)
        state.upstream_fingerprint = current_fingerprint
        for step_id in WORKBENCH_STEP_ORDER:
            step = state.steps[step_id]
            step.upstream_fingerprint = current_fingerprint
        return True
    return False


def _step_completed_ready(step_id: str, state: WorkbenchRunState) -> tuple[bool, str]:
    step = state.steps.get(step_id)
    if not step or step.status not in {STEP_COMPLETED, STEP_WARNING}:
        return False, f"Complete {step_id} first."
    if not step.user_can_continue:
        return False, f"{step_id} is blocking."
    return True, ""


def ensure_workbench_step_registry(state: WorkbenchRunState) -> None:
    """Add newly introduced steps to an existing persisted run state."""
    for step_id in WORKBENCH_STEP_ORDER:
        if step_id not in state.steps:
            state.steps[step_id] = StepState(
                step_id=step_id,
                name=STEP_DISPLAY_NAMES[step_id],
                status=STEP_NOT_STARTED,
                upstream_fingerprint=state.upstream_fingerprint,
            )
    centering = state.steps.get(STEP_6C_CENTERING)
    pca_step = state.steps.get(STEP_7A_PCA_A)
    if (
        centering
        and centering.status == STEP_COMPLETED
        and pca_step
        and pca_step.status == STEP_NOT_STARTED
        and state.preflight_gate_passed
    ):
        pca_step.status = STEP_READY

    pca_step = state.steps.get(STEP_7A_PCA_A)
    focus_step = state.steps.get(STEP_9A_PC_FOCUS)
    if (
        pca_step
        and pca_step.status in {STEP_COMPLETED, STEP_WARNING}
        and pca_step.user_can_continue
        and focus_step
        and focus_step.status == STEP_NOT_STARTED
    ):
        focus_step.status = STEP_READY

    focus_step = state.steps.get(STEP_9A_PC_FOCUS)
    proj_step = state.steps.get(STEP_10A_B_PROJECTION)
    if (
        focus_step
        and focus_step.status in {STEP_COMPLETED, STEP_WARNING}
        and focus_step.user_can_continue
        and proj_step
        and proj_step.status == STEP_NOT_STARTED
    ):
        proj_step.status = STEP_READY

    for prev_id, nxt_id in zip(WORKBENCH_STEP_ORDER[:-1], WORKBENCH_STEP_ORDER[1:]):
        if nxt_id in {STEP_7A_PCA_A, STEP_9A_PC_FOCUS, STEP_10A_B_PROJECTION}:
            continue
        prev = state.steps.get(prev_id)
        nxt = state.steps.get(nxt_id)
        if (
            prev
            and prev.status in {STEP_COMPLETED, STEP_WARNING}
            and prev.user_can_continue
            and nxt
            and nxt.status == STEP_NOT_STARTED
        ):
            nxt.status = STEP_READY


def _step_7a_ready_for_downstream(state: WorkbenchRunState) -> tuple[bool, str]:
    step = state.steps.get(STEP_7A_PCA_A)
    if not step or step.status not in {STEP_COMPLETED, STEP_WARNING}:
        return False, "Complete Step 7A (PCA on Dataset A) first."
    if not step.user_can_continue:
        return False, "Step 7A is blocking; resolve PCA/stability issues first."
    return True, ""


def check_pca_stability_prerequisite(output_dir: Path | str) -> tuple[bool, str]:
    from layer3_jcvpca.workbench_pca_stability import check_pca_stability_gate

    ok, report = check_pca_stability_gate(output_dir)
    if ok:
        return True, ""
    return False, "; ".join(report.get("messages") or ["PCA stability gate not passed."])


def step_prerequisites_met(state: WorkbenchRunState, step_id: str) -> tuple[bool, str]:
    if step_id == STEP_6A_LOAD:
        return state.preflight_gate_passed, "Preflight gate must pass before loading datasets."
    if step_id == STEP_6B_RAW_PREVIEW:
        prev = state.steps.get(STEP_6A_LOAD)
        if prev and prev.status == STEP_COMPLETED:
            return True, ""
        return False, "Run Step 6A (load dataset) before raw preview."
    if step_id == STEP_6C_CENTERING:
        prev_a = state.steps.get(STEP_6A_LOAD)
        prev_b = state.steps.get(STEP_6B_RAW_PREVIEW)
        if not prev_a or prev_a.status != STEP_COMPLETED:
            return False, "Run Step 6A (load dataset) before centering."
        if not prev_b or prev_b.status != STEP_COMPLETED:
            return False, "Run Step 6B (raw preview) before centering."
        return True, ""
    if step_id == STEP_7A_PCA_A:
        if not state.preflight_gate_passed:
            return False, "Preflight gate must pass before PCA on A."
        for req_id, label in (
            (STEP_6A_LOAD, "6A"),
            (STEP_6B_RAW_PREVIEW, "6B"),
            (STEP_6C_CENTERING, "6C"),
        ):
            prev = state.steps.get(req_id)
            if not prev or prev.status != STEP_COMPLETED:
                return False, f"Complete Steps 6A–6C before PCA on A (missing {label})."
        return True, ""
    if step_id == STEP_9A_PC_FOCUS:
        ok, msg = _step_7a_ready_for_downstream(state)
        if not ok:
            return False, msg
        if not state.output_dir:
            return False, "Run output directory missing from state."
        stab_ok, stab_msg = check_pca_stability_prerequisite(state.output_dir)
        if not stab_ok:
            return False, stab_msg
        return True, ""
    jcvpca_steps = (
        STEP_10A_B_PROJECTION,
        STEP_11A_PCA_B,
        STEP_12A_REEXPRESS,
        STEP_13A_AXIS_JCVPCA,
        STEP_14A_RSS,
        STEP_15A_WEIGHTING,
        STEP_18A_EXPORT,
    )
    if step_id in jcvpca_steps:
        ok, msg = _step_7a_ready_for_downstream(state)
        if not ok:
            return False, msg
        focus = state.steps.get(STEP_9A_PC_FOCUS)
        if not focus or focus.status not in {STEP_COMPLETED, STEP_WARNING} or not focus.user_can_continue:
            return False, "Complete Step 9A (PC focus) first."
        if step_id != STEP_10A_B_PROJECTION:
            chain = list(WORKBENCH_STEP_ORDER)
            idx = chain.index(step_id)
            prev_id = chain[idx - 1]
            ok_prev, msg_prev = _step_completed_ready(prev_id, state)
            if not ok_prev:
                return False, msg_prev
        return True, ""
    if step_id == STEP_16A_NV:
        ok, msg = _step_completed_ready(STEP_14A_RSS, state)
        if not ok:
            return False, msg
        return True, ""
    if step_id == STEP_17A_EXPLORATORY:
        ok, msg = _step_completed_ready(STEP_14A_RSS, state)
        if not ok:
            return False, msg
        return True, ""
    return False, f"Unknown step: {step_id}"


def mark_step_completed(
    state: WorkbenchRunState,
    step_id: str,
    *,
    artifact_paths: dict[str, str],
    warnings: list[dict[str, Any]] | None = None,
    blocking_errors: list[dict[str, Any]] | None = None,
    parameters: dict[str, Any] | None = None,
) -> None:
    step = state.steps[step_id]
    step.artifact_paths = artifact_paths
    step.warnings = warnings or []
    step.blocking_errors = blocking_errors or []
    if parameters is not None:
        step.parameters = parameters
    step.completed_at = utc_now_iso()
    if step.blocking_errors:
        step.status = STEP_BLOCKING
        step.user_can_continue = False
    elif step.warnings:
        step.status = STEP_WARNING
        step.user_can_continue = True
    else:
        step.status = STEP_COMPLETED
        step.user_can_continue = True

    # Unlock next step
    try:
        idx = WORKBENCH_STEP_ORDER.index(step_id)
        if idx + 1 < len(WORKBENCH_STEP_ORDER) and step.user_can_continue:
            nxt = state.steps[WORKBENCH_STEP_ORDER[idx + 1]]
            if nxt.status in {STEP_NOT_STARTED, STEP_INVALIDATED}:
                nxt.status = STEP_READY
    except ValueError:
        pass

    save_run_state(state, state.output_dir)
