from stptocnc.config import ProfileFamily
from stptocnc.models.nesting import LinearNest, NestPlacement
from stptocnc.post.emi_writer import emit_nested_nest_to_emi


def test_emit_nested_nest_to_emi_contains_real_nest_structure() -> None:
    nest = LinearNest(nest_id="nest-99", profile_family=ProfileFamily.PIPE, stock_length_in=252.0)
    nest.placements = [
        NestPlacement(
            instance_id="A#1",
            part_mark="A",
            offset_in=0.0,
            length_in=20.0,
            transition_trim_before_in=0.0,
            end1_angle_deg=10.0,
            end1_join_diameter_in=1.5,
            end2_angle_deg=20.0,
            end2_join_diameter_in=1.25,
        )
    ]

    text = emit_nested_nest_to_emi(nest)
    assert "(PROGRAM nest-99)" in text
    assert "(POST EMI 2400 PROMPTS ROP V1.4)" in text
    assert "(PIECE 1: A START=0.000 LEN=20.000)" in text
    assert "(PROMPT REMOVE NESTED STOCK)" in text
    assert "(PLACEHOLDER NESTED CNC)" not in text
