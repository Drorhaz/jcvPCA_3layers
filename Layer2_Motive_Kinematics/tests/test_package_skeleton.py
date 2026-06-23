"""Sanity checks for Milestone 0 skeleton."""

from layer2_motive import __version__


def test_package_version() -> None:
    assert __version__ == "0.0.0"
