"""SeparatorSelector — radio-button style widget for choosing a SeparatorStyle."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button

from prompt_builder.messages import SeparatorChanged
from prompt_builder.models import SeparatorStyle


class SeparatorSelector(Widget):
    """Horizontal set of buttons, one per SeparatorStyle; active gets .active class."""

    selected_sep: reactive[SeparatorStyle] = reactive(SeparatorStyle.POWERLINE_SOLID)

    def __init__(self, initial: SeparatorStyle = SeparatorStyle.POWERLINE_SOLID) -> None:
        super().__init__(id="sep-select")
        self.selected_sep = initial

    def compose(self) -> ComposeResult:
        with Horizontal():
            for style in SeparatorStyle:
                btn = Button(
                    style.value if style.value else "off",
                    id=f"sep-{style.name}",
                    classes="sep-btn",
                )
                if style == self.selected_sep:
                    btn.add_class("active")
                yield btn

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        btn_id = event.button.id or ""
        if not btn_id.startswith("sep-"):
            return
        style_name = btn_id[len("sep-"):]
        try:
            style = SeparatorStyle[style_name]
        except KeyError:
            return
        self.selected_sep = style
        self.post_message(SeparatorChanged(style))

    def watch_selected_sep(self, value: SeparatorStyle) -> None:
        for btn in self.query(".sep-btn"):
            btn.remove_class("active")
        try:
            self.query_one(f"#sep-{value.name}").add_class("active")
        except Exception:
            pass

    def set_separator(self, sep: SeparatorStyle) -> None:
        """Programmatically set without firing SeparatorChanged."""
        self.selected_sep = sep
