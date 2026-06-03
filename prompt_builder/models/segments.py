import uuid
import copy
from enum import Enum
from rich.text import Text
from rich.color import Color
from rich.style import Style
from typing import List, Tuple
from dataclasses import dataclass, field

DEFAULT_COLOR = Color.parse("default")

class SeparatorStyle(str, Enum):
    POWERLINE_SOLID = ""   # solid right arrow
    POWERLINE_LEFT  = ""   # left-pointing solid arrow
    POWERLINE_THIN  = ""   # thin right arrow
    FLAME           = "\ue0c0"   # flame
    LEFT_FLAME      = "\ue0c2" # flame to the left
    TRIANGLE        = "\ue0b8"
    TRIANGLE_REV    = "\ue0ba"
    DOUBLE_LEFT     = "\ue0b6" # Rounded left
    DOUBLE_RIGHT    = "\ue0b4"   # pixelated solid right
    NONE            = ""

class SegmentType(str, Enum):
    # General
    CUSTOM       = "custom"
    CRLF         = "\\n"
    USERNAME     = "username"
    HOSTNAME     = "hostname"
    CWD          = "cwd"

SEGMENT_ICONS: dict[SegmentType, str] = {
    SegmentType.CUSTOM:      "\ue029",
    SegmentType.CRLF:        "\\n",
    SegmentType.USERNAME:    "",
    SegmentType.HOSTNAME:    "",
    SegmentType.CWD:         "",
}

SEGMENT_LABELS: dict[SegmentType, str] = {
    SegmentType.CUSTOM:      "Custom text",
    SegmentType.CRLF:        "\\n",
    SegmentType.USERNAME:    "Username",
    SegmentType.HOSTNAME:    "Hostname",
    SegmentType.CWD:         "Directory",
}

# Default (bg_color, fg_color) per type
# Here ansi color of type 38;5; are used
SEGMENT_DEFAULTS: dict[SegmentType, tuple[int, int]] = {
    SegmentType.CUSTOM:         ('grey27', 'grey74'),
    SegmentType.USERNAME:       ('blue_violet', 'grey100'),
    SegmentType.HOSTNAME:       ('blue3', 'grey100'),
    SegmentType.CWD:            ('dodger_blue2', 'grey100')
}

def _new_id() -> str:
    return uuid.uuid4().hex[:8]

class Segment:
    def __init__(self,
                 type: SegmentType,
                 separator: SeparatorStyle = SeparatorStyle.POWERLINE_SOLID,
                 text: str = "",
                 revert: bool = False,
                 style: Style = None):
        self.type = type
        self.separator = separator
        self.text = text
        self.revert = revert
        self.id = _new_id()
        self.style = style

    def update_style(self, bold=False, italic=False, dim=False, underline=False):
        self.style += Style(bold=bold, italic=italic, dim=dim, underline=underline)

    @property
    def label(self) -> str:
        if self.type == SegmentType.CUSTOM:
            return self.text or "Custom Text"
        return SEGMENT_LABELS[self.type]

    @property
    def icon(self) -> str:
        return SEGMENT_ICONS.get(self.type, "")

    def clone(self) -> "Segment":
        s = copy.copy(self)
        s.id = _new_id()
        return s

@dataclass
class SegmentsList:
    """
    Main class for segment management
    """
    NO_ICONS_SEGMENTS: Tuple[str] = ("CUSTOM", "CRLF")
    NO_BG_SEGMENTS: Tuple[str] = ("CRLF")
    segments: List[Segment] = field(default_factory=list)

    def add(self, segment: Segment):
        self.segments.append(segment)

    def delete(self, segment_id: int):
        self.segments.remove(self._get(segment_id))

    def clone_and_add(self, segment_id: int):
        """Insert a segment right after
        the one with the given id"""
        seg = self._get(segment_id)
        if seg is not None:
            self.segments.insert(self.segments.index(seg),
                                 seg.clone())

    def _get(self, segment_id: int):
        for seg in self.segments:
            if seg.id == segment_id:
                return seg
        return None

    def move(self, segment_id: int, index: int = 0):
        seg_index = self.segments.index(self._get(segment_id))
        segment_to_move = self.segments.pop(seg_index)
        self.segments.insert(index, segment_to_move)

    def move_down(self, segment_id: int):
        seg_index = self.segments.index(self._get(segment_id))
        if seg_index != len(self.segments) - 1:
            self.segments[seg_index], self.segments[seg_index+1] = (
                self.segments[seg_index+1], self.segments[seg_index]
                )
            return True
        return False

    def move_up(self, segment_id: int):
        seg_index = self.segments.index(self._get(segment_id))
        if seg_index != 0:
            self.segments[seg_index], self.segments[seg_index-1] = (
                self.segments[seg_index-1], self.segments[seg_index]
                )
            return True
        return False

    def update(self, segment_id: int, prop, value):
        """
        Update a value of a segment in the segment's list
        """
        seg_index = self.segments.index(self._get(segment_id))
        segment = self.segments[seg_index]
        if prop.startswith("style."):
            to_update = prop[6:]
            new_style = {
                "color"     : segment.style.color,
                "bgcolor"   : segment.style.bgcolor,
                "bold"      : segment.style.bold,
                "italic"    : segment.style.italic,
                "underline" : segment.style.underline,
                "dim"       : segment.style.dim,
            }
            if value is None:
                new_style.pop(to_update)
            else:
                new_style[to_update] = value
            segment.style = Style(**new_style)

        else:
            setattr(segment, prop, value)

    def _build_segment(self,
                       segment,
                       next_segment,
                       _esc,
                       _content,
                       ensure_ascii):
        content = _content(segment)
        _prompt = []
        if segment.type.name in self.NO_ICONS_SEGMENTS:
            icon = ""
        else:
            icon = SEGMENT_ICONS.get(segment.type, "")
            if icon:
                content = f" {icon} {content} "
        _prompt.append(_esc(content, segment.style))
        if segment.separator is SeparatorStyle.NONE:
            return _prompt

        sep_char = segment.separator.value
        if ensure_ascii:
            sep_char = sep_char.encode("unicode_escape")\
                               .decode("ascii")

        tmp_style = segment.style.without_color
        if next_segment is None:
            if segment.revert:
                tmp_style += Style(color=DEFAULT_COLOR)
            else:
                tmp_style += Style(color=segment.style.bgcolor, bgcolor=DEFAULT_COLOR)
            _prompt.append(_esc(sep_char, tmp_style))
            return _prompt

        new_color = next_segment.style.bgcolor
        if segment.type.name in self.NO_BG_SEGMENTS:
            new_color = DEFAULT_COLOR

        if segment.revert:
            tmp_style += Style(color=new_color, bgcolor=segment.style.bgcolor)

        else:
            tmp_style += Style(color=segment.style.bgcolor,
                               bgcolor=new_color)
        _prompt.append(_esc(sep_char, tmp_style))
        return _prompt

    def build(self,
               _esc,
               _content,
               _join,
               ensure_ascii=False):
        """
        Public method for converting segments into a wanted
        format
        """
        prompt = []
        for i, segment in enumerate(self.segments):
            is_last = i == len(self.segments) - 1
            next_segment = None if is_last else self.segments[i+1]
            prompt.extend(self._build_segment(segment,
                           next_segment,
                           _esc,
                           _content,
                           ensure_ascii))
        return _join(prompt)

    def copy(self):
        return SegmentsList(segments=self.segments.copy())
