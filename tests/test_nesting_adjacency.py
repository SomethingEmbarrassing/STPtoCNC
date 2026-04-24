from stptocnc.config import NestingDefaults, ProfileFamily
from stptocnc.models.nesting import EndCondition, PartInstance
from stptocnc.nesting import evaluate_adjacency, pack_instances_first_fit


def _part(idx: int, start: EndCondition, end: EndCondition, length: float = 10.0) -> PartInstance:
    return PartInstance(
        instance_id=f"P{idx}",
        part_mark=f"P{idx}",
        length_in=length,
        profile_family=ProfileFamily.PIPE,
        start_condition=start,
        end_condition=end,
    )


def test_first_part_on_fresh_stick_has_no_trim() -> None:
    decision = evaluate_adjacency(None, _part(1, EndCondition.FLAT, EndCondition.FLAT), NestingDefaults())
    assert decision.trim_before_next_in == 0.0
    assert decision.reason == "fresh_stock_first_part"


def test_flat_to_flat_requires_no_trim() -> None:
    prev = _part(1, EndCondition.FLAT, EndCondition.FLAT)
    nxt = _part(2, EndCondition.FLAT, EndCondition.FLAT)
    decision = evaluate_adjacency(prev, nxt, NestingDefaults())
    assert decision.trim_before_next_in == 0.0


def test_cope_to_flat_inserts_trim() -> None:
    prev = _part(1, EndCondition.FLAT, EndCondition.COPE)
    nxt = _part(2, EndCondition.FLAT, EndCondition.FLAT)
    decision = evaluate_adjacency(prev, nxt, NestingDefaults())
    assert decision.trim_before_next_in == 0.25


def test_multi_part_nest_consumption_only_counts_required_trims() -> None:
    parts = [
        _part(1, EndCondition.FLAT, EndCondition.FLAT, 10.0),
        _part(2, EndCondition.FLAT, EndCondition.COPE, 10.0),
        _part(3, EndCondition.FLAT, EndCondition.FLAT, 10.0),
    ]
    result = pack_instances_first_fit(parts, NestingDefaults())
    nest = result.nests[0]

    # part1 + part2 + trim_before_part3 + part3
    assert nest.used_length_in == 30.25
    assert nest.placements[0].transition_trim_before_in == 0.0
    assert nest.placements[1].transition_trim_before_in == 0.0
    assert nest.placements[2].transition_trim_before_in == 0.25


def test_unknown_end_condition_defaults_conservative_trim() -> None:
    prev = _part(1, EndCondition.FLAT, EndCondition.UNKNOWN)
    nxt = _part(2, EndCondition.FLAT, EndCondition.FLAT)
    decision = evaluate_adjacency(prev, nxt, NestingDefaults())
    assert decision.trim_before_next_in == 0.25
