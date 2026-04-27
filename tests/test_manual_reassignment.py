import pytest

from stptocnc.config import NestingDefaults, ProfileFamily
from stptocnc.models.nesting import EndCondition, PartInstance
from stptocnc.nesting import move_instance_between_nests, pack_instances_first_fit


def _part(instance_id: str, length_in: float, family: ProfileFamily = ProfileFamily.PIPE, end: EndCondition = EndCondition.FLAT) -> PartInstance:
    return PartInstance(
        instance_id=instance_id,
        part_mark=instance_id,
        length_in=length_in,
        profile_family=family,
        start_condition=EndCondition.FLAT,
        end_condition=end,
    )


def test_move_piece_between_compatible_nests_recalculates_lengths() -> None:
    parts = [_part("A", 144.0), _part("B", 144.0), _part("C", 36.0)]
    nests = pack_instances_first_fit(parts, NestingDefaults()).nests
    assert len(nests) == 2

    moved = move_instance_between_nests(nests, "C", "nest-2", NestingDefaults())
    nest1 = next(n for n in moved if n.nest_id == "nest-1")
    nest2 = next(n for n in moved if n.nest_id == "nest-2")
    assert nest1.remaining_length_in == 108.0
    assert nest2.remaining_length_in == 72.0


def test_move_rejects_incompatible_family() -> None:
    parts = [_part("P", 100.0, family=ProfileFamily.PIPE), _part("H", 100.0, family=ProfileFamily.HSS)]
    nests = pack_instances_first_fit(parts, NestingDefaults()).nests
    with pytest.raises(ValueError, match="Incompatible profile family"):
        move_instance_between_nests(nests, "P", nests[1].nest_id, NestingDefaults())


def test_move_rejects_when_target_overflows() -> None:
    parts = [_part("A", 200.0), _part("B", 200.0, end=EndCondition.COPE), _part("C", 52.0)]
    nests = pack_instances_first_fit(parts, NestingDefaults()).nests
    with pytest.raises(ValueError, match="remaining space"):
        move_instance_between_nests(nests, "C", "nest-2", NestingDefaults())


def test_reassignment_is_deterministic() -> None:
    parts = [_part("A", 144.0), _part("B", 144.0), _part("C", 36.0)]
    nests1 = pack_instances_first_fit(parts, NestingDefaults()).nests
    nests2 = pack_instances_first_fit(parts, NestingDefaults()).nests
    out1 = move_instance_between_nests(nests1, "C", "nest-2", NestingDefaults())
    out2 = move_instance_between_nests(nests2, "C", "nest-2", NestingDefaults())
    sig1 = [(n.nest_id, [p.instance_id for p in n.placements]) for n in out1]
    sig2 = [(n.nest_id, [p.instance_id for p in n.placements]) for n in out2]
    assert sig1 == sig2
