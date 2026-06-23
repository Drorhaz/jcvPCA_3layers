"""Tests for CLI validation script."""

import subprocess
import sys


def test_cli_runs_on_fixture(repo_root, fixture_layer1_dir, fixture_layer2_dir, tmp_path):
    out_dir = tmp_path / "cli_validation"
    script = repo_root / "scripts" / "validate_segmentation_inputs.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--layer1-dir",
            str(fixture_layer1_dir),
            "--layer2-dir",
            str(fixture_layer2_dir),
            "--out",
            str(out_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (out_dir / "validation_report.md").exists()
    assert (out_dir / "validation_summary.json").exists()
    assert (out_dir / "validation_checks.csv").exists()
    report = (out_dir / "validation_report.md").read_text()
    assert "SAFE TO OPEN" in report
    assert "0..30603" in report
