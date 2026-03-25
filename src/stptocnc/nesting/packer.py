"""Deterministic first-fit linear nesting with trim-aware adjacency."""

from __future__ import annotations

from stptocnc.config import NestingDefaults
from stptocnc.models.nesting import LinearNest, NestPlacement, NestingResult, PartInstance, default_stock_length_for_family
from stptocnc.nesting.rules import evaluate_adjacency


def _new_nest(index: int, instance: PartInstance, defaults: NestingDefaults) -> LinearNest:
    return LinearNest(
        nest_id=f"nest-{index}",
        profile_family=instance.profile_family,
        stock_length_in=default_stock_length_for_family(instance.profile_family, defaults),
    )


def pack_instances_first_fit(instances: list[PartInstance], defaults: NestingDefaults | None = None) -> NestingResult:
    """Pack instances into one or more linear nests.

    Simple deterministic strategy:
    - preserve input order
    - same-family instances stay together when possible
    - open a new stick when next part would exceed stock length
    """

    cfg = defaults or NestingDefaults()
    nests: list[LinearNest] = []

    current: LinearNest | None = None
    previous_instance: PartInstance | None = None

    for instance in instances:
        if current is None or current.profile_family != instance.profile_family:
            current = _new_nest(len(nests) + 1, instance, cfg)
            nests.append(current)
            previous_instance = None

        decision = evaluate_adjacency(previous_instance, instance, cfg)
        additional_consumption = decision.trim_before_next_in + instance.length_in

        if current.used_length_in + additional_consumption > current.stock_length_in:
            current = _new_nest(len(nests) + 1, instance, cfg)
            nests.append(current)
            previous_instance = None
            decision = evaluate_adjacency(previous_instance, instance, cfg)

        placement = NestPlacement(
            instance_id=instance.instance_id,
            part_mark=instance.part_mark,
            offset_in=current.used_length_in + decision.trim_before_next_in,
            length_in=instance.length_in,
            transition_trim_before_in=decision.trim_before_next_in,
            transition_reason=decision.reason,
            start_offset_in=0.0,  # TODO: derive from explicit start-feature geometry where available.
            profile_designation=instance.profile_designation,
            material=instance.material,
            source_file=instance.source_path,
        )
        current.placements.append(placement)
        previous_instance = instance

    return NestingResult(nests=nests)
