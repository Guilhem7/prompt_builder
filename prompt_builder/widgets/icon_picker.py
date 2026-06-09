from __future__ import annotations

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static, Button, Static, TabbedContent, TabPane
from prompt_builder.messages import IconSelected

ARROWS_ICON_CATALOGUE = ("❯", "➜", "»", "›",
                  "λ", "→", "⟩", "▶",
                  "➤", "⚡", "★", "◆",
                  "", "","╭","╰",'─')

FILES_ICONS_CATALOGUE = (
    "󰈔", "󰉋", "󰉖", "󰈙", "󰈤", "󰈫",
    "", "", "", "", "", "",
    "", "", ""
)

DEV_ICONS_CATALOGUE = (
    "󰆍", "󰘦", "󰨞", "󱉶", "󰌠",
    "󰌠", "󱘗", "󰌞", "󰌛",
    "󰌝", "", "", "󰌟",
    "󰟔", "", "", "󰬷",
    "󰟓", "", "", ""
)

ICON_CATALOGUES = {
    "Arrows":    ARROWS_ICON_CATALOGUE,
    "Utils":     FILES_ICONS_CATALOGUE,
    "Developer": DEV_ICONS_CATALOGUE
}

class IconCell(Widget):
    """A single tappable icon inside the grid."""

    DEFAULT_CSS = """
    IconCell {
        width:  5;
        height: 3;
        content-align: center middle;
        background: $surface-darken-1;
        align-vertical: middle;
    }
    IconCell:hover  { background: $surface; }
    IconCell.active { background: $primary-darken-1; }
    """

    class Chosen(Message):
        def __init__(self, cell: "IconCell", icon: str) -> None:
            super().__init__()
            self.cell  = cell
            self.icon  = icon

    def __init__(self, icon: str) -> None:
        super().__init__()
        self._icon  = icon

    def render(self) -> str:
        return self._icon

    def on_click(self) -> None:
        self.post_message(self.Chosen(self, self._icon))

class IconGrid(Widget):
    """Wrapping grid of cells; rebuilt whenever the filter changes."""

    DEFAULT_CSS = """
    IconGrid {
        height: auto;
        layout: grid;
        grid-size: 5;
        grid-gutter: 0;
        grid-rows: 5;
    }
    """
    def __init__(self, icons: tuple[str]) -> None:
        super().__init__()
        self._all = icons

    def compose(self) -> ComposeResult:
        for icon in self._all:
            yield IconCell(icon)

class IconPicker(Widget):
    """
    Browse icons by category, filter by keyword, select one.
    Emits  IconPicker.Selected(icon, label)  on choice.
    """
    DEFAULT_CSS = """
    TabPane {
        padding: 1 2;
    }

    IconPicker {
        height: auto;
        layout: vertical;
        background: $surface;
        padding-bottom: 1;
    }

    IconPicker Horizontal {
        width: 60;
        height: auto;
        padding: 1;
        background: $surface;
    }

    IconPicker Label {
        padding-top: 3;
        margin-bottom: 1;
        text-style: bold;
        color: $primary-lighten-1;
    }

    IconPicker Input {
        width: 50%;
    }

    #unicode-result {
        width: 8;
        content-align: center middle;
        text-style: bold;
        color: $text;
        border: round $accent;
    }
    """
    def __init__(self):
        super().__init__()
        self._selected_icon = None
        self.grids = {
            name: IconGrid(data)
            for name, data in ICON_CATALOGUES.items()
        }

    def compose(self) -> ComposeResult:
        with TabbedContent():
            for name, grid in self.grids.items():
                with TabPane(name):
                    yield grid
        yield Label("Write your unicode:")
        with Horizontal():
            yield Input(placeholder="\\u0000", id="unicode-input")
            yield Static("", id="unicode-result")

    def on_input_changed(self, event):
        unicode_input = event.value.strip()
        if not unicode_input:
            return
        unicode_res = "N/A"
        try:
            if " " not in unicode_input:
                unicode_res = unicode_input.encode().decode("unicode_escape")
                self._selected_icon = unicode_res
        except Exception:
            self._selected_icon = None
            pass
        self.query_one("#unicode-result", Static).update(unicode_res)

    @on(IconCell.Chosen)
    def _cell_chosen(self, event: IconCell.Chosen) -> None:
        self._selected_icon = event.icon
        self.query_one("#unicode-input", Input).value = self._selected_icon.encode("unicode_escape").decode("ascii", errors="ignore")

class IconSelectorModal(ModalScreen):
    CSS = """
    IconSelectorModal   { align: center middle; }

    IconSelectorModal Horizontal {
        align: center middle;
    }

    #wrapper {
        width: auto;
        max-width: 60;
        height: auto;
        layout: vertical;
        border: solid $primary-darken-1;
        background: $surface;
        padding: 1 2;
    }

    """
    BINDINGS = [
                ("escape", "dismiss", "Quit"),
               ]

    def compose(self) -> ComposeResult:
        with Vertical(id="wrapper"):
            yield IconPicker()
            with Horizontal(id="btn-modal"):
                yield Button("Validate", variant="primary", id="btn-icon-validate")
                yield Button("Quit", id="btn-icon-dismiss")

    def on_key(self, event):
        if event.key == "enter":
            event.stop()
            self._apply_icon()

    def on_button_pressed(self, event: Button.Pressed):
        button_id = event.button.id
        icon = None
        if button_id == "btn-icon-validate":
            self._apply_icon()
        elif button_id == "btn-icon-dismiss":
            self.dismiss()

    def _apply_icon(self):
        try:
            icon = self.query_one(IconPicker)._selected_icon
        except Exception as e:
            self.notify(str(e), severity="error")
            pass 
        self.dismiss(icon)

class IconPickerCompact(Widget):
    """Compact icon picker"""
    DEFAULT_CSS = """
    
    """
    def compose(self) -> ComposeResult:
        yield Button("+i", action="push_icon_screen", classes="clone btn-transparent v-align", flat=True)

    def action_push_icon_screen(self):
        self.app.push_screen(IconSelectorModal(),
                             callback=self._add_icon)

    def _add_icon(self, icon):
        if icon is not None:
            self.post_message(IconSelected(icon))
