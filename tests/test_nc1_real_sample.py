from pathlib import Path

from stptocnc.importers.nc1_parser import parse_nc1_file
from stptocnc.config import ProfileFamily


def test_parse_pp1016_sample_file() -> None:
    sample = Path("docs/pp1016.nc1")
    assert sample.exists()

    part = parse_nc1_file(sample)

    assert part.part_mark.lower() == "pp1016"
    assert part.outer_diameter_in > 0
    assert part.wall_thickness_in > 0
    assert part.length_in > 0
    assert part.end1.angle_deg > 0
    assert part.end2.angle_deg > 0
    assert part.end1.join_diameter_in > 0
    assert part.end2.join_diameter_in > 0
    assert part.quantity == 2
    assert part.quantity_source == "nc1"
    assert part.profile_family == ProfileFamily.PIPE
