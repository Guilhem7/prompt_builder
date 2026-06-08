"""Profile / preset persistence for the Bash Prompt Builder.

Profiles are saved as JSON in ~/.config/prompt-builder/<name>.json.
Built-in presets are defined inline and never written to disk.
"""
from __future__ import annotations

import os
import json
from typing import Any
from pathlib import Path
from rich.style import Style

from prompt_builder.models import SegmentsList, Segment, SegmentType, SeparatorStyle, make_segment

CONFIG_DIR = Path("~/.config/prompt-builder").expanduser()
_AUTOSAVE_NAME = "__autosave__"

_SHELL_KEY = "shell"
_SEGMENTS_KEY = "segments"

def segment_to_dict(seg: Segment) -> dict[str, Any]:
    return {
        "type":       seg.type.value,
        "separator":  seg.separator.value,
        "revert":     seg.revert,
        "text":       seg.text,
        "style": str(seg.style)
    }

def segment_from_dict(d: dict[str, Any]) -> Segment:
    return Segment(
        type=SegmentType(d["type"]),
        separator=SeparatorStyle(d.get("separator", SeparatorStyle.POWERLINE_SOLID.value)),
        text=d.get("text", ""),
        revert=d.get("revert", False),
        style=Style.parse(d["style"])
    )

def save_profile(name: str, segment_list, shell="bash") -> None:
    name = os.path.basename(name)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = [segment_to_dict(s) for s in segment_list.segments]
    datas = {_SHELL_KEY: shell.lower(), _SEGMENTS_KEY: data}
    (CONFIG_DIR / f"{name}.json").write_text(json.dumps(datas, indent=2))

def load_profile(name: str):
    path = CONFIG_DIR / f"{name}.json"
    if not path.exists():
        return None
    try:
        datas = json.loads(path.read_text())
        data = datas[_SEGMENTS_KEY]
        shell = datas[_SHELL_KEY]
        return SegmentsList(segments=[segment_from_dict(d) for d in data]), shell
    except Exception:
        return None, None

def delete_profile(name: str) -> bool:
    name = os.path.basename(name)
    path = CONFIG_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
        return True
    return False

def list_profiles() -> list[str]:
    if not CONFIG_DIR.exists():
        return []
    return sorted(
        p.stem for p in CONFIG_DIR.glob("*.json")
        if p.stem != _AUTOSAVE_NAME
    )

def save_session(segments: list[Segment], shell="bash") -> None:
    save_profile(_AUTOSAVE_NAME, segments, shell)

def load_session() -> list[Segment] | None:
    return load_profile(_AUTOSAVE_NAME)

def _p(stype: SegmentType, **kw) -> Segment:
    return make_segment(stype, **kw)

BUILTIN_PRESETS: dict[str, SegmentsList] = {
    "Simple": SegmentsList(segments=[
        _p(SegmentType.CUSTOM, text=r"\\w ", separator=SeparatorStyle.NONE, color="#00d700"),
        _p(SegmentType.CUSTOM, text="\u2192", separator=SeparatorStyle.NONE, color="#d75f00", bold=True),
    ]),
    "Sunny": SegmentsList(segments=[
        _p(SegmentType.CUSTOM, text=" \u03bb \\\\A ", italic=True, color="black", bgcolor="#f8b400"),
        _p(SegmentType.CUSTOM, text=" \ue760 $$ ", bold=True, color="black", bgcolor="#f8d214"),
        _p(SegmentType.CWD, color="black", bgcolor="#f2e850"),
    ]),
    "Different": SegmentsList(segments=[
        _p(SegmentType.CUSTOM, separator=SeparatorStyle.NONE, text="\u256d\u2500", color="#d7af5f"),
        _p(SegmentType.CUSTOM, separator=SeparatorStyle.NONE, text=r" \\u@", dim=True),
        _p(SegmentType.CUSTOM, separator=SeparatorStyle.NONE, text=r"\\H", color="#87d700"),
        _p(SegmentType.CRLF,   separator=SeparatorStyle.NONE),
        _p(SegmentType.CUSTOM, separator=SeparatorStyle.NONE, text="\u2570\u2500", color="#d7af5f"),
        _p(SegmentType.CUSTOM, separator=SeparatorStyle.NONE, text=" \u27a4", color="#d7af5f"),
    ])
}

def get_preset(name: str) -> SegmentsList | None:
    preset = BUILTIN_PRESETS.get(name)
    if preset is None:
        return None
    # Return clones so the originals stay untouched
    return preset.copy()
