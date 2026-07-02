"""Load, validate, hash, and snapshot the governed threshold registry.

Initial governed registry (G1): full Layer 3 coverage in ``analysis_params.yaml``;
curated L1/L2/L2.5 subset in ``qc_rules.yaml`` — NOT complete all-layer coverage.
See ``docs/research_recovery/G1_REVIEW_ADDENDUM.md``.

Design goals (PROGRAM_GUI_OPTIMIZATION.md Section 4):
  * Fail-fast validation of every ``value`` against declared bounds.
  * Stable ``science_hash`` (excludes GUI display settings) for provenance.
  * ``write_snapshot`` + cross-layer ``invalidates`` lookup.

Stdlib + PyYAML only. Does not import layer analysis packages.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment-specific
    raise ImportError(
        "analysis_config requires PyYAML. Install it in the active environment."
    ) from exc

# Files that contribute to the SCIENCE config hash (affect results).
SCIENCE_CONFIG_FILES = (
    "analysis_params.yaml",
    "qc_rules.yaml",
    "segment_selection.yaml",
)
# Display-only file (own hash; never invalidates results).
DISPLAY_CONFIG_FILE = "gui_settings.yaml"
ALL_CONFIG_FILES = (*SCIENCE_CONFIG_FILES, DISPLAY_CONFIG_FILE)

# Keys that are structural metadata, never threshold entries.
_NON_THRESHOLD_KEYS = {"version", "source_config", "presets"}


class ConfigValidationError(ValueError):
    """Raised when one or more threshold values violate their declared bounds."""


@dataclass(frozen=True)
class Threshold:
    """One governed threshold entry with its rich schema."""

    key: str  # dotted path, e.g. "pca.variance_threshold"
    file: str  # source config file name
    value: Any
    default: Any = None
    allowed_range: tuple[float, float] | None = None
    allowed_values: list[Any] | None = None
    description: str = ""
    scientific_meaning: str = ""
    gui_editable: bool = False
    locked_by_scope: bool = False
    requires_approval: bool = False
    invalidates: tuple[str, ...] = ()
    affects: tuple[str, ...] = ()
    regenerate_after_change: tuple[str, ...] = ()
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def differs_from_default(self) -> bool:
        return self.default is not None and self.value != self.default

    @property
    def scope_approved_value(self) -> Any:
        return self.raw.get("scope_approved_value")

    @property
    def canonical_batch_value(self) -> Any:
        return self.raw.get("canonical_batch_value")

    @property
    def differs_from_scope_approved(self) -> bool:
        sav = self.scope_approved_value
        return sav is not None and self.value != sav

    @property
    def differs_from_canonical_batch(self) -> bool:
        cbv = self.canonical_batch_value
        return cbv is not None and self.value != cbv


def _find_project_root(start: Path | None = None) -> Path:
    anchor = (start or Path(__file__).resolve()).resolve()
    for candidate in (anchor, *anchor.parents):
        if (candidate / "config" / "analysis_params.yaml").is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate project root (missing config/analysis_params.yaml)."
    )


def _is_threshold_entry(node: Any) -> bool:
    return isinstance(node, Mapping) and "value" in node


def _iter_thresholds(
    node: Mapping[str, Any], prefix: tuple[str, ...] = ()
) -> Iterator[tuple[str, Mapping[str, Any]]]:
    """Yield (dotted_key, entry_mapping) for every threshold entry in a config tree."""
    for key, val in node.items():
        if key in _NON_THRESHOLD_KEYS:
            continue
        parts = (*prefix, key)
        if _is_threshold_entry(val):
            yield ".".join(parts), val
        elif isinstance(val, Mapping):
            yield from _iter_thresholds(val, parts)


def _coerce_range(rng: Any) -> tuple[float, float] | None:
    if isinstance(rng, (list, tuple)) and len(rng) == 2:
        return float(rng[0]), float(rng[1])
    return None


def _build_threshold(key: str, file: str, entry: Mapping[str, Any]) -> Threshold:
    return Threshold(
        key=key,
        file=file,
        value=entry.get("value"),
        default=entry.get("default"),
        allowed_range=_coerce_range(entry.get("allowed_range")),
        allowed_values=entry.get("allowed_values"),
        description=str(entry.get("description", "")),
        scientific_meaning=str(entry.get("scientific_meaning", "")),
        gui_editable=bool(entry.get("gui_editable", False)),
        locked_by_scope=bool(entry.get("locked_by_scope", False)),
        requires_approval=bool(entry.get("requires_approval", False)),
        invalidates=tuple(entry.get("invalidates", []) or []),
        affects=tuple(entry.get("affects", []) or []),
        regenerate_after_change=tuple(entry.get("regenerate_after_change", []) or []),
        raw=dict(entry),
    )


def _get_entry_at_key(tree: Mapping[str, Any], dotted_key: str) -> Mapping[str, Any]:
    cur: Any = tree
    for part in dotted_key.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            raise KeyError(f"Unknown threshold key: {dotted_key}")
        cur = cur[part]
    if not _is_threshold_entry(cur):
        raise KeyError(f"Not a threshold entry: {dotted_key}")
    return cur


def _set_entry_value(tree: dict[str, Any], dotted_key: str, new_value: Any) -> Any:
    parts = dotted_key.split(".")
    cur: Any = tree
    for part in parts[:-1]:
        cur = cur[part]
    leaf = cur[parts[-1]]
    if not _is_threshold_entry(leaf):
        raise KeyError(f"Not a threshold entry: {dotted_key}")
    old_value = leaf.get("value")
    leaf["value"] = new_value
    return old_value


def _validate_threshold(t: Threshold) -> list[str]:
    """Return a list of human-readable violation messages (empty when valid)."""
    problems: list[str] = []
    values = t.value if isinstance(t.value, list) else [t.value]

    if t.allowed_range is not None:
        lo, hi = t.allowed_range
        for v in values:
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                problems.append(f"{t.key}: value {v!r} is not numeric for allowed_range")
            elif not (lo <= float(v) <= hi):
                problems.append(f"{t.key}: value {v} outside allowed_range [{lo}, {hi}]")

    if t.allowed_values is not None:
        for v in values:
            if v not in t.allowed_values:
                problems.append(
                    f"{t.key}: value {v!r} not in allowed_values {t.allowed_values}"
                )
    return problems


@dataclass
class AnalysisConfig:
    """Resolved, validated threshold registry."""

    project_root: Path
    config_dir: Path
    thresholds: dict[str, Threshold]
    raw_by_file: dict[str, Any]

    @classmethod
    def load(
        cls,
        config_dir: Path | None = None,
        project_root: Path | None = None,
        validate: bool = True,
    ) -> AnalysisConfig:
        root = (project_root or _find_project_root()).resolve()
        cfg_dir = (config_dir or (root / "config")).resolve()

        raw_by_file: dict[str, Any] = {}
        thresholds: dict[str, Threshold] = {}
        for fname in ALL_CONFIG_FILES:
            path = cfg_dir / fname
            if not path.is_file():
                raise FileNotFoundError(f"Missing config file: {path}")
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            raw_by_file[fname] = data
            for key, entry in _iter_thresholds(data):
                if key in thresholds:
                    raise ConfigValidationError(
                        f"Duplicate threshold key {key!r} "
                        f"(in {thresholds[key].file} and {fname})"
                    )
                thresholds[key] = _build_threshold(key, fname, entry)

        obj = cls(
            project_root=root,
            config_dir=cfg_dir,
            thresholds=thresholds,
            raw_by_file=raw_by_file,
        )
        if validate:
            obj.validate()
        return obj

    def validate(self) -> None:
        problems: list[str] = []
        for t in self.thresholds.values():
            problems.extend(_validate_threshold(t))
        if problems:
            raise ConfigValidationError(
                "Threshold validation failed:\n  - " + "\n  - ".join(problems)
            )

    def get(self, dotted_key: str) -> Any:
        if dotted_key not in self.thresholds:
            raise KeyError(f"Unknown threshold key: {dotted_key}")
        return self.thresholds[dotted_key].value

    def get_threshold(self, dotted_key: str) -> Threshold:
        if dotted_key not in self.thresholds:
            raise KeyError(f"Unknown threshold key: {dotted_key}")
        return self.thresholds[dotted_key]

    # --- Hashing (provenance) ------------------------------------------------
    def _values_for_files(self, files: tuple[str, ...]) -> dict[str, Any]:
        return {
            t.key: t.value
            for t in sorted(self.thresholds.values(), key=lambda x: x.key)
            if t.file in files
        }

    def _hash_of(self, files: tuple[str, ...]) -> str:
        payload = json.dumps(
            self._values_for_files(files), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def science_hash(self) -> str:
        """Hash over result-affecting thresholds (excludes GUI display settings)."""
        return self._hash_of(SCIENCE_CONFIG_FILES)

    @property
    def display_hash(self) -> str:
        return self._hash_of((DISPLAY_CONFIG_FILE,))

    def is_comparable_to(self, other_science_hash: str) -> bool:
        return self.science_hash == other_science_hash

    # --- Invalidation graph --------------------------------------------------
    def invalidates_for(self, dotted_key: str) -> tuple[str, ...]:
        return self.get_threshold(dotted_key).invalidates

    def invalidated_by_changes(self, changed_keys: list[str]) -> set[str]:
        """Union of output classes invalidated by changing the given thresholds."""
        out: set[str] = set()
        for k in changed_keys:
            out.update(self.get_threshold(k).invalidates)
        return out

    # --- Snapshot ------------------------------------------------------------
    def write_snapshot(self, dest_dir: Path) -> Path:
        """Freeze the exact config into ``dest_dir/_config_snapshot/`` and return it."""
        snap = Path(dest_dir) / "_config_snapshot"
        snap.mkdir(parents=True, exist_ok=True)
        for fname in ALL_CONFIG_FILES:
            shutil.copy2(self.config_dir / fname, snap / fname)
        meta = {
            "science_hash": self.science_hash,
            "display_hash": self.display_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config_files": list(ALL_CONFIG_FILES),
        }
        (snap / "config_hash.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        return snap

    def apply_threshold_update(
        self,
        dotted_key: str,
        new_value: Any,
        *,
        reason: str,
        changed_by: str = "gui",
        force_scope_unlock: bool = False,
        approved: bool = False,
    ) -> tuple[Threshold, dict[str, Any]]:
        """Validate, persist, and audit one ``gui_editable`` threshold change (G6)."""
        if not reason.strip():
            raise ConfigValidationError("Threshold update requires a non-empty reason.")

        threshold = self.get_threshold(dotted_key)
        if not threshold.gui_editable:
            raise ConfigValidationError(f"{dotted_key} is not gui_editable.")
        if threshold.locked_by_scope and not force_scope_unlock:
            raise ConfigValidationError(
                f"{dotted_key} is locked_by_scope; explicit scope unlock required."
            )
        if threshold.requires_approval and not approved:
            raise ConfigValidationError(
                f"{dotted_key} requires explicit approval before change."
            )

        old_value = threshold.value
        science_hash_before = self.science_hash
        tree = self.raw_by_file[threshold.file]
        _set_entry_value(tree, dotted_key, new_value)
        entry = _get_entry_at_key(tree, dotted_key)
        candidate = _build_threshold(dotted_key, threshold.file, entry)
        problems = _validate_threshold(candidate)
        if problems:
            _set_entry_value(tree, dotted_key, old_value)
            raise ConfigValidationError(
                "Threshold validation failed:\n  - " + "\n  - ".join(problems)
            )

        path = self.config_dir / threshold.file
        path.write_text(
            yaml.safe_dump(tree, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        self.thresholds[dotted_key] = candidate

        audit_record = {
            "action": "threshold_update",
            "key": dotted_key,
            "file": threshold.file,
            "old_value": old_value,
            "new_value": new_value,
            "reason": reason.strip(),
            "changed_by": changed_by,
            "force_scope_unlock": force_scope_unlock,
            "approved": approved,
            "science_hash_before": science_hash_before,
            "science_hash_after": self.science_hash,
            "invalidates": list(candidate.invalidates),
        }
        from g6_execution import append_change_audit_log

        append_change_audit_log(self.project_root, audit_record)
        return candidate, audit_record


def load_analysis_config(
    config_dir: Path | None = None,
    project_root: Path | None = None,
    validate: bool = True,
) -> AnalysisConfig:
    """Load and validate the governed threshold registry."""
    return AnalysisConfig.load(
        config_dir=config_dir, project_root=project_root, validate=validate
    )
