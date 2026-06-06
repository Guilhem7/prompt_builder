"""SegmentConfigPanel — right-hand form for configuring the selected segment."""
from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, Label, Switch, Button, Checkbox

from prompt_builder.messages import ColorSelected, SeparatorChanged
from prompt_builder.models import Segment, SegmentType, SeparatorStyle
from prompt_builder.widgets.color_picker import ColorPickerCompact
from prompt_builder.widgets.icon_picker import IconPickerCompact
from prompt_builder.widgets.separator_selector import SeparatorSelector

class CustomCheckbox(Checkbox):
    BUTTON_INNER: str = "✔"

class StyleCheck(Widget):
    DEFAULT_CSS = """
    StyleCheck {
        width: auto;
        layout: horizontal;
        padding-left: 2;
    }

    CustomCheckbox {
        height: 3;
        content-align: left middle;
    }
    """
    def compose(self) -> ComposeResult:
        yield CustomCheckbox("𝗕", id="bold", compact=True)
        yield CustomCheckbox("",  id="italic", compact=True)
        yield CustomCheckbox("𝗨", id="underline", compact=True)
        yield CustomCheckbox("D", id="dim", compact=True)

class SegmentConfigPanel(Widget):
    """Form that configures whichever segment is currently selected."""
    active_segment_id: reactive[str | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Label("No segment selected", id="config-title")
        yield Label(
            "← Click a segment in the list to configure it.",
            id="config-empty-hint",
        )
        with Vertical(id="config-fields"):
            with Horizontal(classes="config-row", id="row-fg"):
                yield Label("Foreground:", classes="config-label")
                yield ColorPickerCompact(color="green", picker_id="fg-picker")
                # yield Button()
            with Horizontal(classes="config-row", id="row-bg"):
                yield Label("Background:", classes="config-label")
                yield ColorPickerCompact(color="grey27", picker_id="bg-picker")
            # with Horizontal(classes="config-row", id="row-contrast"):
            #     yield Label("Contrast:", classes="config-label")
            #     yield Label("", id="contrast-badge")
            with Horizontal(classes="config-row", id="row-reverse-icon-color"):
                yield Label("Reverse icon color:", classes="config-label")
                yield Switch(value=False, id="icon-toggle")
            with Horizontal(classes="config-row", id="row-text"):
                yield Label("Custom:", classes="config-label")
                yield Input("", placeholder="prompt text", id="custom-text")
                yield StyleCheck()
                yield IconPickerCompact()
            with Horizontal(classes="config-row", id="row-sep"):
                yield Label("Separator:", classes="config-label")
                yield SeparatorSelector()

    def on_mount(self) -> None:
        self.query_one("#config-fields").display = False

    def on_checkbox_changed(self, event) -> None:
        event.stop()
        seg = self._find_segment(self.active_segment_id)
        if seg is None:
            return

        bold = self.query_one("#bold", CustomCheckbox).value
        italic = self.query_one("#italic", CustomCheckbox).value
        underline = self.query_one("#underline", CustomCheckbox).value
        dim = self.query_one("#dim", CustomCheckbox).value
        seg.update_style(bold=bold, italic=italic, dim=dim, underline=underline)
        self.app.reload_segments()

    def on_switch_changed(self, event):
        event.stop()
        seg = self._find_segment(self.active_segment_id)
        if seg is None:
            return
        # seg.revert = event.value
        self.app.update_segment_field(seg.id, "revert", event.value)

    def watch_active_segment_id(self, seg_id: str | None) -> None:
        if seg_id is None:
            self.query_one("#config-title", Label).update("No segment selected")
            self.query_one("#config-empty-hint").display = True
            self.query_one("#config-fields").display = False
            return

        seg = self._find_segment(seg_id)
        if seg is None:
            return

        self.query_one("#config-title", Label).update(f"Configure: {seg.label}")
        self.query_one("#config-empty-hint").display = False
        self.query_one("#config-fields").display = True

        # Set segment active style
        self.query_one("#fg-picker", ColorPickerCompact).selected_color = seg.style.color
        self.query_one("#bg-picker", ColorPickerCompact).selected_color = seg.style.bgcolor
        self.query_one("#bold", CustomCheckbox).value = seg.style.bold == True
        self.query_one("#italic", CustomCheckbox).value = seg.style.italic == True
        self.query_one("#underline", CustomCheckbox).value = seg.style.underline == True
        self.query_one("#dim", CustomCheckbox).value = seg.style.dim == True

        self.query_one(SeparatorSelector).set_separator(seg.separator)
        self.query_one("#icon-toggle").value = seg.revert
        if seg.type is SegmentType.CUSTOM:
            self.query_one("#row-text").display = True
            self.query_one("#custom-text", Input).value = seg.text
        else:
            self.query_one("#row-text").display = False

    def _find_segment(self, seg_id: str) -> Segment | None:
        for seg in self.app._segments.segments:
            if seg.id == seg_id:
                return seg
        return None

    def on_icon_selected(self, msg):
        """New icon has been selected"""
        msg.stop()
        _icon = msg.icon
        if _icon is not None:
            self.query_one("#custom-text", Input).value += _icon

    def on_color_selected(self, msg: ColorSelected) -> None:
        msg.stop()
        seg_id = self.active_segment_id
        if seg_id is None:
            return
        field = "style.color" if msg.picker_id == "fg-picker" else "style.bgcolor"
        seg = self._find_segment(seg_id)
        if seg is None:
            return
        self.app.update_segment_field(seg_id, field, msg.color_idx)

    def on_separator_changed(self, msg: SeparatorChanged) -> None:
        msg.stop()
        seg_id = self.active_segment_id
        if seg_id is None:
            return
        self.app.update_segment_field(seg_id, "separator", msg.sep)

    @on(Input.Changed, "#custom-text")
    def _on_text_changed(self, event: Input.Changed) -> None:
        event.stop()
        seg_id = self.active_segment_id
        if seg_id is None:
            return
        value = event.value
        # if self._debounce_timer is not None:
        #     self._debounce_timer.stop()
        seg = self._find_segment(seg_id)
        if seg is None or seg.text == value:
            # Nothing to change
            return
        self.app.update_segment_field(seg_id, "text", value)
