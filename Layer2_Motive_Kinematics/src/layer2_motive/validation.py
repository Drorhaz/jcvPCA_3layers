"""Shared validation helpers, thresholds, and stop conditions."""

from __future__ import annotations


class HardStopError(RuntimeError):
    """Raised when the pipeline must stop before downstream computation."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise HardStopError(message)
