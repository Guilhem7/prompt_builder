"""LivePreviewPanel — live prompt preview with virtual terminal simulation."""
from __future__ import annotations

import re
import datetime
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.widget import Widget
from textual.widgets import Button, Label, Select, Static, Input
from textual.screen import ModalScreen

from prompt_builder.messages import SegmentsChanged
from prompt_builder.models import SegmentsList, format_segments

_SHELL_OPTIONS: list[tuple[str, str]] = [
    ("Bash",  "bash"),
    ("Zsh",   "zsh"),
    ("Echo",   "echo"),
    # ("Fish",  "fish"),
    # ("POSIX", "posix"),
]

_DEFAULT_RC: dict[str, Path] = {
    "bash":  Path("~/.bashrc").expanduser(),
    "zsh":   Path("~/.zshrc").expanduser(),
    # "fish":  Path("~/.config/fish/config.fish").expanduser(),
    # "posix": Path("~/.profile").expanduser(),
}

# Fake terminal lines shown above the live prompt
_FAKE_HISTORY = [
    ("dim", "Last login: {} on pts/0".format(datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y"))),
]

class SaveProfileScreen(ModalScreen):
    """Screen with an input to save profile"""
    DEFAULT_CSS = """
    SaveProfileScreen {
        align: center middle;
    }

    SaveProfileScreen Vertical {
        width: 70;
        min-height: 20;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
        align: center middle;
    }

    SaveProfileScreen Vertical Input {
        width: 40;
    }

    #btn-saveprofilescreen-container {
        padding-top: 3;
        align: center middle;
        height: auto;
    }
    """
    BINDINGS = [
        ("escape", "dismiss", "quit"),
    ]

    def __init__(self, button_name: str = "Save"):
        super().__init__()
        self._button_name = button_name

    def compose(self):
        with Vertical():
            yield Label("Enter the [b]profile[/b] name:")
            yield Static()
            yield Input(id="profile-input-name", placeholder="name")
            with Horizontal(id="btn-saveprofilescreen-container"):
                yield Button(self._button_name, variant="primary", id="btn-saveprofilescreen-profile")
                yield Button("Cancel", id="btn-saveprofilescreen-cancel")

    def on_button_pressed(self, event):
        bid = event.button.id
        if bid == "btn-saveprofilescreen-profile":
            profile_name = self.query_one("#profile-input-name", Input).value
            if not profile_name:
                self.app.notify("[red]Input[/red] cannot be empty", severity="error")
            else:
                self.dismiss(profile_name)
        elif bid == "btn-saveprofilescreen-cancel":
            self.dismiss()

class LivePreviewPanel(Widget):
    """Shows live prompt preview in a virtual terminal + export string."""

    def __init__(self, shell) -> None:
        if shell is None:
            shell = "bash"
        super().__init__()
        self._last_export: str = 'export PS1="$ "'
        self._shell: str = shell
        self._segments: list = SegmentsList([])

    def compose(self) -> ComposeResult:
        # Header
        with Horizontal(id="preview-header"):
            yield Label("Live Preview", id="preview-title")
            yield Select(
                _SHELL_OPTIONS,
                id="shell-select",
                value=self._shell,
                allow_blank=False,
            )
        # Virtual terminal
        with Vertical(id="vterm-box"):
            yield Static("", id="vterm-history", markup=False)
            with Horizontal(id="vterm-prompt-row"):
                yield Static("", id="ansi-preview", markup=False)
        # Status bar
        with Horizontal(id="preview-meta"):
            yield Label("", id="validation-badge", classes="badge-valid")
            yield Label("", id="width-indicator")
        # Export string
        yield Label("Export string:", id="ps1-label")
        yield Static("", id="ps1-raw", markup=False)
        # Actions
        with Horizontal(id="preview-actions"):
            yield Button("Copy", id="btn-copy", variant="primary")
            yield Button("Save to RC", id="btn-save")
            yield Button("Save as..", id="btn-save-as")
            yield Button("Delete profile", id="btn-del-profile", variant="error")

    @on(Select.Changed, "#shell-select")
    def _on_shell_changed(self, event: Select.Changed) -> None:
        event.stop()
        if event.value and event.value is not Select.BLANK:
            self._shell = str(event.value)
            self._refresh(self._segments)
            self.app.autosave()

    def on_segments_changed(self, msg: SegmentsChanged) -> None:
        self._segments = msg.segments
        self._refresh(msg.segments)

    def _refresh(self, segs: list) -> None:
        self._update_vterm(segs)
        export_str = format_segments(segs, self._shell)
        self._last_export = export_str
        self.query_one("#ps1-raw", Static).update(export_str)
        self._update_validation()

    def _update_vterm(self, segs: list) -> None:
        # Build history lines
        hist = Text()
        for style, line in _FAKE_HISTORY:
            hist.append(line + "\n", style=style)
        try:
            self.query_one("#vterm-history", Static).update(hist)
        except Exception:
            pass
        self.query_one("#ansi-preview", Static).update(format_segments(segs, "rich", self._shell))

    def _update_validation(self) -> None:
        badge = self.query_one("#validation-badge", Label)
        if self._shell == "bash":
            badge.update("✓ Bash PS1 (Support var like '\\\\u')")
        elif self._shell == "zsh":
            badge.update("✓ Zsh PROMPT (Support var like '%n')")
        else:
            badge.update(f"{self._shell.capitalize()}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-copy":
            self._copy_to_clipboard()
        elif bid == "btn-save":
            self.save_to_rc()
        elif bid == "btn-save-as":
            self.app.push_screen(SaveProfileScreen("Save"),
                                 callback=self.app.save_profile)
        elif bid == "btn-del-profile":
            self.app.push_screen(SaveProfileScreen("Delete"),
                                 callback=self.app.delete_profile)

    def _copy_to_clipboard(self) -> None:
        try:
            import pyperclip
            pyperclip.copy(self._last_export)
            self.notify("Copied to clipboard!", severity="information")
        except Exception as exc:
            self.notify(f"Copy failed: {exc}", severity="warning")

    def save_to_rc(self) -> None:
        path = _DEFAULT_RC.get(self._shell, _DEFAULT_RC["bash"])
        self.save_to_bashrc(path)

    def save_to_bashrc(self, path: Path = _DEFAULT_RC["bash"]) -> None:
        try:
            begin = "##### BEGIN prompt builder"
            end = "##### END prompt builder"

            bloc = begin + "\n"
            bloc += self._last_export + "\n"
            bloc += end + "\n"

            contenu = path.read_text()

            pattern = re.compile(
                rf"{re.escape(begin)}.*?{re.escape(end)}",
                re.DOTALL
            )

            path.parent.mkdir(parents=True, exist_ok=True)
            if pattern.search(contenu):
                contenu = pattern.sub(lambda x : bloc, contenu)
            else:
                contenu += f"\n\n{bloc}\n"
            path.write_text(contenu)
            self.notify(f"Saved to {path}", severity="information")
        except Exception as exc:
            self.notify(f"Save failed: {exc}", severity="error")
            self.notify(f"{self._last_export}", severity="error")
