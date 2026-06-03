from __future__ import annotations

from textual.message import Message

from prompt_builder.models import Segment, SegmentType, SeparatorStyle


class SegmentsChanged(Message):
    """Broadcast whenever the segment list is mutated."""

    def __init__(self, segments: list[Segment], shall_reload_panel: bool = False) -> None:
        super().__init__()
        self.segments = segments
        self.shall_reload_panel = shall_reload_panel

class SegmentSelected(Message):
    """Posted when the user clicks a segment row to configure it."""

    def __init__(self, segment_id: str) -> None:
        super().__init__()
        self.segment_id = segment_id

class SegmentDeleted(Message):
    """Posted when the user clicks a segment row to configure it."""
    def __init__(self, segment_id: str) -> None:
        super().__init__()
        self.segment_id = segment_id

class SegmentAdded(Message):
    """Posted when the user clicks Add in the toolbar."""

    def __init__(self, segment_type: SegmentType) -> None:
        super().__init__()
        self.segment_type = segment_type


class SegmentConfigChanged(Message):
    """Posted when any config field on the active segment changes."""

    def __init__(self, segment_id: str, field: str, value: object) -> None:
        super().__init__()
        self.segment_id = segment_id
        self.field = field
        self.value = value


class ColorSelected(Message):
    """Posted by ColorPickerCompact when a color is chosen."""

    def __init__(self, picker_id, color_idx) -> None:
        super().__init__()
        self.picker_id = picker_id
        self.color_idx = color_idx

class IconSelected(Message):
    """Posted by IconPickerCompact when an icon is chosen."""
    def __init__(self, icon) -> None:
        super().__init__()
        self.icon = icon

class SeparatorChanged(Message):
    """Posted by SeparatorSelector when a style is chosen."""

    def __init__(self, sep: SeparatorStyle) -> None:
        super().__init__()
        self.sep = sep


class ThemeChangeRequested(Message):
    """Posted when the user selects a theme from the toolbar."""

    def __init__(self, theme_name: str) -> None:
        super().__init__()
        self.theme_name = theme_name


class PresetLoadRequested(Message):
    """Posted when the user loads a preset or profile."""

    def __init__(self, preset_name: str, is_builtin: bool = True) -> None:
        super().__init__()
        self.preset_name = preset_name
        self.is_builtin = is_builtin


class ShellChanged(Message):
    """Posted by LivePreviewPanel when the target shell selector changes."""

    def __init__(self, shell: str) -> None:
        super().__init__()
        self.shell = shell
