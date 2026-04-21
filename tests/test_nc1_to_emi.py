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


def test_emit_nc1_part_to_emi_includes_legacy_style_setup_and_wrapped_cut() -> None:
    part = parse_nc1_text(SAMPLE_NC1)
    output = emit_nc1_part_to_emi(part)
    lines = output.splitlines()

    assert "(PROGRAM pp1007)" in lines
    assert "(POST EMI 2400 PROMPTS ROP V1.4)" in lines
    assert "G20" in lines
    assert "G58" in lines
    assert "T1" in lines
    assert "G43 H1" in lines
    assert "#29001 = 140" in lines
    assert "G91" in lines
    assert "G93.1" in lines
    assert "G94" in lines
    assert "G01 X-0.0010 F#29001" in lines
    assert "G01 X0.0002 F#29001" in lines
    assert "G01 F#29002" in lines
    x_values = []
    for line in lines:
        if line.startswith("G01 A") and " X" in line:
            x_chunk = line.split(" X", 1)[1].split(" ", 1)[0]
            x_values.append(round(float(x_chunk), 4))
    assert len(x_values) > 20
    assert len(set(x_values)) > 5
    assert "M30" in lines
