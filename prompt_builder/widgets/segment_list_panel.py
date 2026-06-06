"""SegmentListPanel and SegmentRow widgets."""
from __future__ import annotations

import re

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Button, Label

from prompt_builder.messages import SegmentAdded, SegmentSelected, SegmentsChanged, SegmentDeleted
from prompt_builder.models import SegmentsList, Segment, SEGMENT_ICONS

class SegmentRow(Widget):
    """One row in the segment list panel."""

    DEFAULT_CSS = ""

    def __init__(self, segment: Segment) -> None:
        super().__init__(id=f"row-{segment.id}")
        self._segment = segment
        self.add_class("segment-row-widget")

    def compose(self) -> ComposeResult:
        seg = self._segment
        icon = SEGMENT_ICONS.get(seg.type, "")
        yield Label(icon or " ", classes="seg-icon")
        yield Label(seg.label, classes="seg-label", id=f"lbl-{seg.id}", markup=False)
        with Horizontal():
            yield Button("▲", id=f"up-{seg.id}", classes="row-btn")
            yield Button("▼", id=f"dn-{seg.id}", classes="row-btn")
            yield Button("󰆑", id=f"cl-{seg.id}", classes="row-btn clone")
            yield Button("✕", id=f"rm-{seg.id}", classes="row-btn del")

    def update_from_segment(self, seg: Segment) -> None:
        """Refresh labels without rebuilding the DOM."""
        self._segment = seg
        try:
            icon = SEGMENT_ICONS.get(seg.type, "")
            self.query_one(".seg-icon", Label).update(icon or " ")
            self.query_one(".seg-label", Label).update(seg.label)
        except Exception:
            pass

    def on_click(self) -> None:
        self.post_message(SegmentSelected(self._segment.id))

_UP_RE = re.compile(r"^up-(.+)$")
_DN_RE = re.compile(r"^dn-(.+)$")
_RM_RE = re.compile(r"^rm-(.+)$")
_CL_RE = re.compile(r"^cl-(.+)$")

class SegmentListPanel(Widget):
    """Scrollable panel containing SegmentRow widgets."""
    def __init__(self, initial_segments: SegmentsList) -> None:
        super().__init__()
        self._segments: SegmentsList = initial_segments

    def compose(self) -> ComposeResult:
        for seg in self._segments.segments:
            yield SegmentRow(seg)

    async def on_segments_changed(self, msg: SegmentsChanged) -> None:
        self._segments = msg.segments
        if not msg.shall_reload_panel:
            return

        await self.remove_children()
        for seg in self._segments.segments:
            await self.mount(SegmentRow(seg))

        sel_id = getattr(self.app, "_selected_id", None)
        if sel_id:
            self._apply_selected(sel_id)

    def on_segment_selected(self, msg: SegmentSelected) -> None:
        self._apply_selected(msg.segment_id)

    def _apply_selected(self, segment_id: str) -> None:
        for row in self.query(SegmentRow):
            row.remove_class("selected")
        try:
            self.query_one(f"#row-{segment_id}", SegmentRow).add_class("selected")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        event.stop()

        segs = self._segments.segments

        if m := _RM_RE.match(btn_id):
            seg_id = m.group(1)
            segs = [s for s in segs if s.id != seg_id]
            if getattr(self.app, "_selected_id", None) == seg_id:
                self.app._selected_id = None
            self.app._segments.delete(seg_id)
            self.app.post_message(SegmentDeleted(seg_id))
            self.app.reload_segments(True)

        elif m := _CL_RE.match(btn_id):
            seg_id = m.group(1)
            self.app._segments.clone_and_add(seg_id)
            self.app.reload_segments(True)

        elif m := _UP_RE.match(btn_id):
            seg_id = m.group(1)
            if self.app._segments.move_up(seg_id):
                self.app.reload_segments(True)

        elif m := _DN_RE.match(btn_id):
            seg_id = m.group(1)
            if self.app._segments.move_down(seg_id):
                self.app.reload_segments(True)

    def select_adjacent(self, direction: int) -> None:
        ids = [s.id for s in self._segments.segments]
        if not ids:
            return
        cur = getattr(self.app, "_selected_id", None)
        if cur not in ids:
            new_id = ids[0]
        else:
            idx = ids.index(cur)
            new_id = ids[max(0, min(len(ids) - 1, idx + direction))]
        self.app._selected_id = new_id
        self.post_message(SegmentSelected(new_id))
