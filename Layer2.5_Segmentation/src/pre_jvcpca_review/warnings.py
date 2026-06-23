"""Structured warning/alert records for Layer 2.5 (notebook + manifest)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

# Severity ladder (ascending). `blocking` must prevent export.
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_STRONG = "strong_warning"
SEVERITY_BLOCKING = "blocking"

SEVERITY_ORDER = {
    SEVERITY_INFO: 0,
    SEVERITY_WARNING: 1,
    SEVERITY_STRONG: 2,
    SEVERITY_BLOCKING: 3,
}

WARNING_COLUMNS = [
    "warning_id",
    "severity",
    "category",
    "participant_id",
    "session_id",
    "timepoint",
    "part_id",
    "repetition_id",
    "window_id",
    "start_frame",
    "end_frame",
    "canonical_link_name",
    "parent_canonical",
    "child_canonical",
    "axis",
    "affected_marker",
    "source_layer",
    "source_file",
    "message",
    "recommended_action",
    "blocks_export",
    "requires_user_approval",
    "evidence_file",
]


@dataclass
class WarningRecord:
    warning_id: str
    severity: str
    category: str
    message: str
    recommended_action: str = ""
    participant_id: str = ""
    session_id: str = ""
    timepoint: str = ""
    part_id: str = ""
    repetition_id: str = ""
    window_id: str = ""
    start_frame: int | str = ""
    end_frame: int | str = ""
    canonical_link_name: str = ""
    parent_canonical: str = ""
    child_canonical: str = ""
    axis: str = ""
    affected_marker: str = ""
    source_layer: str = ""
    source_file: str = ""
    evidence_file: str = ""

    @property
    def blocks_export(self) -> bool:
        return self.severity == SEVERITY_BLOCKING

    @property
    def requires_user_approval(self) -> bool:
        return self.severity == SEVERITY_STRONG

    def to_row(self) -> dict[str, object]:
        row = asdict(self)
        row["blocks_export"] = self.blocks_export
        row["requires_user_approval"] = self.requires_user_approval
        return {col: row.get(col, "") for col in WARNING_COLUMNS}


@dataclass
class WarningCollector:
    records: list[WarningRecord] = field(default_factory=list)

    def add(self, record: WarningRecord) -> None:
        self.records.append(record)

    def emit(self, warning_id: str, severity: str, category: str, message: str, **kw) -> None:
        self.add(
            WarningRecord(
                warning_id=warning_id,
                severity=severity,
                category=category,
                message=message,
                **kw,
            )
        )

    @property
    def has_blocking(self) -> bool:
        return any(r.severity == SEVERITY_BLOCKING for r in self.records)

    @property
    def requires_approval(self) -> bool:
        return any(r.severity == SEVERITY_STRONG for r in self.records)

    def counts(self) -> dict[str, int]:
        out = {sev: 0 for sev in SEVERITY_ORDER}
        for r in self.records:
            out[r.severity] = out.get(r.severity, 0) + 1
        return out

    def to_dataframe(self) -> pd.DataFrame:
        if not self.records:
            return pd.DataFrame(columns=WARNING_COLUMNS)
        rows = sorted(
            (r.to_row() for r in self.records),
            key=lambda row: -SEVERITY_ORDER.get(str(row["severity"]), 0),
        )
        return pd.DataFrame(rows, columns=WARNING_COLUMNS)

    def summary(self) -> dict[str, object]:
        counts = self.counts()
        return {
            "n_warnings": len(self.records),
            "n_blocking": counts[SEVERITY_BLOCKING],
            "n_strong_warning": counts[SEVERITY_STRONG],
            "n_warning": counts[SEVERITY_WARNING],
            "n_info": counts[SEVERITY_INFO],
            "has_blocking": self.has_blocking,
            "requires_user_approval": self.requires_approval,
        }

    def write_csv(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.to_dataframe().to_csv(path, index=False)
        return path
