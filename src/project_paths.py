"""Load and validate canonical paths from ``config/paths.yaml``.

This module is intentionally lightweight: stdlib + PyYAML only. It does not
import Layer 2/2.5/3 analysis packages.

Location: ``src/project_paths.py`` at repository root (no root package existed
before R6; layer-specific code lives under ``Layer*/src/``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment-specific
    yaml = None  # type: ignore[assignment]
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None

DEFAULT_CONFIG_REL = Path("config") / "paths.yaml"


class PathRequirement(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    METADATA = "metadata"  # non-path values (IDs, participant lists)


@dataclass(frozen=True)
class PathEntry:
    """One registry entry with resolved absolute path and validation policy."""

    dotted_key: str
    raw_value: str
    resolved: Path | None
    requirement: PathRequirement
    is_glob: bool = False

    def exists(self) -> bool:
        if self.resolved is None or self.is_glob:
            return False
        return self.resolved.exists()


@dataclass(frozen=True)
class PathValidationIssue:
    dotted_key: str
    requirement: PathRequirement
    resolved: Path | None
    message: str

    @property
    def is_error(self) -> bool:
        return self.requirement == PathRequirement.REQUIRED


@dataclass(frozen=True)
class PathValidationResult:
    issues: tuple[PathValidationIssue, ...]

    @property
    def errors(self) -> tuple[PathValidationIssue, ...]:
        return tuple(i for i in self.issues if i.is_error)

    @property
    def warnings(self) -> tuple[PathValidationIssue, ...]:
        return tuple(i for i in self.issues if not i.is_error)

    @property
    def ok(self) -> bool:
        return not self.errors


# Registry policy: which YAML leaves are paths and how strictly to check them.
_PATH_REGISTRY: dict[tuple[str, ...], tuple[PathRequirement, bool]] = {
    # (section, ...keys): (requirement, is_glob)
    ("project", "root"): (PathRequirement.METADATA, False),
    ("raw_data", "layer1"): (PathRequirement.REQUIRED, False),
    ("raw_data", "layer2"): (PathRequirement.REQUIRED, False),
    ("raw_data", "layer2_5_descriptions"): (PathRequirement.REQUIRED, False),
    ("raw_data", "root_test_exports"): (PathRequirement.OPTIONAL, False),
    ("layer2", "active_outputs"): (PathRequirement.REQUIRED, False),
    ("layer2", "active_session_glob"): (PathRequirement.OPTIONAL, True),
    ("layer2", "layer2_exports"): (PathRequirement.OPTIONAL, False),
    ("layer2", "stage_indices"): (PathRequirement.OPTIONAL, True),
    ("layer2", "historical_archive_external"): (PathRequirement.OPTIONAL, False),
    ("layer2_5", "pre_jvcpca_review"): (PathRequirement.REQUIRED, False),
    ("layer2_5", "pre_jvcpca_archive_snapshot"): (PathRequirement.OPTIONAL, False),
    ("layer2_5", "segmentation_xlsx"): (PathRequirement.REQUIRED, False),
    ("layer2_5", "config_manifests"): (PathRequirement.REQUIRED, False),
    ("layer3", "outputs_root"): (PathRequirement.REQUIRED, False),
    ("layer3", "canonical_batch_id"): (PathRequirement.METADATA, False),
    ("layer3", "canonical_batch"): (PathRequirement.REQUIRED, False),
    ("layer3", "poster_evidence_package"): (PathRequirement.OPTIONAL, False),
    ("layer3", "scripts"): (PathRequirement.REQUIRED, False),
    ("layer3", "src"): (PathRequirement.REQUIRED, False),
    ("poster", "final_figures"): (PathRequirement.OPTIONAL, False),
    ("results", "active"): (PathRequirement.OPTIONAL, False),
    ("results", "poster"): (PathRequirement.OPTIONAL, False),
    ("results", "manuscript"): (PathRequirement.OPTIONAL, False),
    ("results", "reports"): (PathRequirement.OPTIONAL, False),
    ("results", "archive_index"): (PathRequirement.OPTIONAL, False),
    ("external_archive", "parent"): (PathRequirement.OPTIONAL, False),
    ("external_archive", "cleanup_stage_b"): (PathRequirement.OPTIONAL, False),
    ("external_archive", "layer2_outputs_archive"): (PathRequirement.OPTIONAL, False),
}


def _require_yaml() -> Any:
    if yaml is None:
        return None
    return yaml


def _strip_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _parse_paths_yaml_minimal(text: str) -> dict[str, Any]:
    """Parse the flat/nested subset used by ``config/paths.yaml`` without PyYAML."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    active_list: tuple[dict[str, Any], str] | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip())
        content = line.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
            active_list = None

        parent = stack[-1][1]

        if content.startswith("- "):
            if active_list is None:
                continue
            list_parent, list_key = active_list
            item = _strip_yaml_scalar(content[2:].strip())
            cast = list_parent[list_key]
            if isinstance(cast, list):
                cast.append(item)
            continue

        if ":" not in content:
            continue

        key, _, value = content.partition(":")
        key = key.strip()
        value = _strip_yaml_scalar(value)

        if value == "":
            if key in {"scripts", "batch_cohort"}:
                parent[key] = []
                active_list = (parent, key)
            else:
                parent[key] = {}
                stack.append((indent, parent[key]))
                active_list = None
        else:
            parent[key] = value
            active_list = None

    return root


def find_project_root(start: Path | None = None) -> Path:
    """Return repository root containing ``config/paths.yaml``."""
    anchor = (start or Path(__file__).resolve()).resolve()
    candidates = [anchor, *anchor.parents]
    for candidate in candidates:
        if (candidate / DEFAULT_CONFIG_REL).is_file():
            return candidate
    searched = ", ".join(str(p) for p in candidates[:6])
    raise FileNotFoundError(
        f"Could not locate project root (missing {DEFAULT_CONFIG_REL}). "
        f"Searched: {searched}"
    )


def default_config_path(project_root: Path | None = None) -> Path:
    root = project_root or find_project_root()
    return root / DEFAULT_CONFIG_REL


def _dotted_key(parts: Iterable[str]) -> str:
    return ".".join(parts)


def _resolve_path(project_root: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (project_root / path).resolve()


def _iter_registry_leaves(
    data: Mapping[str, Any],
    prefix: tuple[str, ...] = (),
) -> Iterator[tuple[tuple[str, ...], Any]]:
    for key, value in data.items():
        parts = (*prefix, key)
        if isinstance(value, Mapping):
            yield from _iter_registry_leaves(value, parts)
        elif isinstance(value, list):
            if parts == ("poster", "scripts"):
                for item in value:
                    yield (parts, item)
            elif parts == ("participants", "batch_cohort"):
                continue
            else:
                yield (parts, value)
        else:
            yield (parts, value)


def load_paths_yaml(config_path: Path | None = None) -> dict[str, Any]:
    """Load raw YAML mapping from ``config/paths.yaml``."""
    path = config_path or default_config_path()
    if not path.is_file():
        raise FileNotFoundError(f"Path registry not found: {path}")
    text = path.read_text(encoding="utf-8")

    yaml_module = _require_yaml()
    if yaml_module is not None:
        loaded = yaml_module.safe_load(text)
    else:
        loaded = _parse_paths_yaml_minimal(text)

    if not isinstance(loaded, dict):
        raise ValueError(f"Expected mapping in {path}, got {type(loaded).__name__}")
    return loaded


@dataclass
class ProjectPaths:
    """Resolved path registry for the 3Layers project."""

    project_root: Path
    config_path: Path
    data: dict[str, Any]
    entries: dict[str, PathEntry]
    used_minimal_yaml_parser: bool = False

    @classmethod
    def load(
        cls,
        config_path: Path | None = None,
        project_root: Path | None = None,
    ) -> ProjectPaths:
        root = (project_root or find_project_root(config_path)).resolve()
        cfg = (config_path or (root / DEFAULT_CONFIG_REL)).resolve()
        text = cfg.read_text(encoding="utf-8")
        yaml_module = _require_yaml()
        if yaml_module is not None:
            raw_obj = yaml_module.safe_load(text)
            used_minimal = False
        else:
            raw_obj = _parse_paths_yaml_minimal(text)
            used_minimal = True
        if not isinstance(raw_obj, dict):
            raise ValueError(f"Expected mapping in {cfg}, got {type(raw_obj).__name__}")
        raw = raw_obj
        entries: dict[str, PathEntry] = {}

        for parts, value in _iter_registry_leaves(raw):
            dotted = _dotted_key(parts)
            if parts in _PATH_REGISTRY:
                requirement, is_glob = _PATH_REGISTRY[parts]
            elif parts[:1] == ("poster",) and parts[-1:] != ("scripts",):
                requirement, is_glob = PathRequirement.OPTIONAL, False
            else:
                requirement, is_glob = PathRequirement.METADATA, False

            if requirement == PathRequirement.METADATA or not isinstance(value, str):
                continue

            resolved = _resolve_path(root, value)
            entries[dotted] = PathEntry(
                dotted_key=dotted,
                raw_value=value,
                resolved=resolved,
                requirement=requirement,
                is_glob=is_glob,
            )

        return cls(
            project_root=root,
            config_path=cfg,
            data=raw,
            entries=entries,
            used_minimal_yaml_parser=used_minimal,
        )

    def get(self, dotted_key: str) -> Path:
        """Return resolved path for ``dotted_key`` (e.g. ``layer3.canonical_batch``)."""
        entry = self.entries.get(dotted_key)
        if entry is None or entry.resolved is None:
            raise KeyError(f"Unknown or non-path registry key: {dotted_key}")
        return entry.resolved

    def get_str(self, dotted_key: str) -> str:
        """Return a scalar string from raw YAML (e.g. ``layer3.canonical_batch_id``)."""
        node: Any = self.data
        for part in dotted_key.split("."):
            if not isinstance(node, Mapping) or part not in node:
                raise KeyError(f"Unknown registry key: {dotted_key}")
            node = node[part]
        if not isinstance(node, str):
            raise TypeError(f"Registry key {dotted_key!r} is not a string")
        return node

    def validate(self) -> PathValidationResult:
        """Check existence of registry paths; glob patterns match optionally."""
        issues: list[PathValidationIssue] = []

        for entry in self.entries.values():
            if entry.requirement == PathRequirement.METADATA:
                continue

            if entry.is_glob:
                if entry.resolved is None:
                    continue
                parent = entry.resolved.parent
                pattern = entry.resolved.name
                if not parent.is_dir():
                    issues.append(
                        PathValidationIssue(
                            dotted_key=entry.dotted_key,
                            requirement=PathRequirement.OPTIONAL,
                            resolved=entry.resolved,
                            message=f"parent directory missing for glob pattern: {parent}",
                        )
                    )
                    continue
                matches = list(parent.glob(pattern))
                if not matches:
                    issues.append(
                        PathValidationIssue(
                            dotted_key=entry.dotted_key,
                            requirement=PathRequirement.OPTIONAL,
                            resolved=entry.resolved,
                            message=f"no matches for glob {entry.raw_value!r} under {parent}",
                        )
                    )
                continue

            if entry.resolved is None:
                continue

            if entry.resolved.exists():
                continue

            issues.append(
                PathValidationIssue(
                    dotted_key=entry.dotted_key,
                    requirement=entry.requirement,
                    resolved=entry.resolved,
                    message="path does not exist",
                )
            )

        return PathValidationResult(issues=tuple(issues))

    def require_existing(self, dotted_key: str) -> Path:
        """Return path or raise ``FileNotFoundError`` with a helpful message."""
        path = self.get(dotted_key)
        if not path.exists():
            raise FileNotFoundError(
                f"Required project path missing for {dotted_key!r}: {path}\n"
                f"Config: {self.config_path}\n"
                f"Project root: {self.project_root}"
            )
        return path

    # Convenience aliases for common canonical paths (future script refactor targets).
    @property
    def layer3_canonical_batch(self) -> Path:
        return self.get("layer3.canonical_batch")

    @property
    def layer3_canonical_batch_id(self) -> str:
        return self.get_str("layer3.canonical_batch_id")

    @property
    def layer2_5_pre_jvcpca_review(self) -> Path:
        return self.get("layer2_5.pre_jvcpca_review")

    @property
    def poster_final_figures(self) -> Path:
        return self.get("poster.final_figures")

    @property
    def poster_evidence_package(self) -> Path:
        return self.get("layer3.poster_evidence_package")

    @property
    def external_archive_parent(self) -> Path:
        return self.get("external_archive.parent")


def load_project_paths(
    config_path: Path | None = None,
    project_root: Path | None = None,
) -> ProjectPaths:
    """Load and resolve all registry paths relative to the project root."""
    return ProjectPaths.load(config_path=config_path, project_root=project_root)
