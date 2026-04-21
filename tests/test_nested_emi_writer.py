from stptocnc.config import EmiMachineProfile
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
    assert "G20" in text
    assert "G58" in text
    assert "T1" in text
    assert "G43 H1" in text
    assert "#29001 = 140" in text
    assert "(PIECE 1: A START=0.000 LEN=20.000)" in text
    assert "(PROMPT REMOVE NESTED STOCK)" in text
    assert "M15" in text
    assert "M16" in text
    assert "M25" in text
    assert "G91" in text
    assert "G93.1" in text
    assert "G94" in text
    assert "(PLACEHOLDER NESTED CNC)" not in text


def test_emit_nested_nest_to_emi_uses_machine_profile_trim_command() -> None:
    nest = LinearNest(nest_id="nest-100", profile_family=ProfileFamily.PIPE, stock_length_in=252.0)
    nest.placements = [
        NestPlacement(
            instance_id="A#1",
            part_mark="A",
            offset_in=0.25,
            length_in=20.0,
            transition_trim_before_in=0.25,
            transition_reason="previous_end_not_flat_compatible",
            end1_angle_deg=10.0,
            end1_join_diameter_in=1.5,
            end2_angle_deg=20.0,
            end2_join_diameter_in=1.25,
        )
    ]
    profile = EmiMachineProfile(trim_cut_command="M88 (TRIM)")
    text = emit_nested_nest_to_emi(nest, profile=profile)
    assert "M88 (TRIM)" in text


def test_emit_nested_nest_to_emi_emits_flat_flags_and_rotation_offset() -> None:
    nest = LinearNest(nest_id="nest-101", profile_family=ProfileFamily.PIPE, stock_length_in=252.0)
    nest.placements = [
        NestPlacement(
            instance_id="A#1",
            part_mark="A",
            offset_in=0.0,
            length_in=20.0,
            transition_trim_before_in=0.0,
            end1_angle_deg=45.0,
            end1_join_diameter_in=1.910,
            end2_angle_deg=90.0,
            end2_join_diameter_in=1.910,
            end1_flat_cut=True,
            end2_flat_cut=False,
            rotational_offset_deg=12.5,
        )
    ]
    text = emit_nested_nest_to_emi(nest)
    assert "(ROTATIONAL OFFSET: 12.500)" in text
    assert "(END1 FLAT: Y)" in text
    assert "(END2 FLAT: N)" in text
    assert "(END GEOMETRY: angle=45.000 join_dia=200.000 od=1.910)" in text


def test_emit_nested_nest_to_emi_has_varying_x_profile_and_reposition() -> None:
    nest = LinearNest(nest_id="nest-102", profile_family=ProfileFamily.PIPE, stock_length_in=252.0)
    nest.placements = [
        NestPlacement(
            instance_id="A#1",
            part_mark="A",
            offset_in=0.0,
            length_in=40.0,
            end1_angle_deg=30.0,
            end1_join_diameter_in=1.0,
            end2_angle_deg=25.0,
            end2_join_diameter_in=1.0,
            outer_diameter_in=1.9,
            rotational_offset_deg=10.0,
        )
    ]
    text = emit_nested_nest_to_emi(nest)
    x_values = []
    for line in text.splitlines():
        if line.startswith("G01 A") and " X" in line:
            x_chunk = line.split(" X", 1)[1].split(" ", 1)[0]
            x_values.append(round(float(x_chunk), 4))
    assert len(x_values) > 20
    assert len(set(x_values)) > 5
    assert ";End1->End2 Reposition" in text
    assert "G01 X40.0000 F#29001" in text
