"""PromptBuilderApp — top-level Textual application."""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Select

from .messages import (
    SegmentAdded,
    SegmentSelected,
    SegmentsChanged,
)
from prompt_builder.models import SegmentsList, Segment, SegmentType, make_segment
from prompt_builder.persistence import (
    BUILTIN_PRESETS,
    get_preset,
    load_session,
    save_profile,
    save_session,
)
from prompt_builder.widgets.live_preview_panel import LivePreviewPanel
from prompt_builder.widgets.segment_config_panel import SegmentConfigPanel
from prompt_builder.widgets.segment_list_panel import SegmentListPanel

def get_default_segments() -> list[Segment]:
    defaults = SegmentsList()
    for stype in [SegmentType.USERNAME, SegmentType.HOSTNAME, SegmentType.CWD]:
        defaults.add(make_segment(stype))
    return defaults

class PromptBuilderApp(App):
    """Interactive TUI for building a custom shell prompt."""

    CSS_PATH = "prompt_builder.tcss"
    TITLE = "Bash Prompt Builder"
    SUB_TITLE = "Build your PS1 visually"

    BINDINGS = [
        Binding("ctrl+q", "quit",             "Quit"),
        Binding("ctrl+s", "save_ps1",         "Save to RC"),
        Binding("ctrl+p", "save_profile_now", "Save profile"),
        Binding("down",   "select_next",      "Next segment", show=False),
        Binding("up",     "select_prev",      "Prev segment", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()

        saved = load_session()
        if saved:
            self._segments = saved
        else:
            self._segments = get_default_segments()

        self._selected_id = None

    def compose(self) -> ComposeResult:
        yield Header()
        from textual.containers import Horizontal, ScrollableContainer, Vertical
        from textual.widgets import Button, Select

        with Horizontal(id="app-container"):
            with Vertical(id="left-panel"):
                with Horizontal(id="toolbar"):
                    seg_options = [(t.value.replace("_", " ").capitalize(), t) for t in SegmentType]
                    yield Select(seg_options, id="seg-type-select", value=SegmentType.USERNAME)
                    yield Button("＋ Add", id="btn-add", variant="primary")
                with Horizontal(id="toolbar2"):
                    preset_options: list[tuple[str, str]] = [("Preset…", "")]
                    preset_options += [(name, name) for name in BUILTIN_PRESETS]
                    yield Select(preset_options, id="preset-select", value="",
                                 allow_blank=False)
                with ScrollableContainer(id="segment-list"):
                    yield SegmentListPanel(self._segments)
            with Vertical(id="right-panel"):
                yield SegmentConfigPanel()
                yield LivePreviewPanel()
        yield Footer()

    def on_mount(self) -> None:
        self.reload_segments(self._segments)

    def reload_segments(
        self,
        reload_panel=False,
    ) -> None:
        """Replace the segment list and notify all interested descendant widgets."""
        msg = SegmentsChanged(segments=self._segments,
                              shall_reload_panel=reload_panel)
        for widget_cls in (SegmentListPanel, LivePreviewPanel):
            try:
                self.query_one(widget_cls).post_message(msg)
            except Exception:
                pass

        # Auto-save session on every change
        try:
            save_session(self._segments)
        except Exception:
            pass

    def update_segment_field(self, segment_id: str, field: str, value: object) -> None:
        """Mutate one field in-place (preserves segment IDs) then broadcast."""
        self._segments.update(segment_id, field, value)
        if field == "text":
            self.reload_segments(True)
        else:
            self.reload_segments()

    def on_segment_added(self, msg: SegmentAdded) -> None:
        new_seg = make_segment(msg.segment_type)
        self._segments.add(new_seg)
        self.reload_segments(True)
        self._selected_id = new_seg.id
        self.post_message(SegmentSelected(new_seg.id))

    def on_segment_selected(self, msg: SegmentSelected) -> None:
        self._selected_id = msg.segment_id
        self._set_active_segment_id(msg.segment_id)

    def on_segment_deleted(self, msg) -> None:
        self._selected_id = msg.segment_id
        self._set_active_segment_id(None)

    def _set_active_segment_id(self, seg_id):
        try:
            self.query_one(SegmentConfigPanel).active_segment_id = seg_id
        except Exception:
            pass

    def on_button_pressed(self, event) -> None:
        if event.button.id == "btn-add":
            sel = self.query_one("#seg-type-select", Select)
            seg_type = sel.value
            if seg_type and seg_type is not Select.BLANK:
                self.post_message(SegmentAdded(seg_type))

    def on_select_changed(self, event) -> None:
        widget_id = event.select.id
        value = event.value

        if value is Select.BLANK or not value:
            return

        elif widget_id == "preset-select":
            name = str(value)
            segments: list[Segment] | None = None
            segments = get_preset(name)
            if segments:
                self._segments = segments
                self.reload_segments(True)
                self._selected_id = None
            try:
                self.query_one("#preset-select", Select).value = ""
            except Exception:
                pass

    def action_select_next(self) -> None:
        self.query_one(SegmentListPanel).select_adjacent(+1)

    def action_select_prev(self) -> None:
        self.query_one(SegmentListPanel).select_adjacent(-1)

    def action_save_profile_now(self) -> None:
        """Quick-save current segments as 'default' profile."""
        try:
            save_profile("default", self._segments)
            self.notify("Profile saved as 'default'", severity="information")
        except Exception as exc:
            self.notify(f"Save failed: {exc}", severity="error")
