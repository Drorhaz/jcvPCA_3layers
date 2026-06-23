"""Notebook helpers: joint labels, checkboxes, readable table display."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import ipywidgets as widgets
import pandas as pd
from IPython.display import HTML, display

from pre_jvcpca_review.load_layer2 import LinkRecord

_SELECTED_DESCRIPTION_COLOR = "#b00020"


def canonical_joint_label(
    link: LinkRecord,
    *,
    overlap_classification: str | None = None,
) -> str:
    """Primary label matches ``joint_overlap_table.csv`` ``canonical_link_name``."""
    meta: list[str] = []
    if overlap_classification:
        meta.append(overlap_classification)
    scope = link.feature_scope.replace("_", " ")
    if scope:
        meta.append(scope)
    meta.append(link.link_id)
    suffix = f" ({', '.join(meta)})" if meta else ""
    return f"{link.display_name}{suffix}"


def _sort_links(
    links: list[LinkRecord],
    canonical_order: list[tuple[str, str]] | None = None,
) -> list[LinkRecord]:
    if not canonical_order:
        return sorted(links, key=lambda link: link.display_name)
    rank = {key: index for index, key in enumerate(canonical_order)}

    def sort_key(link: LinkRecord) -> tuple[int, str]:
        key = (link.parent_canonical, link.child_canonical)
        return (rank.get(key, len(rank)), link.display_name)

    return sorted(links, key=sort_key)


@dataclass
class JointSelector:
    """Checkbox grid for Layer 2 link selection."""

    checkboxes: dict[str, widgets.Checkbox]
    container: widgets.VBox
    filter_core_only: widgets.Checkbox
    _all_links: list[LinkRecord]
    _links_by_id: dict[str, LinkRecord]
    _overlap_by_canonical: dict[str, str]
    _selection_callbacks: list[Callable[[], None]] = field(default_factory=list)
    _updating: bool = field(default=False, init=False, repr=False)
    _observers_attached: bool = field(default=False, init=False, repr=False)

    def selected_link_ids(self) -> list[str]:
        return [link_id for link_id, cb in self.checkboxes.items() if cb.value]

    def selected_canonical_names(self) -> list[str]:
        selected = set(self.selected_link_ids())
        return [link.display_name for link in self._all_links if link.link_id in selected]

    def set_selected(self, link_ids: set[str]) -> None:
        self._updating = True
        try:
            for link_id, cb in self.checkboxes.items():
                selected = link_id in link_ids
                if cb.value != selected:
                    cb.value = selected
                self._sync_checkbox_appearance(cb, self._links_by_id[link_id])
        finally:
            self._updating = False
        self._rebuild_rows()
        self._fire_selection_callbacks()

    def select_core_candidates(self) -> None:
        """Check all core_candidate links, uncheck others, show core list only."""
        self.filter_core_only.value = True
        core_ids = {
            link.link_id for link in self._all_links if link.feature_scope == "core_candidate"
        }
        self.set_selected(core_ids)

    def clear_selection(self) -> None:
        self.set_selected(set())

    def on_selection_change(self, callback: Callable[[], None]) -> None:
        """Run ``callback`` whenever a joint checkbox toggles."""
        self._selection_callbacks.append(callback)
        self._attach_checkbox_observers()

    def _fire_selection_callbacks(self) -> None:
        for cb in self._selection_callbacks:
            cb()

    def _attach_checkbox_observers(self) -> None:
        if self._observers_attached:
            return

        def on_checkbox_change(change) -> None:
            if self._updating:
                return
            owner = change["owner"]
            for link_id, cb in self.checkboxes.items():
                if cb is owner:
                    self._sync_checkbox_appearance(cb, self._links_by_id[link_id])
                    break
            self._fire_selection_callbacks()

        for checkbox in self.checkboxes.values():
            checkbox.observe(on_checkbox_change, names="value")
        self._observers_attached = True

    def _label_for(self, link: LinkRecord) -> str:
        classification = self._overlap_by_canonical.get(link.display_name)
        return canonical_joint_label(link, overlap_classification=classification)

    def _sync_checkbox_appearance(self, cb: widgets.Checkbox, link: LinkRecord) -> None:
        cb.description = self._label_for(link)
        cb.layout = widgets.Layout(width="98%")
        if cb.value:
            cb.style.description_color = _SELECTED_DESCRIPTION_COLOR
            cb.style.font_weight = "bold"
        else:
            cb.style.description_color = ""
            cb.style.font_weight = ""

    def _rebuild_rows(self) -> None:
        show_core = self.filter_core_only.value
        rows: list[widgets.Widget] = []
        for link in self._all_links:
            if show_core and link.feature_scope != "core_candidate":
                continue
            cb = self.checkboxes[link.link_id]
            self._sync_checkbox_appearance(cb, link)
            rows.append(cb)
        if not rows:
            rows.append(widgets.HTML("<i>No links match the current filter.</i>"))
        self.container.children = tuple(rows)

    @classmethod
    def from_links(
        cls,
        links: list[LinkRecord],
        *,
        default_link_ids: set[str] | None = None,
        canonical_order: list[tuple[str, str]] | None = None,
        overlap_by_canonical: dict[str, str] | None = None,
    ) -> JointSelector:
        ordered = _sort_links(links, canonical_order)
        overlap_by_canonical = overlap_by_canonical or {}
        default_link_ids = default_link_ids or set()
        links_by_id = {link.link_id: link for link in ordered}
        checkboxes = {
            link.link_id: widgets.Checkbox(
                value=link.link_id in default_link_ids,
                description=canonical_joint_label(
                    link,
                    overlap_classification=overlap_by_canonical.get(link.display_name),
                ),
                layout=widgets.Layout(width="98%"),
            )
            for link in ordered
        }
        filter_core = widgets.Checkbox(value=False, description="Show only core_candidate joints")
        container = widgets.VBox(list(checkboxes.values()))
        selector = cls(
            checkboxes=checkboxes,
            container=container,
            filter_core_only=filter_core,
            _all_links=ordered,
            _links_by_id=links_by_id,
            _overlap_by_canonical=overlap_by_canonical,
        )
        for link_id, cb in checkboxes.items():
            selector._sync_checkbox_appearance(cb, links_by_id[link_id])

        def on_filter_change(_change) -> None:
            selector._rebuild_rows()

        filter_core.observe(on_filter_change, names="value")
        selector._rebuild_rows()
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
