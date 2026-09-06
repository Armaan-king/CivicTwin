"""Who is asked to reason, and what the answer can therefore be said to cover.

Deliberating two thousand residents is the honest default and it is mostly waste: a stop
closure reaches about forty of them, and the other nineteen hundred spend a model call
each to say nothing changed. Locally that is four hours to learn what the geometry already
knew.

So the run selects. Three strata, each there for a different reason:

    affected    the policy reaches their stop. The finding lives here.
    tied        household and care ties of the affected. This is the second-order
                consequence the product exists to find -- someone unaffected by the
                network who is affected by the person they look after.
    comparison  a stratified sample of everyone else. Without it there is no denominator,
                no subgroup rate, and no way to tell a harmed cohort from a small one.

The comparison sample is stratified rather than random on purpose. `I3`/`I4` report
disparity across four axes and `L2` gates a flag at n >= 30; a flat random draw of a
hundred residents leaves most cells under that floor, so the fairness metric silently
reports nothing and reads as "no disparity". Insufficient evidence is not zero disparity,
and the difference has to survive contact with the sampler.

Nobody outside the cohort is claimed to be unaffected. They are unevaluated, the run
carries the counts, and the screen says so.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from app.population import Population
from app.world import ResidentWorld

#: The subgroup floor from L2. A cell smaller than this cannot support a claim, so the
#: sampler tries to fill every cell to it before it spends draws anywhere else.
MIN_CELL = 30

#: Axes from I4, reported independently. No cross-tabulation in V1.
AXES = ("age_band", "mobility_level", "home_subzone", "is_caregiver")


@dataclass
class Cohort:
    ids: list[str] = field(default_factory=list)
    affected: list[str] = field(default_factory=list)
    tied: list[str] = field(default_factory=list)
    comparison: list[str] = field(default_factory=list)

    def strata(self) -> dict[str, int]:
        return {
            "affected": len(self.affected),
            "tied": len(self.tied),
            "comparison": len(self.comparison),
        }


def _axis_value(persona, axis: str) -> str:
    return str(getattr(persona, axis))


def select_cohort(
    pop: Population,
    world: dict[str, ResidentWorld],
    social: nx.Graph | None = None,
    comparison: int = 240,
    rng=None,
) -> Cohort:
    """Pick who reasons. Deterministic given the population seed unless `rng` says otherwise.

    `comparison` is a budget, not a promise. The sampler fills subgroup cells toward
    `MIN_CELL` first and spends whatever is left on a plain draw, so a small budget
    degrades into "some cells are reportable" rather than into a biased sample that looks
    complete.
    """
    from app.rng import derived_rng

    rng = rng or derived_rng("cohort")
    by_id = pop.by_id()

    affected = [p.persona_id for p in pop.personas
                if world[p.persona_id].directly_affected]
    chosen = set(affected)

    # ---------------------------------------------------------------- tied
    # Household and care ties first -- those are the dependency edges the finding rests
    # on -- then one hop of the social graph, which is how an opinion travels.
    tied: list[str] = []
    for pid in affected:
        w = world[pid]
        for other in (*w.household, *w.depends_on_me, *w.i_depend_on):
            if other not in chosen:
                chosen.add(other)
                tied.append(other)
    if social is not None:
        for pid in affected:
            if pid not in social:
                continue
            for other in social.neighbors(pid):
                if other not in chosen:
                    chosen.add(other)
                    tied.append(other)

    # ---------------------------------------------------------------- comparison
    rest = [p.persona_id for p in pop.personas if p.persona_id not in chosen]
    comparison_ids = _stratified(rest, by_id, chosen, comparison, rng)

    ids = affected + tied + comparison_ids
    return Cohort(ids=ids, affected=affected, tied=tied, comparison=comparison_ids)


def _stratified(
    rest: list[str], by_id: dict, chosen: set[str], budget: int, rng
) -> list[str]:
    """Fill every subgroup cell toward MIN_CELL, then spend the remainder at random.

    Counts what the affected and tied strata already contribute to each cell, because a
    cell that is full of harmed residents does not need topping up with more of them -- it
    needs the comparison the sampler exists to provide.
    """
    have: dict[tuple[str, str], int] = {}
    for pid in chosen:
        p = by_id.get(pid)
        if p is None:
            continue
        for axis in AXES:
            key = (axis, _axis_value(p, axis))
            have[key] = have.get(key, 0) + 1

    pool = list(rest)
    rng.shuffle(pool)
    picked: list[str] = []

    # pass 1: whoever moves the emptiest cell closest to the floor
    for pid in pool:
        if len(picked) >= budget:
            break
        p = by_id[pid]
        if any(have.get((axis, _axis_value(p, axis)), 0) < MIN_CELL for axis in AXES):
            picked.append(pid)
            for axis in AXES:
                key = (axis, _axis_value(p, axis))
                have[key] = have.get(key, 0) + 1

    # pass 2: plain draw, so the comparison group is not composed only of rare cells
    if len(picked) < budget:
        taken = set(picked)
        for pid in pool:
            if len(picked) >= budget:
                break
            if pid not in taken:
                picked.append(pid)

    return picked


def reportable_cells(pop: Population, evaluated: list[str]) -> dict[str, dict[str, int]]:
    """Per axis, how many evaluated residents landed in each cell.

    Handed to the screen so a subgroup rate can be shown with its n, and a cell under
    MIN_CELL can be marked insufficient rather than rendered as a finding or as a zero.
    """
    by_id = pop.by_id()
    out: dict[str, dict[str, int]] = {axis: {} for axis in AXES}
    for pid in evaluated:
        p = by_id.get(pid)
        if p is None:
            continue
        for axis in AXES:
            v = _axis_value(p, axis)
            out[axis][v] = out[axis].get(v, 0) + 1
    return out
