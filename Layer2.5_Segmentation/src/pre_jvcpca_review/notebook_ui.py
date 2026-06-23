"""Notebook helpers: joint labels, checkboxes, readable table display."""

from __future__ import annotations

from dataclasses import dataclass

import ipywidgets as widgets
import pandas as pd
from IPython.display import HTML, display

from pre_jvcpca_review.load_layer2 import LinkRecord
from pre_jvcpca_review.mapping import link_joint_family

FAMILY_LABELS = {
    "left_wrist_hand": "Left wrist / hand",
    "right_wrist_hand": "Right wrist / hand",
    "left_elbow_forearm": "Left elbow / forearm",
    "right_elbow_forearm": "Right elbow / forearm",
    "left_shoulder_arm": "Left shoulder / upper arm",
    "right_shoulder_arm": "Right shoulder / upper arm",
    "left_thigh_knee": "Left knee / thigh",
    "right_thigh_knee": "Right knee / thigh",
    "left_foot": "Left foot / ankle",
    "right_foot": "Right foot / ankle",
    "left_shank_ankle": "Left ankle / shin",
    "right_shank_ankle": "Right ankle / shin",
    "hip_left": "Left hip",
    "hip_right": "Right hip",
    "head_neck": "Head / neck",
    "trunk_chest": "Trunk / chest",
    "unknown": "Other",
}


def _bone_fallback_label(link: LinkRecord) -> str:
    """Readable label when joint_family is generic."""
    parent, child = link.parent_canonical, link.child_canonical
    token = child if len(child) > 1 else parent
    side = "Left " if token.startswith("L") else "Right " if token.startswith("R") else ""
    if "Hand" in token or child == "LHand" or child == "RHand":
        return f"{side}wrist / hand".strip().title()
    if "Shoulder" in parent and "UArm" in child:
        return f"{side}shoulder / upper arm".strip().title()
    if "Shoulder" in token or "Shoulder" in parent:
        return f"{side}shoulder".strip().title()
    if "FArm" in token or "UArm" in token:
        return f"{side}elbow / forearm".strip().title()
    if "Thigh" in token or "Shin" in token:
        return f"{side}knee / leg".strip().title()
    if "Foot" in token or "Shin" in parent:
        return f"{side}foot / ankle".strip().title()
    if child in ("Head", "Neck") or parent in ("Head", "Neck", "Chest"):
        if child == "Head" or parent == "Neck":
            return "Head / neck"
        if "Shoulder" in child:
            return f"{side}shoulder (chest)".strip().title()
    if parent in ("671", "Ab", "Chest") or child in ("671", "Ab", "Chest"):
        return "Trunk / spine"
    return link.display_name.replace("->", " → ")


def friendly_joint_label(link: LinkRecord) -> str:
    family = link_joint_family(link)
    plain = FAMILY_LABELS.get(family)
    if not plain or family == "unknown" or family.startswith("left_unknown") or family.startswith("right_unknown"):
        plain = _bone_fallback_label(link)
    scope = link.feature_scope.replace("_", " ")
    return f"{link.link_id}  |  {plain}  |  {link.display_name}  |  {scope}"


@dataclass
class JointSelector:
    """Checkbox grid for Layer 2 link selection."""

    checkboxes: dict[str, widgets.Checkbox]
    container: widgets.VBox
    filter_core_only: widgets.Checkbox
    _all_links: list[LinkRecord]

    def selected_link_ids(self) -> list[str]:
        return [link_id for link_id, cb in self.checkboxes.items() if cb.value]

    def set_selected(self, link_ids: set[str]) -> None:
        for link_id, cb in self.checkboxes.items():
            cb.value = link_id in link_ids

    def select_core_candidates(self) -> None:
        self.set_selected({link.link_id for link in self._all_links if link.feature_scope == "core_candidate"})

    def clear_selection(self) -> None:
        self.set_selected(set())

    def _rebuild_rows(self) -> None:
        show_core = self.filter_core_only.value
        rows: list[widgets.Widget] = []
        for link in self._all_links:
            if show_core and link.feature_scope != "core_candidate":
                continue
            cb = self.checkboxes[link.link_id]
            cb.description = friendly_joint_label(link)
            cb.layout = widgets.Layout(width="98%")
            rows.append(cb)
        if not rows:
            rows.append(widgets.HTML("<i>No links match the current filter.</i>"))
        self.container.children = tuple(rows)

    @classmethod
    def from_links(cls, links: list[LinkRecord], default_ids: set[str] | None = None) -> JointSelector:
        default_ids = default_ids or {"J005", "J007", "J020"}
        checkboxes = {
            link.link_id: widgets.Checkbox(
                value=link.link_id in default_ids,
                description=friendly_joint_label(link),
                layout=widgets.Layout(width="98%"),
            )
            for link in links
        }
        filter_core = widgets.Checkbox(value=False, description="Show only core_candidate joints")
        container = widgets.VBox(list(checkboxes.values()))
        selector = cls(
            checkboxes=checkboxes,
            container=container,
            filter_core_only=filter_core,
            _all_links=links,
        )

        def on_filter_change(_change) -> None:
            selector._rebuild_rows()

        filter_core.observe(on_filter_change, names="value")
        return selector


def display_table(df: pd.DataFrame, title: str, max_rows: int | None = None) -> None:
    """Render a scrollable, readable HTML table."""
    view = df.head(max_rows) if max_rows else df
    html = view.to_html(index=False, na_rep="", escape=False)
    styled = f"""
    <div style="margin: 12px 0;">
      <h3 style="margin-bottom: 8px;">{title}</h3>
      <div style="max-height: 480px; overflow: auto; border: 1px solid #ccc; padding: 8px;">
        <style>
          table.dataframe {{
            font-size: 12px;
            border-collapse: collapse;
            width: max-content;
            min-width: 100%;
          }}
          table.dataframe th {{
            position: sticky;
            top: 0;
            background: #f0f0f0;
            padding: 6px 8px;
            border: 1px solid #ddd;
            text-align: left;
          }}
          table.dataframe td {{
            padding: 4px 8px;
            border: 1px solid #eee;
            vertical-align: top;
            max-width: 320px;
            word-wrap: break-word;
          }}
        </style>
        {html}
      </div>
      <p style="color:#666; font-size:11px;">{len(df)} rows × {len(df.columns)} columns</p>
    </div>
    """
    display(HTML(styled))


def display_summary_card(df: pd.DataFrame, title: str) -> None:
    """One-row summary as a readable key-value card."""
    if df.empty:
        display(HTML(f"<h3>{title}</h3><p>No data.</p>"))
        return
    row = df.iloc[0]
    items = "".join(
        f"<tr><th style='text-align:left;padding:4px 12px 4px 0;'>{col}</th>"
        f"<td style='padding:4px 0;'>{row[col]}</td></tr>"
        for col in df.columns
    )
    display(
        HTML(
            f"<h3>{title}</h3>"
            f"<table style='font-size:13px;border-collapse:collapse;'>{items}</table>"
        )
    )
