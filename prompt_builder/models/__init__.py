from rich.style import Style
from prompt_builder.models.formatters import format_segments
from prompt_builder.models.segments import (
	Segment,
	SegmentsList,
	SegmentType,
	SeparatorStyle,
	SEGMENT_ICONS
)

def make_segment(stype: SegmentType, **kwargs) -> Segment:
    """Create a Segment with type-appropriate default colors"""
    separator = kwargs.pop("separator", SeparatorStyle.POWERLINE_SOLID)
    text = kwargs.pop("text", "")
    revert = kwargs.pop("revert", False)
    seg_style = Style(**kwargs)
    return Segment(type=stype,
                   separator=separator,
                   text=text,
                   revert=revert,
                   style=seg_style)
