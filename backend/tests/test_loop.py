"""The whole loop, once, with a stub model.

    policy -> deliberation -> harm explanation -> resident remedy
           -> validated intervention -> human selection -> consultation -> calibration

Each stage is tested on its own elsewhere. This asserts they compose: that what a resident
declared reaches the metrics, that what they asked for reaches the validator, and that
nothing scores an alternative nobody evaluated.

The stub exercises plumbing only and never reaches a screen -- `deliberate()` refuses a
mock outright, and this reaches past that deliberately (`AGENTS.md` §20).
"""
from __future__ import annotations

import json

import pytest

from app.aggregate import aggregate, support_comparison
from app.cohort import select_cohort
from app.deliberate import deliberate
from app.engine import study_area
from app.interventions import validate
from app.metrics import metrics_for
from app.population import build_population
from app.remedies import cluster_remedies, collect_remedies, resident_candidates
from app.services.llm import LLMClient
from app.social import build_social_graph
from app.world import build_world


class HarmedStub:
    """Every resident reports harm and asks for the same thing, so the loop has something
    to carry. Grounded by construction: it cites the facts it was handed."""

    name = "stub"

    def complete(self, system, prompt, max_tokens, schema=None):
        ids = [l.split()[1] for l in prompt.splitlines() if l.startswith("RESIDENT ")]
        facts = {
            pid: [w.strip("[]") for w in
                  prompt.split(f"RESIDENT {pid}\n")[1].split("\n\n")[0].split()
                  if w.startswith("[") and w.endswith("]")]
            for pid in ids
        }
        if "OpeningBatch" in prompt:
            return json.dumps({"voices": [
                {"persona_id": pid, "name": "Tan Wei Ming", "summary": "a resident",
                 "turns": [{"round": 0, "position": 0.6, "confidence": 0.4,
                            "reasoning": "I have only heard it will be faster.",
                            "severity": "none", "response": "unaffected",
                            "grounded_in": facts[pid][:1]}]}
                for pid in ids]})
        return json.dumps({"persona_ids": ids, "turns": [
            {"round": 1, "position": 0.1, "confidence": 0.9,
             "reasoning": "The stop I use is closing and I cannot walk to the next one.",
             "severity": "high", "response": "giving_up",
             "grounded_in": facts[pid],
             "remedy": "Keep the stop open at peak hours."}
            for pid in ids]})


@pytest.fixture(scope="module")
def loop():
    geo, closed, _ = study_area()
    pop = build_population(geo, 240)
    world = build_world(pop, geo, closed)
    social = build_social_graph(pop)
    run = deliberate(pop, world, "the whole loop policy", LLMClient(HarmedStub()),
                     social=social, limit=24)
    return pop, world, closed, run


def test_the_loop_carries_a_declaration_all_the_way_to_a_metric(loop):
    pop, world, closed, run = loop

    # deliberation happened, and only over the cohort
    assert run.voices, "nobody deliberated"
    assert len(run.evaluated) <= len(run.cohort) <= run.population

    # what residents declared becomes the outcomes, and the metrics count them
    agg = aggregate(run, pop)
    m = metrics_for(list(agg.outcomes.values()))
    assert m["n"] == len(agg.outcomes)
    assert m["severe_harm_count"] == m["n"], "every stub resident declared high severity"

    # the denominator travels with it, and never claims the unasked
    assert agg.coverage["evaluated"] == len(run.evaluated)
    assert agg.coverage["unevaluated"] == run.population - len(run.evaluated)
    assert agg.coverage["population"] == len(pop.personas)


def test_a_resident_request_becomes_a_validated_candidate(loop):
    pop, world, closed, run = loop

    report = cluster_remedies(collect_remedies(run))
    assert report.asked() > 0, "harmed residents were never asked"
    assert report.mapped, "nothing mapped onto the typed action space"

    cands = resident_candidates(report, removed=set(closed))
    assert cands
    for c in cands:
        assert c.result is None, "unevaluated alternatives must carry no outcome"
        validate(c, fleet_increase_allowed=False)
        assert isinstance(c.valid, bool)
        if not c.valid:
            assert c.validation_errors, "a rejection must say why"
            assert c.result is None, "a rejected candidate is never scored"


def test_both_support_predictions_are_produced_for_calibration(loop):
    """P3/L1: the frozen logistic survives, so calibration has something to compare."""
    pop, world, closed, run = loop
    agg = aggregate(run, pop)
    rows = support_comparison(pop, agg.declared_support, agg.outcomes)
    assert rows
    for row in rows:
        assert row["n"] > 0
        assert 0.0 <= row["frozen_support"] <= 1.0
        assert 0.0 <= row["declared_support"] <= 1.0
        assert row["sufficient"] == (row["n"] >= 30)


def test_the_cohort_is_chosen_not_sliced(loop):
    """`personas[:n]` returns whoever the generator emitted first, which on this
    population is people nowhere near the closure who correctly report nothing."""
    pop, world, closed, run = loop
    cohort = select_cohort(pop, world, build_social_graph(pop), comparison=0)
    assert set(run.cohort) <= set(cohort.ids)
    affected = set(cohort.affected)
    assert any(pid in affected for pid in run.cohort), \
        "a capped run must still reach the residents the policy touches"
