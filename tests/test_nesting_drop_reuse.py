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
        material="A500",
    )


def test_long_first_sorting_with_stable_tie_breakers() -> None:
    parts = [
        _part("short-b", 24.0),
        _part("long-a", 100.0),
        _part("short-a", 24.0),
        _part("mid-a", 60.0),
    ]
    result = pack_instances_first_fit(parts, NestingDefaults())
    ordered = [p.instance_id for p in result.nests[0].placements]
    assert ordered[0] == "long-a"
    assert ordered[1] == "mid-a"


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


def test_drop_reuse_respects_material_compatibility() -> None:
    parts = [
        _part("P1", 144.0, family=ProfileFamily.PIPE),
        PartInstance(
            instance_id="P2",
            part_mark="P2",
            length_in=36.0,
            profile_family=ProfileFamily.PIPE,
            start_condition=EndCondition.FLAT,
            end_condition=EndCondition.FLAT,
            material="A36",
        ),
    ]
    result = pack_instances_first_fit(parts, NestingDefaults())
    assert len(result.nests) == 2


def test_trim_aware_fit_check_creates_new_stick_when_needed() -> None:
    # stick 1 has 36" remnant but next part requires 0.25 trim + 36 length -> no fit
    parts = [
        _part("A", 216.0, end=EndCondition.COPE),
        _part("B", 36.0),
    ]
    result = pack_instances_first_fit(parts, NestingDefaults())
    assert len(result.nests) == 2


def test_best_fit_prefers_smallest_remaining_drop() -> None:
    parts = [
        _part("L1", 200.0),  # nest-1 rem 52
        _part("L2", 190.0),  # nest-2 rem 62
        _part("S1", 50.0),   # fits both -> should pick nest-1 rem 2
    ]
    result = pack_instances_first_fit(parts, NestingDefaults())
    nest1_ids = [p.instance_id for p in result.nests[0].placements]
    assert "S1" in nest1_ids
