"""Shared controller for pre-JcvPCA review (notebook + web dashboard)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from pre_jvcpca_review.build import build_full_review, build_mapping_only
from pre_jvcpca_review.canonical_manifest import (
    DEFAULT_PILOT_MANIFEST,
    ManifestError,
    load_pilot_manifest,
    pilot_feature_order,
    pilot_link_order,
    resolve_session_links_from_manifest,
)
from pre_jvcpca_review.discovery import resolve_layer2
from pre_jvcpca_review.exercise_segments import (
    GROUP4_LABEL,
    ExerciseSegment,
    exercise_choice_label,
    group4_window,
    load_exercise_segments,
    load_exercise_segments_bytes,
    make_window_label,
)
from pre_jvcpca_review.export_constants import MATRIX_IDENTITY_COLUMNS
from pre_jvcpca_review.export_window import export_layer3_window
from pre_jvcpca_review.feature_scope import FeatureScopeConfig, load_feature_scope
from pre_jvcpca_review.joint_body_sections import (
    BODY_SECTION_ALL,
    classify_link_body_section,
    link_matches_body_section,
)
from pre_jvcpca_review.joint_overlap import (
    DIRECT,
    canonical_names_to_link_tuples,
    classify_links,
    emit_joint_comparability_warnings,
    non_comparable_required_features,
    overlap_dataframe,
    write_joint_overlap_table,
)
from pre_jvcpca_review.load_layer2 import LinkRecord, load_link_manifest
from pre_jvcpca_review.notebook_ui import canonical_joint_label
from pre_jvcpca_review.pairing import run_pairing_gate
from pre_jvcpca_review.review_output import (
    participant_out_dir,
    require_review_context,
    resolve_review_out_dir,
)
from pre_jvcpca_review.session_index import (
    DEFAULT_LAYER1_ROOT,
    DEFAULT_LAYER2_ROOT,
    build_session_index,
    participants,
    session_row,
    sessions_for,
    write_session_index,
)
from pre_jvcpca_review.warnings import WarningCollector

_PKG_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class JointOption:
    link_id: str
    label: str
    display_name: str
    feature_scope: str
    is_core: bool
    classification: str = ""
    is_directly_comparable: bool = False
    body_section: str = BODY_SECTION_ALL


@dataclass
class WarningSummary:
    has_blocking: bool
    requires_user_approval: bool
    n_blocking: int
    n_strong_warning: int
    n_warning: int
    n_info: int
    dataframe: pd.DataFrame


@dataclass
class DiscoverResult:
    session_index: pd.DataFrame
    participant_ids: list[str]
    n_matched: int
    index_path: Path


@dataclass
class ExportResultView:
    status: str
    message: str
    paths: dict[str, str] = field(default_factory=dict)
    manifest: dict[str, Any] = field(default_factory=dict)
    matrix_preview: pd.DataFrame | None = None
    warnings_csv: str = ""


class PreJcvpcaReviewController:
    """Orchestrates discovery, warnings, diagnostics, and Layer 3 export."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else _PKG_ROOT
        self.scope: FeatureScopeConfig = load_feature_scope()
        self.pilot_manifest = load_pilot_manifest(DEFAULT_PILOT_MANIFEST)
        self.canonical_feature_order = pilot_feature_order(self.pilot_manifest)
        self.required_links = pilot_link_order(self.pilot_manifest)

        self.session_index: pd.DataFrame | None = None
        self.current_row: pd.Series | None = None
        self.current_overlap: pd.DataFrame | None = None
        self.joint_options: list[JointOption] = []
        self._links: list[LinkRecord] = []
        self._pilot_link_ids: set[str] = set()
        self.exercise_catalog: dict[str, list[ExerciseSegment]] = {}

    @property
    def default_layer1_root(self) -> Path:
        return DEFAULT_LAYER1_ROOT

    @property
    def default_layer2_root(self) -> Path:
        return DEFAULT_LAYER2_ROOT

    @property
    def default_output_root(self) -> Path:
        return self.project_root / "outputs" / "pre_jvcpca_review"

    @property
    def default_exercise_segments(self) -> Path:
        return self.project_root / "671_ex_segmentatios_frames.xlsx"

    def load_exercise_catalog(self, path: Path) -> dict[str, list[ExerciseSegment]]:
        self.exercise_catalog = load_exercise_segments(path)
        return self.exercise_catalog

    def load_exercise_catalog_bytes(
        self,
        data: bytes,
        filename: str,
    ) -> dict[str, list[ExerciseSegment]]:
        self.exercise_catalog = load_exercise_segments_bytes(data, filename)
        return self.exercise_catalog

    def exercises_for_session(self, session_id: str) -> list[ExerciseSegment]:
        return list(self.exercise_catalog.get(session_id, []))

    @staticmethod
    def build_window_label(
        session_id: str,
        start_frame: int,
        end_frame: int,
        *,
        tag: str = "",
    ) -> str:
        return make_window_label(session_id, start_frame, end_frame, tag=tag)

    def apply_exercise_selection(
        self,
        session_id: str,
        choice_key: str,
    ) -> tuple[int, int, str] | None:
        segments = self.exercises_for_session(session_id)
        if not segments:
            return None
        if choice_key == GROUP4_LABEL:
            window = group4_window(segments)
            if window is None:
                return None
            start, end = window
            label = self.build_window_label(session_id, start, end, tag="g4")
            return start, end, label
        for segment in segments:
            key = exercise_choice_label(segment)
            if key == choice_key:
                label = self.build_window_label(session_id, segment.start_frame, segment.end_frame)
                return segment.start_frame, segment.end_frame, label
        return None

    @property
    def default_datadescriptions(self) -> Path:
        return (
            self.project_root
            / "reevluate_project"
            / "671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001_DataDescriptions.csv"
        )

    def discover(
        self,
        layer1_root: Path,
        layer2_root: Path,
        output_root: Path,
    ) -> DiscoverResult:
        index = build_session_index(layer1_root, layer2_root)
        if index.empty:
            raise ValueError("No sessions found under the given Layer 1 / Layer 2 roots.")
        index_path = output_root.parent / "session_index.csv"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        write_session_index(index, index_path)
        self.session_index = index
        pids = participants(index)
        return DiscoverResult(
            session_index=index,
            participant_ids=pids,
            n_matched=int(index["is_matched"].sum()),
            index_path=index_path,
        )

    def participant_sessions(self, participant_id: str) -> pd.DataFrame:
        if self.session_index is None:
            raise ValueError("Run discovery first.")
        return sessions_for(self.session_index, participant_id)

    def build_overlap_table(self, participant_id: str, output_root: Path) -> pd.DataFrame | None:
        if self.session_index is None:
            return None
        sess_df = sessions_for(self.session_index, participant_id)
        matched = sess_df[sess_df["is_matched"]]
        sess_links: dict[str, list[LinkRecord]] = {}
        for _, row in matched.iterrows():
            if not row["layer2_run_dir"]:
                continue
            try:
                layer2 = resolve_layer2(row["layer2_run_dir"])
                sess_links[row["session_id"]] = load_link_manifest(layer2.link_manifest)
            except Exception:
                continue
        if not sess_links:
            self.current_overlap = None
            return None
        rows = classify_links(sess_links, candidate_links=self.required_links)
        overlap = overlap_dataframe(rows, participant_id, list(sess_links))
        out_dir = participant_out_dir(output_root, participant_id)
        write_joint_overlap_table(overlap, out_dir / "joint_overlap_table.csv")
        self.current_overlap = overlap
        return overlap

    def select_session(self, session_id: str) -> pd.Series:
        if self.session_index is None:
            raise ValueError("Run discovery first.")
        row = session_row(self.session_index, session_id)
        self.current_row = row
        self.load_joints(str(row["layer2_run_dir"] or ""))
        return row

    def _overlap_classifications(self) -> dict[str, str]:
        if self.current_overlap is None:
            return {}
        return {
            str(row["canonical_link_name"]): str(row["classification"])
            for _, row in self.current_overlap.iterrows()
        }

    def _default_joint_ids(self, links: list[LinkRecord]) -> set[str]:
        try:
            pilot_ids, _ = resolve_session_links_from_manifest(self.pilot_manifest, links)
            return set(pilot_ids[:3])
        except ManifestError:
            core = [link.link_id for link in links if link.feature_scope == "core_candidate"]
            return set(core[:3])

    def default_selected_joint_ids(self) -> list[str]:
        if not self._links:
            return []
        return list(self._default_joint_ids(self._links))

    def load_joints(self, layer2_dir: str) -> list[JointOption]:
        if not layer2_dir.strip():
            self.joint_options = []
            self._links = []
            return []
        links = load_link_manifest(resolve_layer2(Path(layer2_dir)).link_manifest)
        self._links = links
        try:
            pilot_ids, _ = resolve_session_links_from_manifest(self.pilot_manifest, links)
            self._pilot_link_ids = set(pilot_ids)
        except ManifestError:
            self._pilot_link_ids = set()
        overlap = self._overlap_classifications()
        ordered = sorted(
            links,
            key=lambda link: (
                self.required_links.index((link.parent_canonical, link.child_canonical))
                if (link.parent_canonical, link.child_canonical) in self.required_links
                else len(self.required_links),
                link.display_name,
            ),
        )
        self.joint_options = [
            JointOption(
                link_id=link.link_id,
                label=canonical_joint_label(
                    link,
                    overlap_classification=overlap.get(link.display_name),
                ),
                display_name=link.display_name,
                feature_scope=link.feature_scope,
                is_core=link.feature_scope == "core_candidate",
                classification=overlap.get(link.display_name, ""),
                is_directly_comparable=overlap.get(link.display_name) == DIRECT,
                body_section=classify_link_body_section(link),
            )
            for link in ordered
        ]
        return self.joint_options

    def core_joint_ids(self) -> list[str]:
        return [opt.link_id for opt in self.joint_options if opt.is_core]

    def directly_comparable_joint_ids(self) -> list[str]:
        return [opt.link_id for opt in self.joint_options if opt.is_directly_comparable]

    def filtered_joint_options(
        self,
        *,
        core_only: bool = False,
        directly_comparable_only: bool = False,
        body_section: str = BODY_SECTION_ALL,
    ) -> list[JointOption]:
        visible: list[JointOption] = []
        for opt in self.joint_options:
            link = next((item for item in self._links if item.link_id == opt.link_id), None)
            if link is None:
                continue
            if core_only and not opt.is_core:
                continue
            if directly_comparable_only and not opt.is_directly_comparable:
                continue
            if not link_matches_body_section(
                link,
                body_section,
                pilot_link_ids=self._pilot_link_ids,
            ):
                continue
            visible.append(opt)
        return visible

    def review_out_dir(self, output_root: Path, window_label: str) -> Path:
        if self.current_row is None:
            return output_root / "_unset"
        return resolve_review_out_dir(
            output_root,
            str(self.current_row["participant_id"]),
            str(self.current_row["session_id"]),
            window_label,
        )

    def _warning_identity(self) -> dict[str, str]:
        if self.current_row is None:
            return {}
        return {
            "participant_id": str(self.current_row["participant_id"]),
            "session_id": str(self.current_row["session_id"]),
        }

    def _export_comparability_scope(self, selected_link_ids: list[str]) -> list[tuple[str, str]]:
        if selected_link_ids:
            names = [
                opt.display_name
                for opt in self.joint_options
                if opt.link_id in selected_link_ids
            ]
            return canonical_names_to_link_tuples(names)
        return list(self.required_links)

    def collect_warnings(self, selected_link_ids: list[str]) -> WarningCollector:
        collector = WarningCollector()
        if self.current_row is not None:
            run_pairing_gate(self.current_row, collector)
        if self.current_overlap is not None:
            emit_joint_comparability_warnings(
                collector,
                self.current_overlap,
                self._export_comparability_scope(selected_link_ids),
                **self._warning_identity(),
            )
        return collector

    def summarize_warnings(self, selected_link_ids: list[str]) -> WarningSummary:
        collector = self.collect_warnings(selected_link_ids)
        summary = collector.summary()
        df = collector.to_dataframe()
        display_cols = [
            c
            for c in (
                "severity",
                "category",
                "warning_id",
                "message",
                "recommended_action",
            )
            if c in df.columns
        ]
        return WarningSummary(
            has_blocking=bool(summary["has_blocking"]),
            requires_user_approval=bool(summary["requires_user_approval"]),
            n_blocking=int(summary["n_blocking"]),
            n_strong_warning=int(summary["n_strong_warning"]),
            n_warning=int(summary["n_warning"]),
            n_info=int(summary["n_info"]),
            dataframe=df[display_cols] if display_cols else df,
        )

    def non_comparable_features(self) -> list[str]:
        if self.current_overlap is None:
            return []
        return non_comparable_required_features(self.current_overlap, self.required_links)

    def run_mapping(
        self,
        *,
        layer1_dir: Path,
        layer2_dir: Path,
        output_root: Path,
        window_label: str,
        selected_link_ids: list[str],
        datadescriptions: Path | None,
    ) -> tuple[Path, pd.DataFrame]:
        ctx_err = require_review_context(
            current_row=self.current_row,
            layer1_dir=layer1_dir,
            layer2_dir=layer2_dir,
        )
        if ctx_err:
            raise ValueError(ctx_err)
        if not selected_link_ids:
            raise ValueError("Select at least one joint.")
        out = self.review_out_dir(output_root, window_label)
        out.mkdir(parents=True, exist_ok=True)
        mapping_path = build_mapping_only(
            layer1_dir,
            layer2_dir,
            out,
            datadescriptions if datadescriptions and datadescriptions.is_file() else None,
            selected_link_ids=selected_link_ids,
        )
        return mapping_path, pd.read_csv(mapping_path)

    def run_full_review(
        self,
        *,
        layer1_dir: Path,
        layer2_dir: Path,
        output_root: Path,
        window_label: str,
        frame_start: int,
        frame_end: int,
        selected_link_ids: list[str],
        qc_evidence: list[str],
        datadescriptions: Path | None,
    ) -> dict[str, Path]:
        ctx_err = require_review_context(
            current_row=self.current_row,
            layer1_dir=layer1_dir,
            layer2_dir=layer2_dir,
        )
        if ctx_err:
            raise ValueError(ctx_err)
        if not selected_link_ids:
            raise ValueError("Select at least one joint.")
        if not qc_evidence:
            raise ValueError("Select at least one QC evidence type.")
        out = self.review_out_dir(output_root, window_label)
        out.mkdir(parents=True, exist_ok=True)
        return build_full_review(
            layer1_dir=layer1_dir,
            layer2_dir=layer2_dir,
            out_dir=out,
            frame_start=frame_start,
            frame_end=frame_end,
            selected_link_ids=selected_link_ids,
            qc_evidence=qc_evidence,
            datadescriptions=(
                datadescriptions if datadescriptions and datadescriptions.is_file() else None
            ),
        )

    def export_window(
        self,
        *,
        layer1_dir: Path,
        layer2_dir: Path,
        output_root: Path,
        window_label: str,
        frame_start: int,
        frame_end: int,
        selected_link_ids: list[str],
        allow_nan_matrix: bool,
    ) -> ExportResultView:
        if self.current_row is None:
            raise ValueError("Select a participant and session first.")
        out = self.review_out_dir(output_root, window_label)
        scope = self._export_comparability_scope(selected_link_ids)
        result = export_layer3_window(
            layer1_dir,
            layer2_dir,
            out,
            frame_start,
            frame_end,
            session_row=self.current_row,
            window_label=window_label,
            allow_nan_matrix=allow_nan_matrix,
            overlap_df=self.current_overlap,
            scope_required_links=scope if selected_link_ids else None,
        )
        if result["status"] == "blocked":
            return ExportResultView(
                status="blocked",
                message="Export blocked by blocking warnings. No matrix written.",
                warnings_csv=str(result["warnings_csv"]),
            )
        paths = result["paths"]
        manifest = json.loads(Path(paths["manifest"]).read_text(encoding="utf-8"))
        matrix_df = pd.read_parquet(paths["jvcpca_matrix"])
        feature_cols = [c for c in matrix_df.columns if c not in MATRIX_IDENTITY_COLUMNS]
        preview_cols = MATRIX_IDENTITY_COLUMNS + feature_cols[: min(6, len(feature_cols))]
        return ExportResultView(
            status="ok",
            message="Layer 3-safe export complete.",
            paths={k: str(v) for k, v in paths.items()},
            manifest=manifest,
            matrix_preview=matrix_df[preview_cols].head(8),
        )

    def load_review_tables(
        self,
        output_root: Path,
        window_label: str,
    ) -> list[tuple[str, pd.DataFrame, int | None]]:
        from pre_jvcpca_review.review_display import DEFAULT_REVIEW_TABLES

        out = self.review_out_dir(output_root, window_label)
        loaded: list[tuple[str, pd.DataFrame, int | None]] = []
        for spec in DEFAULT_REVIEW_TABLES:
            path = out / spec.filename
            if not path.is_file():
                continue
            df = pd.read_csv(path)
            title = spec.title or spec.filename
            loaded.append((title, df, spec.max_rows))
        return loaded
