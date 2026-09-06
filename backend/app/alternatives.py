"""Re-deliberate an alternative, so a candidate can carry an outcome it earned.

The loop's last engineering step. A candidate that has only been validated is a proposal;
one that has been put back to the residents is a comparison. **J2** caps how many get that
far, and the rule that matters is the one from `IMPLEMENTING.md`: a rejected intervention
carries no metrics, because scoring something never evaluated is inventing a result.

What changes between the baseline run and an alternative is the *world*, not the people.
The same residents, the same seeds, the same social graph, reasoning about a different
network -- which is what makes the delta attributable to the intervention rather than to
reshuffled randomness (**G2**).

This is the expensive operation in the product. Each alternative is another deliberation,
so `J2`'s cap is a cost ceiling as much as a design one, and the cohort is what keeps it
affordable at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from app.aggregate import Aggregation, aggregate
from app.deliberate import DeliberationRun, deliberate
from app.geography import Geography
from app.interventions import Candidate
from app.metrics import metrics_for, subgroup_metrics
from app.population import Population
from app.services.llm import LLMClient
from app.world import build_world


@dataclass
class Evaluated:
    """A candidate that residents have actually reasoned about."""
    candidate: Candidate
    run: DeliberationRun | None = None
    aggregation: Aggregation | None = None
    metrics: dict | None = None
    #: severe harm under this alternative minus severe harm under the policy. Negative is
    #: an improvement, and it is only meaningful when both sides were evaluated over the
    #: same residents.
    severe_harm_delta: int | None = None
    compared_over: int = 0
    skipped: str | None = None


def closures_under(candidate: Candidate, closed: set[str]) -> set[str]:
    """Which stops are shut under this alternative.

    Only `retain_stop_peak` changes the network's shape in a way the world facts can
    express: the stop stays open, so the residents who lost it did not. The others act on
    fares, phasing or vehicles, which this fact layer does not model -- and a candidate
    whose effect cannot be represented must not be scored as though it were neutral.
    """
    if candidate.kind == "retain_stop_peak":
        keep = set(candidate.params.get("stop_ids") or closed)
        return set(closed) - keep
    return set(closed)


def evaluate(
    candidate: Candidate,
    baseline: DeliberationRun,
    pop: Population,
    geo: Geography,
    closed: set[str],
    policy_text: str,
    llm: LLMClient,
    social: nx.Graph | None = None,
) -> Evaluated:
    """Put one alternative back to the residents who deliberated the policy.

    Restricted to the baseline's evaluated set on purpose. A comparison across two
    different groups of people is not a comparison, and expanding the cohort here would
    make the alternative look better simply by asking calmer residents.
    """
    if not candidate.valid:
        return Evaluated(candidate, skipped="rejected by the validator, so never scored")

    cohort = baseline.evaluated
    if not cohort:
        return Evaluated(candidate, skipped="nobody was evaluated under the policy")

    alt_closed = closures_under(candidate, closed)
    if alt_closed == set(closed):
        return Evaluated(
            candidate,
            skipped=("this action changes fares, phasing or vehicles, which the world "
                     "facts do not model; it is not scored rather than scored as neutral"))

    # the same people, a different network
    alt_world = build_world(pop, geo, alt_closed)
    keep = set(cohort)
    slice_pop = Population(
        personas=[p for p in pop.personas if p.persona_id in keep],
        care_edges=[e for e in pop.care_edges
                    if e.carer in keep and e.dependent in keep],
    )

    run = deliberate(
        slice_pop,
        {pid: alt_world[pid] for pid in keep if pid in alt_world},
        f"{policy_text}\n\nALTERNATIVE UNDER CONSIDERATION: {candidate.name}. "
        f"{candidate.rationale}",
        llm,
        social=social.subgraph(keep).copy() if social is not None else None,
        cohort_ids=list(cohort),
    )

    agg = aggregate(run, slice_pop)
    outcomes = list(agg.outcomes.values())
    metrics = metrics_for(outcomes)

    base_agg = aggregate(baseline, pop)
    # compare only over residents evaluated on BOTH sides
    both = set(agg.outcomes) & set(base_agg.outcomes)
    delta = None
    if both:
        alt_severe = sum(1 for pid in both if agg.outcomes[pid].severity == "high")
        base_severe = sum(1 for pid in both if base_agg.outcomes[pid].severity == "high")
        delta = alt_severe - base_severe

    return Evaluated(
        candidate=candidate,
        run=run,
        aggregation=agg,
        metrics={"overall": metrics,
                 "subgroup": subgroup_metrics(slice_pop, agg.outcomes)},
        severe_harm_delta=delta,
        compared_over=len(both),
    )
