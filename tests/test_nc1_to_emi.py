from stptocnc.importers.nc1_parser import parse_nc1_text
from stptocnc.post.emi_writer import emit_nc1_part_to_emi


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


def test_emit_nc1_part_to_emi_includes_two_64_step_loops() -> None:
    part = parse_nc1_text(SAMPLE_NC1)
    output = emit_nc1_part_to_emi(part)
    lines = output.splitlines()

    assert "(PROGRAM pp1007)" in lines
    assert "(POST EMI 2400 PROMPTS ROP V1.4)" in lines
    assert sum(1 for line in lines if line.startswith("A")) == 128
    assert "M30" in lines
