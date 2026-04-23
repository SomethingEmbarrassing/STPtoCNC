"""Deterministic first-fit linear nesting with trim-aware adjacency."""

from __future__ import annotations

from stptocnc.config import NestingDefaults, ProfileFamily
from stptocnc.models.nesting import (
    LinearNest,
    NestPlacement,
    NestingResult,
    PartInstance,
    default_stock_length_for_family,
)
from stptocnc.nesting.rules import evaluate_adjacency


def _new_nest(index: int, instance: PartInstance, defaults: NestingDefaults) -> LinearNest:
    return LinearNest(
        nest_id=f"nest-{index}",
        profile_family=instance.profile_family,
        stock_length_in=default_stock_length_for_family(instance.profile_family, defaults),
    )


def _placement_as_instance(placement: NestPlacement, family: ProfileFamily) -> PartInstance:
    return PartInstance(
        instance_id=placement.instance_id,
        part_mark=placement.part_mark,
        length_in=placement.length_in,
        profile_family=family,
        start_condition=placement.start_condition,
        end_condition=placement.end_condition,
        profile_designation=placement.profile_designation,
        material=placement.material,
        source_path=placement.source_file,
        outer_diameter_in=placement.outer_diameter_in,
        wall_thickness_in=placement.wall_thickness_in,
        end1_angle_deg=placement.end1_angle_deg,
        end1_join_diameter_in=placement.end1_join_diameter_in,
        end2_angle_deg=placement.end2_angle_deg,
        end2_join_diameter_in=placement.end2_join_diameter_in,
        end1_flat_cut=placement.end1_flat_cut,
        end2_flat_cut=placement.end2_flat_cut,
        rotational_offset_deg=placement.rotational_offset_deg,
    )


def _make_placement(current: LinearNest, instance: PartInstance, trim_before: float, reason: str) -> NestPlacement:
    return NestPlacement(
        instance_id=instance.instance_id,
        part_mark=instance.part_mark,
        offset_in=current.used_length_in + trim_before,
        length_in=instance.length_in,
        transition_trim_before_in=trim_before,
        transition_reason=reason,
        start_offset_in=0.0,
        profile_designation=instance.profile_designation,
        material=instance.material,
        source_file=instance.source_path,
        outer_diameter_in=instance.outer_diameter_in,
        wall_thickness_in=instance.wall_thickness_in,
        end1_angle_deg=instance.end1_angle_deg,
        end1_join_diameter_in=instance.end1_join_diameter_in,
        end2_angle_deg=instance.end2_angle_deg,
        end2_join_diameter_in=instance.end2_join_diameter_in,
        end1_flat_cut=instance.end1_flat_cut,
        end2_flat_cut=instance.end2_flat_cut,
        rotational_offset_deg=instance.rotational_offset_deg,
        start_condition=instance.start_condition,
        end_condition=instance.end_condition,
    )


def pack_instances_first_fit(instances: list[PartInstance], defaults: NestingDefaults | None = None) -> NestingResult:
    """Pack instances into one or more linear nests.

    Deterministic best-fit reuse strategy:
    - preserve input order for incoming instances
    - evaluate all open compatible sticks (same profile family)
    - place into best-fit existing stick (least remaining length after placement)
    - open a new stick only when no compatible open stick can fit
    """

    cfg = defaults or NestingDefaults()
    nests: list[LinearNest] = []

    for instance in instances:
        candidates: list[tuple[float, int, LinearNest, float, str]] = []
        for idx, nest in enumerate(nests):
            if nest.profile_family != instance.profile_family:
                continue
            previous = _placement_as_instance(nest.placements[-1], nest.profile_family) if nest.placements else None
            decision = evaluate_adjacency(previous, instance, cfg)
            added = decision.trim_before_next_in + instance.length_in
            used_after = nest.used_length_in + added
            if used_after <= nest.stock_length_in:
                candidates.append((nest.stock_length_in - used_after, idx, nest, decision.trim_before_next_in, decision.reason))

        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1]))
            _, _, target, trim_before, reason = candidates[0]
        else:
            target = _new_nest(len(nests) + 1, instance, cfg)
            nests.append(target)
            trim_before = 0.0
            reason = "fresh_stock_first_part"

        target.placements.append(_make_placement(target, instance, trim_before, reason))

    return NestingResult(nests=nests)


def move_instance_between_nests(
    nests: list[LinearNest],
    instance_id: str,
    target_nest_id: str,
    defaults: NestingDefaults | None = None,
) -> list[LinearNest]:
    """Move one placed instance from source nest to target nest with validation/recalc."""
    cfg = defaults or NestingDefaults()
    source: LinearNest | None = None
    source_index = -1
    moved: NestPlacement | None = None
    target = next((n for n in nests if n.nest_id == target_nest_id), None)
    if target is None:
        raise ValueError(f"Target nest not found: {target_nest_id}")

    for nest in nests:
        for i, placement in enumerate(nest.placements):
            if placement.instance_id == instance_id:
                source = nest
                source_index = i
                moved = nest.placements.pop(i)
                break
        if moved is not None:
            break

    if moved is None or source is None:
        raise ValueError(f"Instance not found: {instance_id}")
    if source.nest_id == target.nest_id:
        source.placements.insert(source_index, moved)
        raise ValueError("Source and target nest must be different")
    if source.profile_family != target.profile_family:
        source.placements.insert(source_index, moved)
        raise ValueError("Incompatible profile family between source and target nests")

    moved_instance = _placement_as_instance(moved, target.profile_family)
    target_instances = [_placement_as_instance(p, target.profile_family) for p in target.placements] + [moved_instance]
    rebuilt_target = pack_instances_first_fit(target_instances, defaults=cfg).nests
    if len(rebuilt_target) != 1:
        source.placements.insert(source_index, moved)
        raise ValueError("Target nest does not have enough remaining space for moved instance")

    source_instances = [_placement_as_instance(p, source.profile_family) for p in source.placements]
    rebuilt_source = pack_instances_first_fit(source_instances, defaults=cfg).nests if source_instances else []
    if len(rebuilt_source) > 1:
        source.placements.insert(source_index, moved)
        raise ValueError("Source nest rebalance overflowed unexpectedly")

    # apply rebuilt placements
    target.placements = rebuilt_target[0].placements
    source.placements = rebuilt_source[0].placements if rebuilt_source else []
    return [nest for nest in nests if nest.placements]
