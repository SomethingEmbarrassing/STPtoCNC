from stptocnc.importers.nc1_parser import parse_nc1_text


SAMPLE_NC1 = """
PART MARK: pp1007
OD: 1.900
WALL: 0.145
LENGTH: 42.500
END1 ANGLE: 35.0
END1 JOIN DIAMETER: 1.500
END2 ANGLE: 20.0
END2 JOIN DIAMETER: 1.250
"""


def test_parse_nc1_text_extracts_required_fields() -> None:
    part = parse_nc1_text(SAMPLE_NC1)

    assert part.part_mark == "pp1007"
    assert part.outer_diameter_in == 1.9
    assert part.wall_thickness_in == 0.145
    assert part.length_in == 42.5
    assert part.end1.angle_deg == 35.0
    assert part.end1.join_diameter_in == 1.5
    assert part.end2.angle_deg == 20.0
    assert part.end2.join_diameter_in == 1.25


def test_quantity_defaults_to_one_when_missing() -> None:
    part = parse_nc1_text(SAMPLE_NC1)
    assert part.quantity == 1
    assert part.quantity_source == "default"


def test_flat_cut_forces_join_to_200_and_parses_rotation() -> None:
    part = parse_nc1_text(
        """
PART MARK: p20
OD: 1.900
WALL: 0.145
LENGTH: 60.0
END1 ANGLE: 45.0
END1 JOIN DIAMETER: 1.910
END1 FLAT: Y
END2 ANGLE: 90.0
END2 JOIN DIAMETER: 1.910
END2 FLAT: N
ROTATIONAL OFFSET: 12.5
"""
    )
    assert part.end1.flat_cut is True
    assert part.end1.join_diameter_in == 200.0
    assert part.end2.flat_cut is False
    assert part.end2.join_diameter_in == 1.910
    assert part.rotational_offset_deg == 12.5
