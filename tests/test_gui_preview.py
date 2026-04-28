from stptocnc.config import ProfileFamily
from stptocnc.gui.app import _build_preview_segments
from stptocnc.models.nesting import LinearNest, NestPlacement


def test_build_preview_segments_includes_trim_part_and_drop() -> None:
    nest = LinearNest(nest_id="nest-1", profile_family=ProfileFamily.PIPE, stock_length_in=100.0)
    nest.placements = [
        NestPlacement(instance_id="A#1", part_mark="A", offset_in=0.0, length_in=30.0, transition_trim_before_in=0.0),
        NestPlacement(instance_id="B#1", part_mark="B", offset_in=30.25, length_in=20.0, transition_trim_before_in=0.25),
    ]
    segments = _build_preview_segments(nest)
    kinds = [seg.kind for seg in segments]
    assert kinds == ["part", "trim", "part", "drop"]
