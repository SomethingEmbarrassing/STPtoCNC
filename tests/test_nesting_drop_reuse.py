from stptocnc.config import NestingDefaults, ProfileFamily
from stptocnc.models.nesting import EndCondition, PartInstance
from stptocnc.nesting import pack_instances_first_fit


def _part(instance_id: str, length_in: float, family: ProfileFamily = ProfileFamily.PIPE, end: EndCondition = EndCondition.FLAT) -> PartInstance:
    return PartInstance(
        instance_id=instance_id,
        part_mark=instance_id,
        length_in=length_in,
        profile_family=family,
        start_condition=EndCondition.FLAT,
        end_condition=end,
    )


def test_drop_reuse_regression_five_by_twelve_then_ten_by_three() -> None:
    # 5 x 12' then 10 x 3', stock 21' (252 in)
    parts = [_part(f"L{i}", 144.0) for i in range(5)] + [_part(f"S{i}", 36.0) for i in range(10)]
    result = pack_instances_first_fit(parts, NestingDefaults())

    # Should not open extra sticks for shorts because 12' sticks leave 9' remnants.
    assert len(result.nests) == 5
    short_count = sum(1 for nest in result.nests for p in nest.placements if p.part_mark.startswith("S"))
    assert short_count == 10


def test_drop_reuse_respects_profile_family_compatibility() -> None:
    parts = [
        _part("P1", 144.0, family=ProfileFamily.PIPE),
        _part("P2", 144.0, family=ProfileFamily.PIPE),
        _part("H1", 36.0, family=ProfileFamily.HSS),
    ]
    result = pack_instances_first_fit(parts, NestingDefaults())
    assert len(result.nests) == 3
    assert result.nests[0].profile_family == ProfileFamily.PIPE
    assert result.nests[2].profile_family == ProfileFamily.HSS


def test_trim_aware_fit_check_creates_new_stick_when_needed() -> None:
    # stick 1 has 36" remnant but next part requires 0.25 trim + 36 length -> no fit
    parts = [
        _part("A", 216.0, end=EndCondition.COPE),
        _part("B", 36.0),
    ]
    result = pack_instances_first_fit(parts, NestingDefaults())
    assert len(result.nests) == 2
