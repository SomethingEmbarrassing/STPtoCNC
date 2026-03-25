from stptocnc.importers.nc1_parser import parse_nc1_file
from stptocnc.parsers.nc1_inspector import inspect_nc1_file


def test_parse_hss_sample() -> None:
    part = parse_nc1_file("docs/h1001.nc1")

    assert part.part_mark.lower() == "h1001"
    assert part.outer_diameter_in > 0
    assert part.wall_thickness_in > 0
    assert part.length_in > 0


def test_parse_angle_sample() -> None:
    part = parse_nc1_file("docs/as1007.nc1")

    assert part.part_mark.lower() == "as1007"
    assert part.outer_diameter_in > 0
    assert part.wall_thickness_in > 0
    assert part.length_in > 0


def test_inspect_hss_bo_ko_records() -> None:
    result = inspect_nc1_file("docs/h1001.nc1")

    assert result["status"] == "ok"
    assert "BO" in result["record_types"]
    assert "KO" in result["record_types"]
    assert len(result["bo_records"]) >= 1
    assert len(result["ko_records"]) >= 1
