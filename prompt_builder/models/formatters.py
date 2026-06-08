from __future__ import annotations

import os
import socket
from rich.style import Style
from rich.color import ColorSystem
from rich.text import Text

from prompt_builder.models.segments import SegmentType, DEFAULT_COLOR
from prompt_builder.models.interpolators import BASH_ENGINE, ZSH_ENGINE

class Formatter:
    """
    Base class that format a list of segments in order
    to get a proper result
    """
    ENSURE_ASCII = False
    content_type = {}

    @classmethod
    def no_length_esc(cls, ansi_esc_sequence):
        return cls.FIRST_ESC + \
               ansi_esc_sequence + \
               cls.LAST_ESC

    @classmethod
    def esc(cls, text: str = None, style: Style = None):
        ...

    @classmethod
    def join(cls, prompt_list):
        ...

    @classmethod
    def content(cls, segment: Segment):
        type_text = cls.content_from_type(segment)
        if type_text:
            return cls.get_content(segment) + " " + type_text
        return cls.get_content(segment)

    @classmethod
    def content_from_type(cls, segment: Segment):
        return cls.content_type.get(segment.type, "")

    @classmethod
    def format_segments(cls, segments: SegmentsList):
        return segments.build(cls.esc,
                              cls.content,
                              cls.join,
                              cls.ENSURE_ASCII)

class RichTextFormatter(Formatter):
    """Base Formatter for being displayed in preview"""
    ENSURE_ASCII = False
    content_type = {
        SegmentType.USERNAME: os.getlogin(),
        SegmentType.CWD:      os.getcwd(),
        SegmentType.CRLF:     "\n",
    }

    SHELL = None

    @classmethod
    def with_shell(cls, shell = None):
        cls.SHELL = shell
        return cls

    @classmethod
    def esc(cls, text: str = None, style: Style = None):
        if not(style and text):
            return Text(text)

        new_style = style.without_color
        if style.color != DEFAULT_COLOR:
            new_style += Style(color=style.color)
        if style.bgcolor != DEFAULT_COLOR:
            new_style += Style(bgcolor=style.bgcolor)
        return Text(text, style=new_style)

    @classmethod
    def join(cls, prompt_list):
        res = Text()
        for t in prompt_list:
            res.append_text(t)
        return res

    @classmethod
    def get_content(cls, segment: Segment):
        if cls.SHELL == "bash":
            return BASH_ENGINE.render(segment.text)
        if cls.SHELL == "zsh":
            return ZSH_ENGINE.render(segment.text)
        return segment.text

class BaseFormatter(Formatter):
    """Base Formatter for PROMPT and PS1"""
    ENSURE_ASCII = True

    @classmethod
    def esc(cls, text: str = None, style: Style = None):
        if not text:
            return ""
        ansi_codes = style._make_ansi_codes(ColorSystem.TRUECOLOR)
        if not ansi_codes:
            # return text.encode("unicode_escape").decode("ascii")
            return text
        return cls.no_length_esc(f"\\x1b[{ansi_codes}m") + \
               text + \
               cls.no_length_esc("\\x1b[0m")

    @classmethod
    def join(cls, prompt_list):
        return "{}$'{} '".format(cls.PROMPT_NAME, "".join(prompt_list))

    @classmethod
    def get_content(cls, segment: Segment):
        return segment.text

class Ps1Formatter(BaseFormatter):
    """Formats Segments for bash PS1"""
    FIRST_ESC = r"\["
    LAST_ESC = r"\]"
    PROMPT_NAME = "PS1="
    content_type = {
        SegmentType.USERNAME: r"\u",
        SegmentType.CWD:      r"\w",
        SegmentType.CRLF:     r"\n",
    }

class ZshFormatter(BaseFormatter):
    """Formats Segments for zsh PROMPT"""
    FIRST_ESC = "%{"
    LAST_ESC = "%}"
    PROMPT_NAME = "PROMPT="
    content_type = {
        SegmentType.USERNAME: "%n",
        SegmentType.CWD:      "%~",
        SegmentType.CRLF:     r"\n",
    }
    @classmethod
    def esc(cls, text: str = None, style: Style = None):
        if not text:
            return ""
        if style.without_color == Style.null():
            zsh_style = ""
            zsh_esc = ""
            if style.color:
                hex_color = style.color.get_truecolor().hex
                zsh_style += f"%F{{{hex_color}}}"
                zsh_esc += "%f"
            if style.bgcolor:
                hex_color = style.bgcolor.get_truecolor().hex
                zsh_style += f"%K{{{hex_color}}}"
                zsh_esc += "%k"
            return f"{zsh_style}{text}{zsh_esc}"
        return super().esc(text, style)

class EchoFormatter(BaseFormatter):
    """Formats Segments for echo, reusable in functions
    or PROMPT_COMMAND"""
    FIRST_ESC = ""
    LAST_ESC = ""
    PROMPT_NAME = "echo -e "
    content_type = {
        SegmentType.USERNAME: os.getlogin(),
        SegmentType.CWD:      os.getcwd(),
        SegmentType.CRLF:     r"\n",
    }

def format_segments(segments, formatter: str, shell: str | None = None):
    """
    Formatters
    """
    formatter = formatter.lower()
    if formatter == "rich":
        return RichTextFormatter.with_shell(shell).format_segments(segments)
    if formatter == "bash":
        return Ps1Formatter.format_segments(segments)
    if formatter == "zsh":
        return ZshFormatter.format_segments(segments)
    if formatter == "echo":
        return EchoFormatter.format_segments(segments)
    raise ValueError(f"Unknow formatter: {formatter}")
