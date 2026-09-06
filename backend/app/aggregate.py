"""Turn what residents said into the numbers the screens show.

This is the seam the V2 pivot turns on. `metrics.py` is unchanged and still canonical --
the six metrics of **I1**, the four axes of **I4**, the n >= 30 floor. What changes is
where two fields of an `Outcome` come from.

    computed, and still computed      walk_distance_m, journey_time_delta_min
                                      geometry: distances, routes, who lost a stop

    declared, and no longer computed  severity, adaptation, essential-trip completion,
                                      support

`AGENTS.md` §10 draws exactly this line: distance and geometry are world facts, retrieved
and handed to the agents; judging consequence, severity, adaptation and opinion "is exactly
what the agents are for, and that judgement is no longer to be moved back into code."

Nothing here invents an outcome for a resident who did not produce one. A resident who was
never asked, or whose every turn failed the grounding guard, has no `Outcome` at all --
they are absent from the denominator rather than counted as unharmed. `coverage()` on the
run is what says how many that is.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.deliberate import DeliberationRun
from app.population import Population
from app.schemas.deliberation import AgentVoice
from app.simulation import Outcome

#: How a resident's declared `response` maps onto the adaptation vocabulary the rest of
#: the codebase already speaks. The left side is what a person does; the right side is the
#: label `simulation.py` and the event log were built around.
ADAPTATION = {
    "unaffected": "continue_transit",
    "absorbing": "continue_transit",
    "adapting": "reroute",
    "substituting": "switch_mode",
    "delegating": "delegate",
    "giving_up": "abandon_trip",
}

#: A declared response that means the essential trip did not happen.
TRIP_LOST = {"giving_up"}


@dataclass
class Aggregation:
    outcomes: dict[str, Outcome] = field(default_factory=dict)
    #: resident-declared support, 0..1, for the calibration comparison in L1/P3
    declared_support: dict[str, float] = field(default_factory=dict)
    #: residents who claimed to have taken on someone else's journey
    absorbing: dict[str, str] = field(default_factory=dict)
    #: the denominator story, carried with the numbers rather than beside them
    coverage: dict = field(default_factory=dict)


def _final(voice: AgentVoice):
    return voice.turns[-1] if voice.turns else None


def aggregate(
    run: DeliberationRun,
    pop: Population,
    geometry: dict[str, Outcome] | None = None,
) -> Aggregation:
    """Build one `Outcome` per *evaluated* resident.

    `geometry` supplies the computed half -- walk distance, journey time delta -- keyed by
    persona id, from the fact layer that also fed the agents their numbers. Where it is
    missing a resident simply carries no geometry; the declared fields still stand, because
    a resident saying they have given up a trip is a finding whether or not we can price
    the walk.
    """
    geometry = geometry or {}
    out = Aggregation(coverage=run.coverage())

    for pid, voice in run.voices.items():
        turn = _final(voice)
        if turn is None:
            # asked, nothing survived the guard: unevaluated, not unharmed
            continue

        base = geometry.get(pid)
        o = Outcome(
            persona_id=pid,
            # ---------------------------------------------------- declared
            severity=turn.severity,
            adaptation=ADAPTATION.get(turn.response, "continue_transit"),
            second_order=bool(turn.absorbing_for),
            # ---------------------------------------------------- computed
            walk_distance_m=base.walk_distance_m if base else 0,
            baseline_walk_m=base.baseline_walk_m if base else 0,
            journey_time_min=base.journey_time_min if base else 0.0,
            journey_time_delta_min=base.journey_time_delta_min if base else 0.0,
        )

        # Essential trips are declared too. A resident who says they have stopped going is
        # the finding; a rule that infers it from walking distance is the thing V2 removed.
        person = pop.by_id().get(pid)
        essential = 1 if (person and person.needs_clinic) else 0
        o.essential_trips_total = essential
        o.essential_trips_completed = (
            0 if (essential and turn.response in TRIP_LOST) else essential)
        o.accessibility_status = "lost" if o.essential_trips_completed < essential else "ok"

        out.outcomes[pid] = o
        out.declared_support[pid] = turn.position
        if turn.absorbing_for:
            out.absorbing[pid] = turn.absorbing_for

    return out


def declared_support_by_cohort(
    pop: Population, declared: dict[str, float], axis: str
) -> dict[str, dict]:
    """Mean declared support per cohort, with its n.

    Paired against the frozen logistic in `calibration`. Per **L2** the count travels with
    the number, so a cohort of six is visibly a cohort of six rather than a finding.
    """
    by_id = pop.by_id()
    buckets: dict[str, list[float]] = {}
    for pid, value in declared.items():
        p = by_id.get(pid)
        if p is None:
            continue
        buckets.setdefault(str(getattr(p, axis)), []).append(value)
    return {
        key: {"n": len(vals), "mean_support": round(sum(vals) / len(vals), 4)}
        for key, vals in sorted(buckets.items()) if vals
    }


def support_comparison(
    pop: Population,
    declared: dict[str, float],
    outcomes: dict[str, Outcome],
    axis: str = "age_band",
) -> list[dict]:
    """P3: both predictions, side by side, on one documented scale.

    **L1** keeps the logistic and **P3** says why: it is inspectable and its error
    attributes to a named coefficient, while the reasoning is richer and its error does
    not. Keeping both turns that weakness into a result -- which is only true if somebody
    actually computes both, which is what this does.

    Three columns per cohort:

        frozen      the L1 logistic, which does not know about terrain by design
        declared    what residents said during deliberation
        n           the denominator, carried per L2 so a cohort of six reads as six

    The gap between the first two is the finding: where structured reasoning and a fitted
    curve disagree is where one of them is wrong, and the consultation says which.
    """
    from app.consultation import predicted_support
    from app.support_scale import likert_to_fraction, signed_error_pp

    by_id = pop.by_id()
    buckets: dict[str, dict[str, list[float]]] = {}
    for pid, position in declared.items():
        p = by_id.get(pid)
        o = outcomes.get(pid)
        if p is None or o is None:
            continue
        key = str(getattr(p, axis))
        cell = buckets.setdefault(key, {"frozen": [], "declared": []})
        cell["frozen"].append(likert_to_fraction(predicted_support(p, o)))
        cell["declared"].append(position)

    rows = []
    for key, cell in sorted(buckets.items()):
        n = len(cell["declared"])
        frozen = sum(cell["frozen"]) / n
        spoken = sum(cell["declared"]) / n
        rows.append({
            "cohort_axis": axis,
            "cohort_value": key,
            "n": n,
            "frozen_support": round(frozen, 4),
            "declared_support": round(spoken, 4),
            "divergence_pp": signed_error_pp(frozen, spoken),
            # Under the floor a gap is noise wearing a finding's clothes (L2, I3).
            "sufficient": n >= 30,
        })
    return rows
