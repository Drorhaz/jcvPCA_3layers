"""Default feature-scope config loader (dependency-free YAML subset).

Reads ``config/default_feature_scope.yaml``. Only a tiny, flat subset of YAML is
supported (``key: value`` scalars and ``- item`` lists) so the program does not
depend on PyYAML. This keeps the default Layer 3 feature scope in config rather
than hard-coded in notebook cells.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

CONFIG_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEATURE_SCOPE_PATH = CONFIG_ROOT / "config" / "default_feature_scope.yaml"


@dataclass(frozen=True)
class FeatureScopeConfig:
    default_body_scope: str
    exclude_fingers: bool
    exclude_toes: bool
    core_link_set_name: str
    allowed_feature_scope: str
    feature_naming_policy: str
    feature_manifest: Path
    excluded_child_prefixes: tuple[str, ...] = field(default_factory=tuple)
    source_path: Path = DEFAULT_FEATURE_SCOPE_PATH


def _parse_simple_yaml(text: str) -> dict[str, object]:
    """Parse a minimal flat YAML subset: scalars and single-level '- ' lists."""
    data: dict[str, object] = {}
    current_list_key: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line.lstrip().startswith("- ") and current_list_key is not None:
            item = line.lstrip()[2:].strip()
            data[current_list_key].append(item)  # type: ignore[union-attr]
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.split("#", 1)[0].strip()
        if value == "":
            data[key] = []
            current_list_key = key
        else:
            data[key] = value
            current_list_key = None
    return data


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"true", "1", "yes"}


def load_feature_scope(path: Path | None = None) -> FeatureScopeConfig:
    cfg_path = Path(path) if path else DEFAULT_FEATURE_SCOPE_PATH
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Feature scope config not found: {cfg_path}")
    raw = _parse_simple_yaml(cfg_path.read_text(encoding="utf-8"))

    manifest_value = str(raw.get("feature_manifest", "")).strip()
    manifest_path = Path(manifest_value)
    if not manifest_path.is_absolute():
        manifest_path = (CONFIG_ROOT / manifest_path).resolve()

    excluded = raw.get("excluded_child_prefixes", [])
    if not isinstance(excluded, list):
        excluded = [str(excluded)]

    return FeatureScopeConfig(
        default_body_scope=str(raw.get("default_body_scope", "upper_body_core")),
        exclude_fingers=_as_bool(raw.get("exclude_fingers"), True),
        exclude_toes=_as_bool(raw.get("exclude_toes"), True),
        core_link_set_name=str(raw.get("core_link_set_name", "group4_upper_body_pilot")),
        allowed_feature_scope=str(raw.get("allowed_feature_scope", "core_candidate")),
        feature_naming_policy=str(
            raw.get("feature_naming_policy", "canonical_parent_child_axis")
        ),
        feature_manifest=manifest_path,
        excluded_child_prefixes=tuple(str(p) for p in excluded),
        source_path=cfg_path,
    )
