"""Batch Gaga JcvPCA workbench validation and execution."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from layer3_jcvpca.comparable_links import (
    COMPARABILITY_BLOCKING,
    REASON_FEATURE_ORDER_MISMATCH,
    detect_comparable_links,
    load_central_manifest,
    select_manifest_rows,
)
from layer3_jcvpca.dataset_builder import (
    ANALYSIS_MODE_EXPLORATORY,
    ANALYSIS_MODE_LONGITUDINAL,
    CONSTRUCTION_BLOCKING,
    DatasetConstructionConfig,
    DatasetSideSpec,
    build_dataset_construction_preview,
    write_dataset_construction_artifacts,
)
from layer3_jcvpca.jcvpca_trace import PcaAParameters
from layer3_jcvpca.pc_focus import (
    PC_FOCUS_ALL,
    PC_FOCUS_FUNCTIONAL,
    PC_FOCUS_NULL_SPACE,
    PcFocusParameters,
)
from layer3_jcvpca.step_runner import Phase6RunContext, StepRunError, initialize_run_state, run_step
from layer3_jcvpca.viz import (
    _save,
    plot_cumulative_variance,
    plot_delta_jrw,
    plot_delta_vs_nv,
    plot_jrw_bars,
    plot_scree,
)
from layer3_jcvpca.workbench_jcvpca_runner import WeightingParameters
from layer3_jcvpca.workbench_pca_stability import save_pca_stability_acknowledgment
from layer3_jcvpca.workbench_preflight import (
    load_construction_artifacts,
    run_workbench_preflight,
    save_preflight_acknowledgment,
    write_workbench_preflight_artifacts,
)
from layer3_jcvpca.workbench_state import (
    STEP_10A_B_PROJECTION,
    STEP_9A_PC_FOCUS,
    WORKBENCH_STEP_ORDER,
    invalidate_downstream_steps,
    load_run_state,
    save_run_state,
)

TARGET_PARTICIPANTS: tuple[str, ...] = ("671", "252")
BLOCK_EXERCISES: dict[str, list[str]] = {
    "A": ["P1", "P2", "P3", "P4", "P5"],
    "B": ["P3", "P4", "P5"],
}
BLOCK_LABELS: dict[str, str] = {
    "A": "all_P1_P2_P3_P4_P5",
    "B": "P3_P4_P5",
}
SENSITIVITY_P = 2
FOCUS_LABEL_ALL = "all"
FOCUS_LABEL_FUNCTIONAL = "functional_p2"
FOCUS_LABEL_NULL_SPACE = "null_space_p2"
GAGA_EXERCISES: tuple[str, ...] = ("P1", "P2", "P3", "P4", "P5")
TIMEPOINTS: tuple[str, ...] = ("T1", "T2", "T3")
REPETITIONS: tuple[str, ...] = ("R1", "R2")

STATUS_COMPLETED = "completed"
STATUS_SKIPPED_MISSING = "skipped_missing_data"
STATUS_BLOCKED_PREFLIGHT = "blocked_preflight"
STATUS_BLOCKED_NO_LINKS = "blocked_no_comparable_links"
STATUS_BLOCKED_MISSING_REP = "blocked_missing_repetition"
STATUS_BLOCKED_HARMONIZATION = "blocked_harmonization_required"
STATUS_FAILED = "failed_error"
STATUS_PARTIAL_WARNING = "completed_partial_with_warning"


@dataclass
class FocusRunResult:
    focus_mode: str
    focus_label: str
    status: str
    reason: str = ""
    p: int | None = None
    included_pcs: list[int] = field(default_factory=list)
    run_dir: str = ""


@dataclass
class ComparisonSpec:
    comparison_id: str
    comparison_label: str
    analysis_mode: str
    dataset_a_timepoints: list[str]
    dataset_a_repetitions: list[str]
    dataset_b_timepoints: list[str]
    dataset_b_repetitions: list[str]
    exploratory_timepoint: str = ""
    exploratory_repetition_a: str = "R1"
    exploratory_repetition_b: str = "R2"


@dataclass
class ComparisonRunResult:
    participant_id: str
    block_id: str
    block_exercises: list[str]
    comparison_id: str
    comparison_label: str
    analysis_mode: str
    status: str
    reason: str = ""
    comparable_links: list[str] = field(default_factory=list)
    excluded_links: pd.DataFrame = field(default_factory=pd.DataFrame)
    n_pca_features: int = 0
    feature_schema_id: str = ""
    selected_m: int | None = None
    selected_m_reason: str = ""
    pc_focus_mode: str = PC_FOCUS_ALL
    run_dir: str = ""
    error_trace: str = ""
    focus_runs: list[FocusRunResult] = field(default_factory=list)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_layer25_root() -> Path:
    src = _repo_root() / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from project_paths import load_project_paths  # noqa: PLC0415

    return load_project_paths().layer2_5_pre_jvcpca_review.resolve()


def block_label_for_id(block_id: str) -> str:
    return BLOCK_LABELS.get(block_id, block_id)


def refresh_central_manifest_from_scan(layer25_root: Path | str) -> pd.DataFrame:
    """Rebuild central manifest from window exports, excluding _archive paths."""
    layer25_root = Path(layer25_root)
    try:
        import sys

        l25_src = _repo_root() / "Layer2.5_Segmentation" / "src"
        if str(l25_src) not in sys.path:
            sys.path.insert(0, str(l25_src))
        from pre_jvcpca_review.layer3_export_manifest import (  # noqa: PLC0415
            central_manifest_path,
            scan_window_exports,
            write_layer25_export_manifest,
        )

        rows = scan_window_exports(layer25_root)
        write_layer25_export_manifest(rows, central_manifest_path(layer25_root))
        return load_central_manifest(layer25_root)
    except Exception:
        return load_central_manifest(layer25_root)


def build_comparison_specs() -> list[ComparisonSpec]:
    specs: list[ComparisonSpec] = []
    specs.append(
        ComparisonSpec(
            comparison_id="L1_T1_vs_T2",
            comparison_label="T1_vs_T2",
            analysis_mode=ANALYSIS_MODE_LONGITUDINAL,
            dataset_a_timepoints=["T1"],
            dataset_a_repetitions=["R1", "R2"],
            dataset_b_timepoints=["T2"],
            dataset_b_repetitions=["R1", "R2"],
        )
    )
    specs.append(
        ComparisonSpec(
            comparison_id="L2_T1_vs_T3",
            comparison_label="T1_vs_T3",
            analysis_mode=ANALYSIS_MODE_LONGITUDINAL,
            dataset_a_timepoints=["T1"],
            dataset_a_repetitions=["R1", "R2"],
            dataset_b_timepoints=["T3"],
            dataset_b_repetitions=["R1", "R2"],
        )
    )
    for tp in TIMEPOINTS:
        specs.append(
            ComparisonSpec(
                comparison_id=f"I_{tp}_R1_vs_R2",
                comparison_label=f"{tp}_R1_vs_{tp}_R2",
                analysis_mode=ANALYSIS_MODE_EXPLORATORY,
                dataset_a_timepoints=[tp],
                dataset_a_repetitions=["R1"],
                dataset_b_timepoints=[tp],
                dataset_b_repetitions=["R2"],
                exploratory_timepoint=tp,
                exploratory_repetition_a="R1",
                exploratory_repetition_b="R2",
            )
        )
    return specs


def scan_data_availability(
    manifest: pd.DataFrame,
    *,
    participants: list[str] | None = None,
    layer25_root: Path | None = None,
) -> pd.DataFrame:
    participants = participants or list(TARGET_PARTICIPANTS)
    attempts_path = (
        Path(layer25_root) / "layer25_export_attempts_report.csv"
        if layer25_root
        else default_layer25_root() / "layer25_export_attempts_report.csv"
    )
    attempts = pd.read_csv(attempts_path) if attempts_path.is_file() else pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for participant_id in participants:
        sub = manifest[manifest["participant_id"].astype(str) == participant_id]
        for tp in TIMEPOINTS:
            for rep in REPETITIONS:
                for exercise in GAGA_EXERCISES:
                    match = sub[
                        (sub["timepoint"].astype(str) == tp)
                        & (sub["repetition"].astype(str) == rep)
                        & (sub["gaga_exercise_label"].astype(str) == exercise)
                        & (sub["export_granularity"].astype(str) == "per_exercise")
                    ]
                    if match.empty:
                        attempt = attempts[
                            (attempts["participant_id"].astype(str) == participant_id)
                            & (attempts["timepoint"].astype(str) == tp)
                            & (attempts["repetition"].astype(str) == rep)
                            & (attempts["export_label"].astype(str) == exercise)
                        ] if not attempts.empty else pd.DataFrame()
                        reason = "not_in_central_manifest"
                        export_status = ""
                        if not attempt.empty:
                            export_status = str(attempt.iloc[0].get("status", ""))
                            reason = str(attempt.iloc[0].get("reason_message") or attempt.iloc[0].get("reason_code") or reason)
                        rows.append(
                            {
                                "participant_id": participant_id,
                                "timepoint": tp,
                                "repetition": rep,
                                "gaga_exercise_label": exercise,
                                "export_granularity": "per_exercise",
                                "available": False,
                                "matrix_path": "",
                                "layer3_safe": "",
                                "qc_status": "",
                                "n_frames": "",
                                "feature_schema_id": "",
                                "export_status": export_status,
                                "reason": reason,
                            }
                        )
                    else:
                        row = match.iloc[0]
                        path = Path(str(row["matrix_path"]))
                        rows.append(
                            {
                                "participant_id": participant_id,
                                "timepoint": tp,
                                "repetition": rep,
                                "gaga_exercise_label": exercise,
                                "export_granularity": "per_exercise",
                                "available": path.is_file(),
                                "matrix_path": str(row["matrix_path"]),
                                "layer3_safe": str(row.get("layer3_safe", "")),
                                "qc_status": str(row.get("qc_status", "")),
                                "n_frames": row.get("n_frames", ""),
                                "feature_schema_id": str(row.get("feature_schema_id", "")),
                                "export_status": "exported",
                                "reason": "" if path.is_file() else "matrix_file_missing",
                            }
                        )
                g4 = sub[
                    (sub["timepoint"].astype(str) == tp)
                    & (sub["repetition"].astype(str) == rep)
                    & (sub["export_granularity"].astype(str) == "combined_group4")
                ]
                if g4.empty:
                    rows.append(
                        {
                            "participant_id": participant_id,
                            "timepoint": tp,
                            "repetition": rep,
                            "gaga_exercise_label": "combined_group4",
                            "export_granularity": "combined_group4",
                            "available": False,
                            "matrix_path": "",
                            "layer3_safe": "",
                            "qc_status": "",
                            "n_frames": "",
                            "feature_schema_id": "",
                            "reason": "not_in_central_manifest",
                        }
                    )
                else:
                    row = g4.iloc[0]
                    path = Path(str(row["matrix_path"]))
                    rows.append(
                        {
                            "participant_id": participant_id,
                            "timepoint": tp,
                            "repetition": rep,
                            "gaga_exercise_label": "combined_group4",
                            "export_granularity": "combined_group4",
                            "available": path.is_file(),
                            "matrix_path": str(row["matrix_path"]),
                            "layer3_safe": str(row.get("layer3_safe", "")),
                            "qc_status": str(row.get("qc_status", "")),
                            "n_frames": row.get("n_frames", ""),
                            "feature_schema_id": str(row.get("feature_schema_id", "")),
                            "reason": "" if path.is_file() else "matrix_file_missing",
                        }
                    )
    return pd.DataFrame(rows)


def build_comparison_plan(
    *,
    participants: list[str] | None = None,
    blocks: dict[str, list[str]] | None = None,
    specs: list[ComparisonSpec] | None = None,
) -> pd.DataFrame:
    participants = participants or list(TARGET_PARTICIPANTS)
    blocks = blocks or BLOCK_EXERCISES
    specs = specs or build_comparison_specs()
    rows: list[dict[str, Any]] = []
    for participant_id in participants:
        for block_id, exercises in blocks.items():
            for spec in specs:
                rows.append(
                    {
                        "participant_id": participant_id,
                        "block_id": block_id,
                        "block_label": block_label_for_id(block_id),
                        "block_exercises": "+".join(exercises),
                        "comparison_id": spec.comparison_id,
                        "comparison_label": spec.comparison_label,
                        "analysis_mode": spec.analysis_mode,
                        "dataset_a_timepoints": ",".join(spec.dataset_a_timepoints),
                        "dataset_a_repetitions": ",".join(spec.dataset_a_repetitions),
                        "dataset_b_timepoints": ",".join(spec.dataset_b_timepoints),
                        "dataset_b_repetitions": ",".join(spec.dataset_b_repetitions),
                    }
                )
    return pd.DataFrame(rows)


def _rows_for_comparison(
    manifest: pd.DataFrame,
    participant_id: str,
    exercises: list[str],
    spec: ComparisonSpec,
) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    if spec.analysis_mode == ANALYSIS_MODE_EXPLORATORY:
        for rep in (spec.exploratory_repetition_a, spec.exploratory_repetition_b):
            parts.append(
                select_manifest_rows(
                    manifest,
                    participant_ids=[participant_id],
                    timepoints=[spec.exploratory_timepoint],
                    repetitions=[rep],
                    gaga_exercise_labels=exercises,
                    export_granularities=["per_exercise"],
                )
            )
    else:
        parts.append(
            select_manifest_rows(
                manifest,
                participant_ids=[participant_id],
                timepoints=spec.dataset_a_timepoints,
                repetitions=spec.dataset_a_repetitions,
                gaga_exercise_labels=exercises,
                export_granularities=["per_exercise"],
            )
        )
        parts.append(
            select_manifest_rows(
                manifest,
                participant_ids=[participant_id],
                timepoints=spec.dataset_b_timepoints,
                repetitions=spec.dataset_b_repetitions,
                gaga_exercise_labels=exercises,
                export_granularities=["per_exercise"],
            )
        )
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).drop_duplicates()


def _harmonization_block_reason(report) -> str:
    if report.summary.get("feature_order_match", True):
        return ""
    order_labels = report.summary.get("feature_order_mismatch_matrices") or []
    suffix = f" Mismatched matrices: {order_labels}." if order_labels else ""
    return f"Feature order/name mismatch across selected matrices.{suffix}"


def _expected_source_count(
    participant_id: str,
    exercises: list[str],
    spec: ComparisonSpec,
) -> tuple[int, list[str]]:
    missing: list[str] = []
    if spec.analysis_mode == ANALYSIS_MODE_EXPLORATORY:
        expected = len(exercises) * 2
        for exercise in exercises:
            for rep in (spec.exploratory_repetition_a, spec.exploratory_repetition_b):
                missing.append(f"{participant_id}/{spec.exploratory_timepoint}/{rep}/{exercise}")
        return expected, missing
    expected = len(exercises) * (
        len(spec.dataset_a_timepoints) * len(spec.dataset_a_repetitions)
        + len(spec.dataset_b_timepoints) * len(spec.dataset_b_repetitions)
    )
    for tp in spec.dataset_a_timepoints:
        for rep in spec.dataset_a_repetitions:
            for exercise in exercises:
                missing.append(f"{participant_id}/{tp}/{rep}/{exercise}")
    for tp in spec.dataset_b_timepoints:
        for rep in spec.dataset_b_repetitions:
            for exercise in exercises:
                missing.append(f"{participant_id}/{tp}/{rep}/{exercise}")
    return expected, missing


def _run_workbench_pipeline(run_dir: Path, construction_dir: Path, preflight_dir: Path) -> None:
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "construction": str(construction_dir),
                "preflight": str(preflight_dir),
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()[:16]
    ctx = Phase6RunContext(
        construction_artifact_dir=construction_dir,
        preflight_artifact_dir=preflight_dir,
        output_dir=run_dir,
        upstream_fingerprint=fingerprint,
        run_id=f"batch_{run_dir.name}",
    )
    state = initialize_run_state(ctx)
    pre_pca_steps = WORKBENCH_STEP_ORDER[: WORKBENCH_STEP_ORDER.index(STEP_10A_B_PROJECTION)]
    for step_id in pre_pca_steps:
        if step_id.endswith("pca_on_dataset_a"):
            state = run_step(
                step_id,
                ctx,
                state,
                pca_a_params=PcaAParameters(variance_threshold=0.80),
            )
        elif step_id.endswith("pc_focus_selection"):
            state = run_step(
                step_id,
                ctx,
                state,
                pc_focus_params=PcFocusParameters(pc_focus_mode=PC_FOCUS_ALL),
            )
        else:
            state = run_step(step_id, ctx, state)
        combined_path = run_dir / "pca_stability_combined_summary.json"
        if combined_path.is_file():
            combined = json.loads(combined_path.read_text(encoding="utf-8"))
            if combined.get("combined_status") == "warning" and not combined.get(
                "warnings_acknowledged"
            ):
                save_pca_stability_acknowledgment(
                    run_dir, acknowledged=True, combined_summary=combined
                )
        save_run_state(state, run_dir)

    start = WORKBENCH_STEP_ORDER.index(STEP_10A_B_PROJECTION)
    for step_id in WORKBENCH_STEP_ORDER[start:]:
        if step_id.endswith("explained_variance_weighting"):
            state = run_step(
                step_id,
                ctx,
                state,
                weighting_params=WeightingParameters(explained_variance_weighting=False),
            )
        else:
            state = run_step(step_id, ctx, state)
        save_run_state(state, run_dir)


def _run_focus_sensitivity_pipeline(
    main_run_dir: Path,
    *,
    construction_dir: Path,
    preflight_dir: Path,
    focus_label: str,
    pc_focus_params: PcFocusParameters,
) -> FocusRunResult:
    focus_dir = main_run_dir.parent / f"run_{focus_label}"
    if focus_dir.exists():
        shutil.rmtree(focus_dir)
    shutil.copytree(main_run_dir, focus_dir)

    state = load_run_state(focus_dir)
    if state is None:
        return FocusRunResult(
            focus_mode=pc_focus_params.pc_focus_mode,
            focus_label=focus_label,
            status=STATUS_FAILED,
            reason="Could not load run state for sensitivity rerun.",
            p=pc_focus_params.p,
        )

    fingerprint = state.upstream_fingerprint
    invalidate_downstream_steps(state, STEP_9A_PC_FOCUS)
    save_run_state(state, focus_dir)

    ctx = Phase6RunContext(
        construction_artifact_dir=construction_dir,
        preflight_artifact_dir=preflight_dir,
        output_dir=focus_dir,
        upstream_fingerprint=fingerprint,
        run_id=f"batch_{focus_dir.name}",
    )

    start = WORKBENCH_STEP_ORDER.index(STEP_9A_PC_FOCUS)
    for step_id in WORKBENCH_STEP_ORDER[start:]:
        if step_id.endswith("pc_focus_selection"):
            state = run_step(step_id, ctx, state, pc_focus_params=pc_focus_params)
        elif step_id.endswith("explained_variance_weighting"):
            state = run_step(
                step_id,
                ctx,
                state,
                weighting_params=WeightingParameters(explained_variance_weighting=False),
            )
        else:
            state = run_step(step_id, ctx, state)
        save_run_state(state, focus_dir)

    pf_path = focus_dir / "pc_focus_selection.json"
    included: list[int] = []
    if pf_path.is_file():
        included = [int(x) for x in json.loads(pf_path.read_text(encoding="utf-8")).get("included_pcs", [])]

    return FocusRunResult(
        focus_mode=pc_focus_params.pc_focus_mode,
        focus_label=focus_label,
        status=STATUS_COMPLETED,
        p=pc_focus_params.p,
        included_pcs=included,
        run_dir=str(focus_dir),
    )


def _run_pc_focus_sensitivity(
    main_run_dir: Path,
    *,
    construction_dir: Path,
    preflight_dir: Path,
    selected_m: int | None,
) -> list[FocusRunResult]:
    results: list[FocusRunResult] = []

    try:
        results.append(
            _run_focus_sensitivity_pipeline(
                main_run_dir,
                construction_dir=construction_dir,
                preflight_dir=preflight_dir,
                focus_label=FOCUS_LABEL_FUNCTIONAL,
                pc_focus_params=PcFocusParameters(
                    pc_focus_mode=PC_FOCUS_FUNCTIONAL,
                    p=SENSITIVITY_P,
                ),
            )
        )
    except (StepRunError, ValueError, OSError) as exc:
        results.append(
            FocusRunResult(
                focus_mode=PC_FOCUS_FUNCTIONAL,
                focus_label=FOCUS_LABEL_FUNCTIONAL,
                status=STATUS_FAILED,
                reason=str(exc),
                p=SENSITIVITY_P,
            )
        )

    if selected_m is None or selected_m <= SENSITIVITY_P:
        results.append(
            FocusRunResult(
                focus_mode=PC_FOCUS_NULL_SPACE,
                focus_label=FOCUS_LABEL_NULL_SPACE,
                status="skipped",
                reason="null_space_skipped_selected_m_leq_p",
                p=SENSITIVITY_P,
            )
        )
        return results

    try:
        results.append(
            _run_focus_sensitivity_pipeline(
                main_run_dir,
                construction_dir=construction_dir,
                preflight_dir=preflight_dir,
                focus_label=FOCUS_LABEL_NULL_SPACE,
                pc_focus_params=PcFocusParameters(
                    pc_focus_mode=PC_FOCUS_NULL_SPACE,
                    p=SENSITIVITY_P,
                ),
            )
        )
    except (StepRunError, ValueError, OSError) as exc:
        results.append(
            FocusRunResult(
                focus_mode=PC_FOCUS_NULL_SPACE,
                focus_label=FOCUS_LABEL_NULL_SPACE,
                status=STATUS_FAILED,
                reason=str(exc),
                p=SENSITIVITY_P,
            )
        )
    return results


def _write_focus_sensitivity_plots(
    *,
    batch_root: Path,
    participant_id: str,
    block_id: str,
    comparison_id: str,
    main_run_dir: Path,
    focus_runs: list[FocusRunResult],
) -> list[dict[str, str]]:
    import matplotlib.pyplot as plt

    plot_root = (
        batch_root
        / "plots"
        / "all_vs_functional_vs_nullspace"
        / participant_id
        / block_id
        / comparison_id
    )
    plot_root.mkdir(parents=True, exist_ok=True)
    index: list[dict[str, str]] = []

    def _load_link(run_dir: Path) -> pd.DataFrame | None:
        path = run_dir / "link_level_jcvpca_unweighted.csv"
        return pd.read_csv(path) if path.is_file() else None

    main_df = _load_link(main_run_dir)
    if main_df is None:
        return index

    focus_map: dict[str, pd.DataFrame] = {FOCUS_LABEL_ALL: main_df}
    for fr in focus_runs:
        if fr.status == STATUS_COMPLETED and fr.run_dir:
            df = _load_link(Path(fr.run_dir))
            if df is not None:
                focus_map[fr.focus_label] = df

    labels = [FOCUS_LABEL_ALL, FOCUS_LABEL_FUNCTIONAL, FOCUS_LABEL_NULL_SPACE]
    available = [lab for lab in labels if lab in focus_map]
    if len(available) >= 2:
        fig, axes = plt.subplots(1, len(available), figsize=(5 * len(available), 5), sharey=True)
        if len(available) == 1:
            axes = [axes]
        for ax, lab in zip(axes, available):
            df = focus_map[lab]
            agg = df.groupby("link_id")["JcvPCA_link"].mean().sort_values()
            ax.barh(agg.index, agg.values, color="steelblue")
            ax.set_title(lab)
            ax.invert_yaxis()
        fig.suptitle(f"{participant_id} {block_label_for_id(block_id)} {comparison_id}")
        out = plot_root / "all_vs_functional_vs_nullspace_link_jcvpca.png"
        _save(fig, out)
        index.append(
            {
                "plot_name": "all_vs_functional_vs_nullspace_link_jcvpca",
                "path": str(out.relative_to(batch_root)),
            }
        )

    for lab in (FOCUS_LABEL_FUNCTIONAL, FOCUS_LABEL_NULL_SPACE):
        if lab not in focus_map:
            continue
        out = plot_root / f"{lab}_link_jcvpca.png"
        _save(plot_delta_jrw(focus_map[lab], title=f"Link-level JcvPCA ({lab})"), out)
        index.append({"plot_name": f"{lab}_link_jcvpca", "path": str(out.relative_to(batch_root))})

    return index


def _write_comparison_plots(
    run_dir: Path,
    plot_dir: Path,
    batch_root: Path,
) -> list[dict[str, str]]:
    plot_dir.mkdir(parents=True, exist_ok=True)
    index: list[dict[str, str]] = []

    link_path = run_dir / "link_level_jcvpca_unweighted.csv"
    if link_path.is_file():
        link_df = pd.read_csv(link_path)
        for name, fig_fn, fname in (
            ("link_jcvpca_bar", lambda df: plot_delta_jrw(df, title="Link-level JcvPCA (RSS)"), "link_jcvpca_bar.png"),
            ("jrw_A_B_bar", plot_jrw_bars, "jrw_A_B_bar.png"),
        ):
            out = plot_dir / fname
            _save(fig_fn(link_df), out)
            index.append({"plot_name": name, "path": str(out.relative_to(batch_root))})

    evr_path = run_dir / "pca_A_explained_variance.csv"
    if evr_path.is_file():
        evr = pd.read_csv(evr_path)["explained_variance_ratio"].to_numpy()
        for name, fn, fname in (
            ("pca_A_scree", plot_scree, "pca_A_scree.png"),
            ("pca_A_cumulative_variance", plot_cumulative_variance, "pca_A_cumulative_variance.png"),
        ):
            out = plot_dir / fname
            _save(fn(evr), out)
            index.append({"plot_name": name, "path": str(out.relative_to(batch_root))})

    nv_path = run_dir / "main_vs_nv_descriptive_comparison.csv"
    if nv_path.is_file():
        mvn = pd.read_csv(nv_path)
        if not mvn.empty:
            out = plot_dir / "nv_interval_overlay.png"
            _save(plot_delta_vs_nv(mvn), out)
            index.append(
                {
                    "plot_name": "nv_interval_overlay",
                    "path": str(out.relative_to(batch_root)),
                }
            )
    return index


def run_single_comparison(
    manifest: pd.DataFrame,
    *,
    participant_id: str,
    block_id: str,
    exercises: list[str],
    spec: ComparisonSpec,
    batch_root: Path,
) -> ComparisonRunResult:
    result = ComparisonRunResult(
        participant_id=participant_id,
        block_id=block_id,
        block_exercises=exercises,
        comparison_id=spec.comparison_id,
        comparison_label=spec.comparison_label,
        analysis_mode=spec.analysis_mode,
        status=STATUS_SKIPPED_MISSING,
    )
    selected_rows = _rows_for_comparison(manifest, participant_id, exercises, spec)
    expected_n, _ = _expected_source_count(participant_id, exercises, spec)
    if len(selected_rows) < expected_n:
        result.reason = (
            f"Missing source matrices: found {len(selected_rows)} of {expected_n} expected "
            f"per-exercise exports for block {block_id} ({'+'.join(exercises)})."
        )
        return result

    link_report = detect_comparable_links(selected_rows)
    result.excluded_links = link_report.excluded_links.copy()
    result.comparable_links = list(link_report.comparable_link_stems)
    result.n_pca_features = len(result.comparable_links) * 3
    if not link_report.selected_matrices.empty:
        schemas = link_report.selected_matrices["feature_schema_id"].astype(str).unique()
        result.feature_schema_id = schemas[0] if len(schemas) == 1 else "|".join(schemas)

    if link_report.summary.get("comparability_status") == COMPARABILITY_BLOCKING:
        result.status = STATUS_BLOCKED_NO_LINKS
        result.reason = "No comparable links across selected matrices."
        return result

    harm_reason = _harmonization_block_reason(link_report)
    if harm_reason:
        result.status = STATUS_BLOCKED_HARMONIZATION
        result.reason = harm_reason
        return result

    if not result.comparable_links:
        result.status = STATUS_BLOCKED_NO_LINKS
        result.reason = "Comparable link set is empty after detection."
        return result

    config = DatasetConstructionConfig(
        analysis_mode=spec.analysis_mode,
        participant_ids=[participant_id],
        exercises=exercises,
        export_granularities=["per_exercise"],
        dataset_a=DatasetSideSpec(
            timepoints=spec.dataset_a_timepoints,
            repetitions=spec.dataset_a_repetitions,
        ),
        dataset_b=DatasetSideSpec(
            timepoints=spec.dataset_b_timepoints,
            repetitions=spec.dataset_b_repetitions,
        ),
        exploratory_timepoint=spec.exploratory_timepoint,
        exploratory_repetition_a=spec.exploratory_repetition_a,
        exploratory_repetition_b=spec.exploratory_repetition_b,
        selected_link_stems=result.comparable_links,
        acknowledge_missing_repetitions=False,
    )
    preview = build_dataset_construction_preview(manifest, config)
    comp_key = f"{participant_id}_{block_id}_{spec.comparison_id}"
    comp_root = batch_root / "comparisons" / comp_key
    construction_dir = comp_root / "construction"
    preflight_dir = comp_root / "preflight"
    run_dir = comp_root / "run"
    write_dataset_construction_artifacts(preview, construction_dir)

    if preview.construction_status == CONSTRUCTION_BLOCKING:
        if not preview.blocking_errors.empty and (
            preview.blocking_errors["reason_code"].astype(str) == "missing_matrix"
        ).any():
            result.status = STATUS_BLOCKED_MISSING_REP
        else:
            result.status = STATUS_SKIPPED_MISSING
        msgs = preview.blocking_errors["reason_message"].astype(str).tolist() if not preview.blocking_errors.empty else []
        result.reason = "; ".join(msgs[:3]) or "Dataset construction blocked."
        return result

    bundle = load_construction_artifacts(construction_dir)
    preflight = run_workbench_preflight(bundle, warnings_acknowledged=True)
    write_workbench_preflight_artifacts(preflight, preflight_dir)
    save_preflight_acknowledgment(
        preflight_dir, acknowledged=True, preflight_summary=preflight.summary
    )

    if preflight.summary.get("preflight_status") == "blocking":
        result.status = STATUS_BLOCKED_PREFLIGHT
        result.reason = "; ".join(
            preflight.summary.get("messages") or ["Preflight blocking."]
        )
        return result

    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        _run_workbench_pipeline(run_dir, construction_dir, preflight_dir)
        result.status = STATUS_COMPLETED
        result.run_dir = str(run_dir)
        result.reason = ""

        sel_path = run_dir / "pca_A_selected_m.json"
        if sel_path.is_file():
            sel = json.loads(sel_path.read_text(encoding="utf-8"))
            result.selected_m = int(sel.get("selected_m", 0))
            result.selected_m_reason = str(sel.get("selection_reason", ""))
        result.pc_focus_mode = PC_FOCUS_ALL

        result.focus_runs = _run_pc_focus_sensitivity(
            run_dir,
            construction_dir=construction_dir,
            preflight_dir=preflight_dir,
            selected_m=result.selected_m,
        )

        plot_dir = batch_root / "plots" / participant_id / block_id / spec.comparison_id
        _write_comparison_plots(run_dir, plot_dir, batch_root)
        _write_focus_sensitivity_plots(
            batch_root=batch_root,
            participant_id=participant_id,
            block_id=block_id,
            comparison_id=spec.comparison_id,
            main_run_dir=run_dir,
            focus_runs=result.focus_runs,
        )
    except (StepRunError, ValueError, OSError) as exc:
        result.status = STATUS_FAILED
        result.reason = str(exc)
        result.error_trace = traceback.format_exc()
    except Exception as exc:  # noqa: BLE001 — batch runner must capture per-comparison failures
        result.status = STATUS_FAILED
        result.reason = f"{type(exc).__name__}: {exc}"
        result.error_trace = traceback.format_exc()
    return result


def run_gaga_batch_jcvpca(
    *,
    layer25_root: Path | str | None = None,
    output_dir: Path | str | None = None,
    participants: list[str] | None = None,
) -> Path:
    layer25_root = Path(layer25_root or default_layer25_root())
    participants = participants or list(TARGET_PARTICIPANTS)
    batch_root = Path(output_dir or (_repo_root() / "Layer3_JcvPCA" / "outputs" / f"gaga_batch_jcvpca_{utc_timestamp()}"))
    batch_root.mkdir(parents=True, exist_ok=True)

    manifest = refresh_central_manifest_from_scan(layer25_root)
    availability = scan_data_availability(manifest, participants=participants, layer25_root=layer25_root)
    availability.to_csv(batch_root / "data_availability_report.csv", index=False)
    attempts_src = layer25_root / "layer25_export_attempts_report.csv"
    if attempts_src.is_file():
        pd.read_csv(attempts_src).to_csv(batch_root / "export_attempts_report.csv", index=False)

    plan = build_comparison_plan(participants=participants)
    plan.to_csv(batch_root / "comparison_plan.csv", index=False)

    specs = {s.comparison_id: s for s in build_comparison_specs()}
    results: list[ComparisonRunResult] = []
    for _, row in plan.iterrows():
        spec = specs[str(row["comparison_id"])]
        exercises = BLOCK_EXERCISES[str(row["block_id"])]
        results.append(
            run_single_comparison(
                manifest,
                participant_id=str(row["participant_id"]),
                block_id=str(row["block_id"]),
                exercises=exercises,
                spec=spec,
                batch_root=batch_root,
            )
        )

    _write_batch_tables(batch_root, results, manifest, layer25_root)
    return batch_root


def _write_batch_tables(
    batch_root: Path,
    results: list[ComparisonRunResult],
    manifest: pd.DataFrame,
    layer25_root: Path,
) -> None:
    status_rows = []
    comparable_rows = []
    excluded_rows = []
    construction_rows = []
    preflight_rows = []
    stability_rows = []
    selected_m_rows = []
    pc_focus_rows = []
    link_rows = []
    axis_rows = []
    link_focus_rows = []
    axis_focus_rows = []
    sensitivity_rows = []
    null_space_rows = []
    focus_status_rows = []
    nv_rows = []
    exploratory_rows = []
    plot_rows = []
    workbench_exports: list[dict[str, str]] = []

    def _append_link_axis(run_dir: Path, res: ComparisonRunResult, comp_key: str, focus_label: str, p: int | None) -> None:
        lp = run_dir / "link_level_jcvpca_unweighted.csv"
        if lp.is_file():
            ldf = pd.read_csv(lp)
            ldf.insert(0, "focus_mode", focus_label)
            ldf.insert(0, "p", p if p is not None else "")
            ldf.insert(0, "comparison_key", comp_key)
            ldf.insert(0, "block_label", block_label_for_id(res.block_id))
            ldf.insert(0, "participant_id", res.participant_id)
            ldf.insert(0, "block_id", res.block_id)
            ldf.insert(0, "comparison_id", res.comparison_id)
            ldf.insert(0, "comparison_label", res.comparison_label)
            if focus_label == FOCUS_LABEL_ALL:
                link_rows.append(ldf)
            else:
                link_focus_rows.append(ldf)
        ap = run_dir / "axis_level_jcvpca_unweighted.csv"
        if ap.is_file():
            adf = pd.read_csv(ap)
            adf.insert(0, "focus_mode", focus_label)
            adf.insert(0, "p", p if p is not None else "")
            adf.insert(0, "comparison_key", comp_key)
            adf.insert(0, "block_label", block_label_for_id(res.block_id))
            adf.insert(0, "participant_id", res.participant_id)
            adf.insert(0, "block_id", res.block_id)
            adf.insert(0, "comparison_id", res.comparison_id)
            adf.insert(0, "comparison_label", res.comparison_label)
            if focus_label == FOCUS_LABEL_ALL:
                axis_rows.append(adf)
            else:
                axis_focus_rows.append(adf)

    for res in results:
        block_label = block_label_for_id(res.block_id)
        status_rows.append(
            {
                "participant_id": res.participant_id,
                "block_id": res.block_id,
                "block_label": block_label,
                "block_exercises": "+".join(res.block_exercises),
                "comparison_id": res.comparison_id,
                "comparison_label": res.comparison_label,
                "focus_mode": FOCUS_LABEL_ALL,
                "analysis_mode": res.analysis_mode,
                "status": res.status,
                "reason": res.reason,
                "n_comparable_links": len(res.comparable_links),
                "n_pca_features": res.n_pca_features,
                "feature_schema_id": res.feature_schema_id,
                "selected_m": res.selected_m,
                "pc_focus_mode": res.pc_focus_mode,
                "run_dir": res.run_dir,
            }
        )
        for fr in res.focus_runs:
            focus_status_rows.append(
                {
                    "participant_id": res.participant_id,
                    "block_id": res.block_id,
                    "block_label": block_label,
                    "comparison_id": res.comparison_id,
                    "comparison_label": res.comparison_label,
                    "focus_mode": fr.focus_label,
                    "p": fr.p,
                    "included_pcs": ",".join(str(x) for x in fr.included_pcs),
                    "status": fr.status,
                    "reason": fr.reason,
                    "selected_m": res.selected_m,
                }
            )
            sensitivity_rows.append(
                {
                    "participant_id": res.participant_id,
                    "block_label": block_label,
                    "comparison_label": res.comparison_label,
                    "focus_mode": fr.focus_label,
                    "p": fr.p,
                    "selected_m": res.selected_m,
                    "included_pcs": ",".join(str(x) for x in fr.included_pcs),
                    "status": fr.status,
                    "reason": fr.reason,
                }
            )
            if fr.focus_label == FOCUS_LABEL_NULL_SPACE:
                null_space_rows.append(
                    {
                        "participant_id": res.participant_id,
                        "block_label": block_label,
                        "comparison_label": res.comparison_label,
                        "selected_m": res.selected_m,
                        "p": fr.p,
                        "status": fr.status,
                        "reason": fr.reason,
                    }
                )
        for stem in res.comparable_links:
            comparable_rows.append(
                {
                    "participant_id": res.participant_id,
                    "block_id": res.block_id,
                    "comparison_id": res.comparison_id,
                    "link_stem": stem,
                }
            )
        if not res.excluded_links.empty:
            ex = res.excluded_links.copy()
            ex["participant_id"] = res.participant_id
            ex["block_id"] = res.block_id
            ex["comparison_id"] = res.comparison_id
            excluded_rows.append(ex)

        if not res.run_dir:
            continue
        run_dir = Path(res.run_dir)
        comp_key = run_dir.parent.name
        constr = run_dir.parent / "construction"
        pref = run_dir.parent / "preflight"
        if (constr / "dataset_construction_summary.json").is_file():
            summary = json.loads((constr / "dataset_construction_summary.json").read_text())
            construction_rows.append(
                {
                    "comparison_key": comp_key,
                    "construction_status": summary.get("construction_status"),
                    "dataset_a_rows": summary.get("dataset_a_total_rows"),
                    "dataset_b_rows": summary.get("dataset_b_total_rows"),
                    "n_warnings": summary.get("n_warnings"),
                }
            )
        if (pref / "preflight_summary.json").is_file():
            ps = json.loads((pref / "preflight_summary.json").read_text())
            preflight_rows.append(
                {
                    "comparison_key": comp_key,
                    "preflight_status": ps.get("preflight_status"),
                    "can_continue": ps.get("can_continue_to_phase6"),
                }
            )
        for side in ("A", "B"):
            sp = run_dir / f"pca_{side}_stability_summary.json"
            if sp.is_file():
                ss = json.loads(sp.read_text())
                stability_rows.append({"comparison_key": comp_key, "dataset_side": side, **ss})
        if (run_dir / "pca_A_selected_m.json").is_file():
            sel = json.loads((run_dir / "pca_A_selected_m.json").read_text())
            selected_m_rows.append({"comparison_key": comp_key, **sel})
        if (run_dir / "pc_focus_selection.json").is_file():
            pf = json.loads((run_dir / "pc_focus_selection.json").read_text())
            pf_row = {"comparison_key": comp_key, "focus_mode": FOCUS_LABEL_ALL, **pf}
            pc_focus_rows.append(pf_row)
        _append_link_axis(run_dir, res, comp_key, FOCUS_LABEL_ALL, None)

        for fr in res.focus_runs:
            if fr.status != STATUS_COMPLETED or not fr.run_dir:
                continue
            fr_dir = Path(fr.run_dir)
            if (fr_dir / "pc_focus_selection.json").is_file():
                pf = json.loads((fr_dir / "pc_focus_selection.json").read_text())
                pc_focus_rows.append({"comparison_key": comp_key, "focus_mode": fr.focus_label, **pf})
            _append_link_axis(fr_dir, res, comp_key, fr.focus_label, fr.p)

        np_ = run_dir / "main_vs_nv_descriptive_comparison.csv"
        if np_.is_file():
            ndf = pd.read_csv(np_)
            ndf.insert(0, "comparison_key", comp_key)
            ndf.insert(0, "participant_id", res.participant_id)
            ndf.insert(0, "block_id", res.block_id)
            ndf.insert(0, "comparison_id", res.comparison_id)
            nv_rows.append(ndf)
        ep = run_dir / "exploratory_numeric_summary.csv"
        if ep.is_file():
            edf = pd.read_csv(ep)
            edf.insert(0, "comparison_key", comp_key)
            edf.insert(0, "participant_id", res.participant_id)
            edf.insert(0, "block_id", res.block_id)
            edf.insert(0, "comparison_id", res.comparison_id)
            exploratory_rows.append(edf)

        plot_dir = batch_root / "plots" / res.participant_id / res.block_id / res.comparison_id
        if plot_dir.is_dir():
            for png in sorted(plot_dir.glob("*.png")):
                plot_rows.append(
                    {
                        "participant_id": res.participant_id,
                        "block_id": res.block_id,
                        "block_label": block_label,
                        "comparison_id": res.comparison_id,
                        "focus_mode": FOCUS_LABEL_ALL,
                        "plot_path": str(png.relative_to(batch_root)),
                    }
                )
        sens_plot_dir = (
            batch_root
            / "plots"
            / "all_vs_functional_vs_nullspace"
            / res.participant_id
            / res.block_id
            / res.comparison_id
        )
        if sens_plot_dir.is_dir():
            for png in sorted(sens_plot_dir.glob("*.png")):
                plot_rows.append(
                    {
                        "participant_id": res.participant_id,
                        "block_id": res.block_id,
                        "block_label": block_label,
                        "comparison_id": res.comparison_id,
                        "focus_mode": "sensitivity",
                        "plot_path": str(png.relative_to(batch_root)),
                    }
                )
        wb = run_dir / "workbench_export_manifest.json"
        if wb.is_file():
            workbench_exports.append(
                {
                    "comparison_key": comp_key,
                    "participant_id": res.participant_id,
                    "block_label": block_label,
                    "comparison_label": res.comparison_label,
                    "manifest_path": str(wb.relative_to(batch_root)),
                }
            )

    focus_status_df = pd.DataFrame(focus_status_rows)
    if not focus_status_df.empty:
        focus_status_df.to_csv(batch_root / "comparison_status_by_focus.csv", index=False)
    pd.DataFrame(status_rows).to_csv(batch_root / "comparison_status.csv", index=False)
    pd.DataFrame(sensitivity_rows).to_csv(batch_root / "pc_focus_sensitivity_results.csv", index=False)
    pd.DataFrame(null_space_rows).to_csv(batch_root / "null_space_availability_report.csv", index=False)
    pd.DataFrame(comparable_rows).to_csv(batch_root / "comparable_links_by_comparison.csv", index=False)
    if excluded_rows:
        pd.concat(excluded_rows, ignore_index=True).to_csv(
            batch_root / "excluded_links_by_comparison.csv", index=False
        )
    else:
        pd.DataFrame(
            columns=["participant_id", "block_id", "comparison_id", "link_stem", "reason_code", "reason_message"]
        ).to_csv(batch_root / "excluded_links_by_comparison.csv", index=False)
    pd.DataFrame(construction_rows).to_csv(batch_root / "dataset_construction_by_comparison.csv", index=False)
    pd.DataFrame(preflight_rows).to_csv(batch_root / "preflight_by_comparison.csv", index=False)
    pd.DataFrame(stability_rows).to_csv(batch_root / "pca_stability_by_comparison.csv", index=False)
    pd.DataFrame(selected_m_rows).to_csv(batch_root / "selected_m_by_comparison.csv", index=False)
    pd.DataFrame(pc_focus_rows).to_csv(batch_root / "pc_focus_by_comparison.csv", index=False)
    if link_rows:
        pd.concat(link_rows, ignore_index=True).to_csv(batch_root / "jcvpca_link_results.csv", index=False)
    else:
        pd.DataFrame().to_csv(batch_root / "jcvpca_link_results.csv", index=False)
    if axis_rows:
        pd.concat(axis_rows, ignore_index=True).to_csv(batch_root / "jcvpca_axis_results.csv", index=False)
    else:
        pd.DataFrame().to_csv(batch_root / "jcvpca_axis_results.csv", index=False)
    if link_focus_rows:
        pd.concat(link_focus_rows, ignore_index=True).to_csv(
            batch_root / "jcvpca_link_results_by_pc_focus.csv", index=False
        )
    else:
        pd.DataFrame().to_csv(batch_root / "jcvpca_link_results_by_pc_focus.csv", index=False)
    if axis_focus_rows:
        pd.concat(axis_focus_rows, ignore_index=True).to_csv(
            batch_root / "jcvpca_axis_results_by_pc_focus.csv", index=False
        )
    else:
        pd.DataFrame().to_csv(batch_root / "jcvpca_axis_results_by_pc_focus.csv", index=False)
    if nv_rows:
        pd.concat(nv_rows, ignore_index=True).to_csv(batch_root / "nv_baseline_results.csv", index=False)
    else:
        pd.DataFrame().to_csv(batch_root / "nv_baseline_results.csv", index=False)
    if exploratory_rows:
        pd.concat(exploratory_rows, ignore_index=True).to_csv(
            batch_root / "exploratory_summary_results.csv", index=False
        )
    else:
        pd.DataFrame().to_csv(batch_root / "exploratory_summary_results.csv", index=False)
    pd.DataFrame(plot_rows).to_csv(batch_root / "plot_index.csv", index=False)
    pd.DataFrame(workbench_exports).to_csv(batch_root / "workbench_export_manifest.csv", index=False)

    manifest_path = layer25_root / "layer25_export_manifest.csv"
    attempts_path = layer25_root / "layer25_export_attempts_report.csv"
    batch_manifest = {
        "batch_timestamp": batch_root.name.replace("gaga_batch_jcvpca_", ""),
        "layer25_root": str(layer25_root),
        "central_manifest": str(manifest_path),
        "central_manifest_rows": len(manifest),
        "export_attempts_report": str(attempts_path) if attempts_path.is_file() else "",
        "participants": list({r.participant_id for r in results}),
        "n_comparisons_attempted": len(results),
        "n_completed": sum(1 for r in results if r.status == STATUS_COMPLETED),
    }
    pd.DataFrame([batch_manifest]).to_csv(batch_root / "batch_manifest.csv", index=False)

    completed = sum(1 for r in results if r.status == STATUS_COMPLETED)
    lines = [
        "# Gaga JcvPCA batch summary",
        "",
        f"- Batch folder: `{batch_root}`",
        f"- Central manifest rows: {len(manifest)}",
        f"- Comparisons attempted: {len(results)}",
        f"- Completed: {completed}",
        "",
        "## Status counts",
        "",
    ]
    for status, count in pd.Series([r.status for r in results]).value_counts().items():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Notes", "", "Numerical outputs only. No scientific conclusions.", ""])
    (batch_root / "batch_summary.md").write_text("\n".join(lines), encoding="utf-8")
