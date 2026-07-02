"""G1 tests for the governed threshold registry (src/analysis_config.py).

Proves:
  * config loads and validates;
  * Layer 3 registry values reproduce the current hardcoded Python constants
    (bit-for-bit) — both against known literals and, when importable, against
    the live constants;
  * L1/L2/L2.5 registry values mirror their source config files (Option A);
  * fail-fast validation rejects out-of-range values;
  * the science hash excludes GUI display settings;
  * snapshot + invalidation behave as specified.

Runnable with any Python that has PyYAML (e.g. a layer .venv).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from analysis_config import (  # noqa: E402
    ConfigValidationError,
    load_analysis_config,
)


@pytest.fixture(scope="module")
def cfg():
    return load_analysis_config(project_root=REPO_ROOT)


# --- Load + validate ---------------------------------------------------------
def test_config_loads_and_validates(cfg):
    assert cfg.thresholds  # non-empty
    cfg.validate()  # must not raise


# --- Layer 3: reproduce hardcoded constants (literals) -----------------------
def test_layer3_values_match_expected_literals(cfg):
    assert cfg.get("pca.variance_threshold") == 0.80
    assert cfg.get("pca.min_pcs") == 2
    assert cfg.get("pca.max_pcs") == 10
    assert cfg.get("pc_focus.cumulative_thresholds") == [0.50, 0.60]
    assert cfg.get("pc_focus.sensitivity_p_archived") == 2
    assert cfg.get("weighting.explained_variance_weighting") is False
    assert cfg.get("distribution.low_contribution_flag") == 0.02
    assert cfg.get("cohort.participants") == ["671", "252"]
    assert cfg.get("cohort.block_a") == ["P1", "P2", "P3", "P4", "P5"]
    assert cfg.get("cohort.block_b") == ["P3", "P4", "P5"]


# --- Layer 3: reproduce LIVE Python constants (skip if not importable) --------
def test_layer3_values_match_live_python_constants(cfg):
    sys.path.insert(0, str(REPO_ROOT / "Layer3_JcvPCA" / "src"))
    try:
        from layer3_jcvpca.jcvpca_trace import (
            DEFAULT_MAX_PCS,
            DEFAULT_MIN_PCS,
            DEFAULT_VARIANCE_THRESHOLD,
        )
        from layer3_jcvpca.gaga_batch_runner import (
            BLOCK_EXERCISES,
            SENSITIVITY_P,
            TARGET_PARTICIPANTS,
        )
    except Exception as exc:  # heavy deps may be absent in a minimal env
        pytest.skip(f"Layer 3 package not importable here: {exc}")

    assert cfg.get("pca.variance_threshold") == DEFAULT_VARIANCE_THRESHOLD
    assert cfg.get("pca.min_pcs") == DEFAULT_MIN_PCS
    assert cfg.get("pca.max_pcs") == DEFAULT_MAX_PCS
    assert cfg.get("pc_focus.sensitivity_p_archived") == SENSITIVITY_P
    assert cfg.get("cohort.participants") == list(TARGET_PARTICIPANTS)
    assert cfg.get("cohort.block_a") == BLOCK_EXERCISES["A"]
    assert cfg.get("cohort.block_b") == BLOCK_EXERCISES["B"]


# --- L1/L2/L2.5: mirror source config files ----------------------------------
def _find_leaf_values(node, leaf_name, found=None):
    if found is None:
        found = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == leaf_name and not isinstance(v, (dict, list)):
                found.append(v)
            _find_leaf_values(v, leaf_name, found)
    return found


def _get_by_dotted_path(node: dict, dotted: str):
    cur = node
    for part in dotted.split("."):
        cur = cur[part]
    return cur


@pytest.mark.parametrize(
    "registry_key, source_rel, source_path, expected",
    [
        ("layer1.min_marker_coverage_pct",
         "Layer1_motive_qc/motive_qc/config.yaml", "readiness.min_marker_coverage_pct", 90.0),
        ("layer1.max_missing_percent_pass",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "quality_labels.marker.clean.max_missing_percent", 1.0),
        ("layer1.max_missing_percent_warn",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "quality_labels.marker.minor_issue.max_missing_percent", 5.0),
        ("layer1.max_missing_percent_caution",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "quality_labels.marker.caution.max_missing_percent", 10.0),
        ("layer1.max_large_gaps_pass",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "quality_labels.marker.clean.max_large_gaps", 0),
        ("layer1.max_large_gaps_caution",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "quality_labels.marker.caution.max_large_gaps", 1),
        ("layer1.session_acceptable_max_labeled_missing_percent",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "quality_labels.session.acceptable_for_preprocessing.max_labeled_missing_percent", 5.0),
        ("layer1.session_caution_max_labeled_missing_percent",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "quality_labels.session.caution_for_preprocessing.max_labeled_missing_percent", 10.0),
        ("layer1.session_acceptable_max_large_gaps_labeled",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "quality_labels.session.acceptable_for_preprocessing.max_large_gaps_labeled", 0),
        ("layer1.session_caution_max_large_gaps_labeled",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "quality_labels.session.caution_for_preprocessing.max_large_gaps_labeled", 2),
        ("layer1.frame_caution_missing_labeled_percent",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "frame_qc_mask.caution_missing_labeled_percent", 10.0),
        ("layer1.frame_exclude_missing_labeled_percent",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "frame_qc_mask.exclude_missing_labeled_percent", 20.0),
        ("layer1.velocity_percentile_threshold",
         "Layer1_motive_qc/motive_qc/config.yaml", "artifacts.velocity_percentile_threshold", 99.97),
        ("layer1.acceleration_percentile_threshold",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "artifacts.acceleration_percentile_threshold", 99.97),
        ("layer1.chosen_sigma",
         "Layer1_motive_qc/motive_qc/config.yaml",
         "artifacts.sigma_sensitivity.chosen_sigma", 8.0),
        ("layer2.rotvec_jump_warning_rad",
         "Layer2_Motive_Kinematics/configs/default_layer2_config.yaml", "rotvec.jump_warning_rad", 0.5),
        ("layer2.rotvec_near_pi_warning_fraction",
         "Layer2_Motive_Kinematics/configs/default_layer2_config.yaml",
         "rotvec.near_pi_warning_fraction", 0.95),
        ("layer2.quaternion_warning_max_abs_norm_error",
         "Layer2_Motive_Kinematics/configs/default_layer2_config.yaml",
         "quaternion_qc.warning_max_abs_norm_error", 0.01),
        ("layer2.rotvec_jump_fail_rad",
         "Layer2_Motive_Kinematics/configs/default_layer2_config.yaml", "rotvec.jump_fail_rad", 1.0),
        ("layer2.filtering_cutoff_hz",
         "Layer2_Motive_Kinematics/configs/default_layer2_config.yaml", "filtering.cutoff_hz", 10.0),
        ("layer2.jump_context_window_frames",
         "Layer2_Motive_Kinematics/configs/default_layer2_config.yaml",
         "filtering.jump_context_window_frames", 30),
        ("layer2.quaternion_pass_max_abs_norm_error",
         "Layer2_Motive_Kinematics/configs/default_layer2_config.yaml",
         "quaternion_qc.pass_max_abs_norm_error", 0.001),
        ("layer2_5.allowed_feature_scope",
         "Layer2.5_Segmentation/config/default_feature_scope.yaml",
         "allowed_feature_scope", "core_candidate"),
        ("layer2_5.exclude_fingers",
         "Layer2.5_Segmentation/config/default_feature_scope.yaml", "exclude_fingers", True),
        ("layer2_5.exclude_toes",
         "Layer2.5_Segmentation/config/default_feature_scope.yaml", "exclude_toes", True),
    ],
)
def test_registry_mirrors_source_configs(cfg, registry_key, source_rel, source_path, expected):
    assert cfg.get(registry_key) == expected
    source = yaml.safe_load((REPO_ROOT / source_rel).read_text(encoding="utf-8"))
    if "." in source_path:
        live = _get_by_dotted_path(source, source_path)
    else:
        live = source[source_path]
    assert live == expected


def test_g1_1_l1_gap_tiers_invalidate_downstream(cfg):
    t = cfg.get_threshold("layer1.max_missing_percent_caution")
    for tag in (
        "layer1_qc", "layer2_5_exports", "layer3_batches",
        "decision_summaries", "audit_reports", "exported_figures",
    ):
        assert tag in t.invalidates


def test_g1_1_l2_jump_window_invalidate_downstream(cfg):
    t = cfg.get_threshold("layer2.jump_context_window_frames")
    assert "layer2_5_exports" in t.invalidates
    assert "exported_figures" in t.invalidates
    assert "export_readiness" in t.affects


# --- Fail-fast validation ----------------------------------------------------
def test_out_of_range_value_fails(tmp_path):
    # Minimal config dir with one out-of-range threshold.
    (tmp_path / "analysis_params.yaml").write_text(
        "version: 1\npca:\n  variance_threshold:\n    value: 1.5\n"
        "    allowed_range: [0.5, 0.99]\n",
        encoding="utf-8",
    )
    for other in ("qc_rules.yaml", "segment_selection.yaml", "gui_settings.yaml"):
        (tmp_path / other).write_text("version: 1\n", encoding="utf-8")
    with pytest.raises(ConfigValidationError):
        load_analysis_config(config_dir=tmp_path, project_root=REPO_ROOT)


def test_disallowed_value_fails(tmp_path):
    (tmp_path / "analysis_params.yaml").write_text(
        "version: 1\nweighting:\n  explained_variance_weighting:\n    value: maybe\n"
        "    allowed_values: [true, false]\n",
        encoding="utf-8",
    )
    for other in ("qc_rules.yaml", "segment_selection.yaml", "gui_settings.yaml"):
        (tmp_path / other).write_text("version: 1\n", encoding="utf-8")
    with pytest.raises(ConfigValidationError):
        load_analysis_config(config_dir=tmp_path, project_root=REPO_ROOT)


# --- Hashing -----------------------------------------------------------------
def test_science_hash_excludes_gui_settings(cfg):
    science_keys = {
        t.key for t in cfg.thresholds.values()
        if t.file in ("analysis_params.yaml", "qc_rules.yaml", "segment_selection.yaml")
    }
    gui_keys = {t.key for t in cfg.thresholds.values() if t.file == "gui_settings.yaml"}
    assert science_keys and gui_keys
    assert cfg.science_hash != cfg.display_hash
    assert len(cfg.science_hash) == 64  # sha256 hex


def test_science_hash_is_deterministic(cfg):
    again = load_analysis_config(project_root=REPO_ROOT)
    assert cfg.science_hash == again.science_hash


# --- Snapshot ----------------------------------------------------------------
def test_write_snapshot(cfg, tmp_path):
    snap = cfg.write_snapshot(tmp_path)
    assert (snap / "analysis_params.yaml").is_file()
    assert (snap / "qc_rules.yaml").is_file()
    assert (snap / "gui_settings.yaml").is_file()
    meta = yaml.safe_load((snap / "config_hash.json").read_text(encoding="utf-8"))
    assert meta["science_hash"] == cfg.science_hash


# --- Invalidation + scope locks ----------------------------------------------
def test_invalidation_lookup(cfg):
    assert "layer3_batches" in cfg.invalidates_for("pca.variance_threshold")
    invalidated = cfg.invalidated_by_changes(
        ["pca.variance_threshold", "layer1.min_marker_coverage_pct"]
    )
    assert "layer3_batches" in invalidated
    assert "layer1_qc" in invalidated


def test_scope_locked_flags(cfg):
    for key in ("pca.centering", "pca.normalization"):
        t = cfg.get_threshold(key)
        assert t.locked_by_scope is True
        assert t.gui_editable is False


def test_variance_threshold_badge_metadata(cfg):
    t = cfg.get_threshold("pca.variance_threshold")
    assert t.value == 0.80
    assert t.scope_approved_value == 0.90
    assert t.canonical_batch_value == 0.80
    assert t.differs_from_scope_approved is True
    assert t.differs_from_canonical_batch is False
