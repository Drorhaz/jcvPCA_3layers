"""Per-session HTML quality report (best-effort, non-blocking)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from motive_qc.artifacts import (
    artifact_candidate_severity_note,
    velocity_mad_sigma,
    velocity_percentile_threshold,
)
from motive_qc.batch_report import _html_table, _interval_summary_stats
from motive_qc.core import __version__, QCResult


def _run_key(config: dict[str, Any]) -> str:
    project = config.get("project", {})
    subject_id = str(project.get("subject_id", ""))
    session_id = str(project.get("session_id", "session"))
    return f"{subject_id}_{session_id}" if subject_id else session_id


def _embed_plot(figures: dict[str, Path], output_dir: Path, name: str, caption: str) -> str:
    path = figures.get(name)
    if path is None or not path.exists():
        return ""
    try:
        rel = path.relative_to(output_dir).as_posix()
    except ValueError:
        rel = path.name
    return (
        f'<figure><img src="{rel}" alt="{name}"/>'
        f"<figcaption>{caption}</figcaption></figure>"
    )


def build_session_quality_report_html(
    layer1_result: QCResult,
    layer2_result: QCResult,
    layer3_result: QCResult | None,
    layer4_result: QCResult | None,
    layer5_result: QCResult | None,
    tables: dict[str, pd.DataFrame],
    config: dict[str, Any],
    output_dir: Path,
    figures: dict[str, Path],
) -> str:
    """Build a single-session shareable HTML report."""
    session = layer1_result.session
    assert session is not None
    md = session.metadata
    project = config.get("project", {})
    subject_id = str(project.get("subject_id", ""))
    session_id = str(project.get("session_id", ""))
    run_key = _run_key(config)

    summary = layer2_result.tables.get("session_summary", pd.DataFrame())
    summary_row = summary.iloc[0].to_dict() if not summary.empty else {}

    qc_mask = tables.get("qc_mask", pd.DataFrame())
    intervals = tables.get("qc_mask_intervals", pd.DataFrame())
    stats = _interval_summary_stats(intervals, qc_mask, config)

    skel_note = ""
    events = md.get("skeleton_selection_events") or []
    if events:
        ev = events[0]
        skel_note = (
            f"<p class=\"sub\">Skeleton: using <code>{ev.get('chosen_skeleton')}</code>, "
            f"ignored phantom <code>{ev.get('ignored_skeleton')}</code> "
            f"({ev.get('n_markers_quarantined')} markers quarantined).</p>"
        )

    interval_preview = ""
    if not intervals.empty:
        excl = intervals[intervals["status"] == "exclude"].sort_values(
            "duration_s", ascending=False
        ).head(10)
        if not excl.empty:
            cols = [c for c in ["start_s", "end_s", "duration_s", "criterion", "affected_markers"] if c in excl.columns]
            interval_preview = (
                "<h3>Top exclude intervals (preview)</h3>"
                + _html_table(excl[cols])
            )

    mask_status_counts = ""
    if not qc_mask.empty and "status" in qc_mask.columns:
        counts = qc_mask["status"].value_counts().to_dict()
        mask_status_counts = ", ".join(f"{k}: {v:,}" for k, v in counts.items())

    art_sigma = velocity_mad_sigma(config)
    vel_pct = velocity_percentile_threshold(config)
    art_severity_note = artifact_candidate_severity_note(config)

    plot_sections = [
        _embed_plot(figures, output_dir, "gap_timeline", "Gap timeline"),
        _embed_plot(figures, output_dir, "artifact_timeline", "Artifact event timeline"),
        _embed_plot(
            figures,
            output_dir,
            "window_quality_timeline",
            "Window quality (0.5 s bins)",
        ),
        _embed_plot(
            figures,
            output_dir,
            "artifact_velocity_histogram",
            f"Artifact velocity histogram — {art_severity_note}",
        ),
    ]
    for name, path in sorted(figures.items()):
        if name.startswith("artifact_velocity_histogram__") and path.exists():
            plot_sections.append(
                _embed_plot(figures, output_dir, name, f"Velocity histogram — {name.split('__', 1)[-1]}")
            )

    plots_html = "".join(p for p in plot_sections if p)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Motive QC — {run_key}</title>
<style>
 body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
   margin: 0 auto; max-width: 1000px; padding: 32px; color: #1a202c; line-height: 1.5; }}
 h1 {{ font-size: 24px; margin-bottom: 4px; }}
 h2 {{ margin-top: 32px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
 h3 {{ font-size: 16px; }}
 .sub {{ color: #718096; font-size: 13px; }}
 table {{ border-collapse: collapse; width: 100%; font-size: 12px; margin-top: 10px; }}
 th, td {{ border: 1px solid #e2e8f0; padding: 6px 8px; text-align: left; vertical-align: top; }}
 th {{ background: #f7fafc; }}
 figure {{ margin: 16px 0; }} img {{ max-width: 100%; border: 1px solid #e2e8f0; border-radius: 6px; }}
 figcaption {{ color: #718096; font-size: 12px; }}
 .note {{ background: #ebf8ff; border-left: 4px solid #4299e1; padding: 10px 14px; font-size: 13px; }}
 ul {{ padding-left: 20px; }}
</style></head><body>
<h1>Motive raw marker QC — {run_key}</h1>
<p class="sub">Generated {datetime.now().isoformat(timespec='seconds')} · Motive_QC {__version__}</p>
<p class="sub">Input: <code>{md.get('input_file', '')}</code></p>
{skel_note}

<h2>Session summary</h2>
<ul>
  <li><strong>Subject / session:</strong> {subject_id} / {session_id}</li>
  <li><strong>Frames:</strong> {md.get('n_frames', summary_row.get('total_frames_observed', ''))}</li>
  <li><strong>Frame rate:</strong> {md.get('effective_frame_rate_hz', summary_row.get('effective_frame_rate_hz', ''))} Hz</li>
  <li><strong>Preprocessing status:</strong> {summary_row.get('raw_qc_preprocessing_status', 'n/a')}</li>
  <li><strong>Labeled missing %:</strong> {summary_row.get('missing_percent_labeled', 'n/a')}</li>
</ul>

<h2>QC mask (primary deliverable)</h2>
<div class="note">
  Join Layer 2 Stage 08 parquet on <code>frame</code> (preferred) or <code>time_s</code>.
  Full mask: <a href="tables/qc_mask.csv"><strong>tables/qc_mask.csv</strong></a> ·
  Intervals: <a href="tables/qc_mask_intervals.csv"><strong>tables/qc_mask_intervals.csv</strong></a>
</div>
<ul>
  <li><strong>Frame status counts:</strong> {mask_status_counts or 'n/a'}</li>
  <li><strong>{stats['n_exclude']}</strong> exclude intervals · <strong>{stats['n_caution']}</strong> caution intervals</li>
  <li><strong>{stats['n_artifact_sigma_frames']:,}</strong> frames flagged by velocity MAD
   (σ={stats['art_sigma']}, percentile={stats['vel_percentile']})</li>
</ul>
{interval_preview}

<h2>Plots</h2>
{plots_html or '<p><em>No plots available.</em></p>'}

<p class="sub">See <code>qc_report.md</code> and <code>layer1_segmentation_notebook_manifest.json</code> for full details.</p>
</body></html>"""
