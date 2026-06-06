"""ColorPickerCompact + PaletteScreen with free hex RGB input."""
from __future__ import annotations

from rich.color import Color as RichColor
from rich.style import Style
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.validation import Integer, Number
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static

from prompt_builder.messages import ColorSelected

_ansi256_to_hex = lambda n: RichColor.from_ansi(n).get_truecolor().hex
_get_hex_color = lambda n: n if isinstance(n, str) else _ansi256_to_hex(n)

_COLS = 32
_ROWS = 8
_CELL = "  "

class PaletteGrid(Static):
    """8 × 32 clickable 256-colour ANSI grid."""

    hovered_color: reactive[int] = reactive(0)

    def __init__(self) -> None:
        super().__init__()
        self.hovered_color = -1

    def render(self) -> Text:
        text = Text()
        for row in range(_ROWS):
            for col in range(_COLS):
                idx = row * _COLS + col
                try:
                    rich_color = RichColor.from_ansi(idx)
                    style = Style(bgcolor=rich_color)
                    if idx == self.hovered_color:
                        style = Style(bgcolor=rich_color, reverse=True)
                except Exception:
                    style = Style()
                text.append(_CELL, style=style)
            text.append("\n")
        return text

    def on_click(self, event) -> None:
        col = (event.x - 1) // 2
        row = event.y - 1
        idx = row * _COLS + col
        if 0 <= idx <= 255:
            self.hovered_color = idx
        # Also change input and display the selected one
        try:
            self.screen.query_one("#palette-hex-input").value = _ansi256_to_hex(idx)
        except Exception:
            pass

    def watch_hovered_color(self, value: int) -> None:
        self.refresh()

class PaletteScreen(ModalScreen):
    """Modal 256-colour picker with hex RGB input."""
    BINDINGS = [
                ("escape", "dismiss", "quit"),
                ("enter", "apply", "Save")
               ]

    DEFAULT_CSS = """
    #btn-choices {
        min-width: 1fr;
        align: center middle;
    }
    """

    def __init__(self, current) -> None:
        super().__init__()
        self._current = current

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-dialog"):
            yield Label("Select a colour: click or enter hex #RRGGBB:",
                        id="palette-title")
            yield PaletteGrid()
            with Horizontal():
                yield Input(
                    self._current.get_truecolor().hex if self._current is not None else "#000000",
                    placeholder="#rrggbb",
                    id="palette-hex-input",
                )
                yield Static("\n\n\n", id="color-hex-input")
            with Horizontal(id="btn-choices"):
                yield Button("Apply", variant="primary", id="btn-color-apply")
                yield Button("Cancel", id="btn-palette-screen-escape")

    def on_button_pressed(self, event):
        button_id = event.button.id
        if button_id == "btn-color-apply":
            self.action_apply()
        elif button_id == "btn-palette-screen-escape":
            self.dismiss()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.action_apply()

    def action_apply(self):
        """
        Apply the current hex color to the static widget
        """
        color = self.query_one("#palette-hex-input", Input).value
        self.dismiss(color)

    def on_input_changed(self, event) -> None:
        try:
            preview = self.query_one("#color-hex-input", Static)
            color = event.value.strip()
            preview.styles.background = color
        except Exception:
            pass

class ClickableColor(Static):
    # DEFAULT_CSS = """
    # ClickableColor {
    #     border: round white;
    # }
    # ClickableColor:hover {
    #     border: solid;
    # }
    # """
    def on_click(self):
        self.parent.open_color_modal()

class ColorPickerCompact(Widget):
    """Compact colour picker: swatch + 0-255 index | hex."""
    selected_color = reactive(RichColor.parse("grey27"))

    def __init__(self, color: str, picker_id: str) -> None:
        super().__init__(id=picker_id)
        self._picker_id = picker_id
        self.selected_color = RichColor.parse(color)

    def compose(self) -> ComposeResult:
        yield ClickableColor("", id="swatch")
        yield Button("✕", classes="del-background row-btn del")

    @on(Button.Pressed, ".del-background")
    def remove_color(self, event: Button.Pressed):
        self.selected_color = None
        self.post_message(ColorSelected(self._picker_id, None))

    def open_color_modal(self):
        """
        Push the screen and handle the result
        """
        self.app.push_screen(PaletteScreen(self.selected_color),
                             callback=self._handle_palette_result)

    def on_mount(self) -> None:
        self._refresh_swatch(self.selected_color)

    def watch_selected_color(self, old_color: RichColor | None, new_color: RichColor | None) -> None:
        self._refresh_swatch(new_color)

    def _refresh_swatch(self, color: RichColor | None) -> None:
        try:
            # color = _get_hex_color(color)
            if color is None:
                text = Text("None", style=Style(color="indian_red"))
            else:
                text = Text("    ", style=Style(bgcolor=color.name))
            self.query_one("#swatch", Static).update(text)
        except Exception as e:
            pass

    def _handle_palette_result(self, color: str | None) -> None:
        if color is not None:
            self.selected_color = RichColor.parse(color)
            self._refresh_swatch(color)
            self.post_message(ColorSelected(self._picker_id, color))
