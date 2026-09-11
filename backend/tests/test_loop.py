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
        return json.dumps({"turns": [
            {"persona_id": pid, "round": 1, "position": 0.1, "confidence": 0.9,
             "reasoning": "The stop I use is closing and I cannot walk to the next one.",
             "severity": "high", "response": "giving_up",
             "grounded_in": facts[pid],
             "changed_because": "my stop is closing",
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


def test_an_unexplained_change_is_counted_but_never_deletes_a_harm_claim():
    """The bias that rejecting on continuity introduced, held shut by a test.

    Only a *change* needs explaining, so a guard that rejects unexplained moves removes
    residents who declared harm and keeps residents who reported nothing. Measured on a
    real run: seven turns dropped from twelve residents, every survivor unaffected -- a
    run made to look harmless by its own safeguard.
    """
    import json

    from app.deliberate import deliberate
    from app.engine import study_area
    from app.population import build_population
    from app.services.llm import LLMClient
    from app.social import build_social_graph
    from app.world import build_world

    class SilentlyMoves:
        """Declares harm in round 1 and never says what changed it."""

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
                    {"persona_id": pid, "name": "Tan Wei Ming", "summary": "s",
                     "turns": [{"round": 0, "position": 0.5, "confidence": 0.5,
                                "reasoning": "Only heard it will be faster.",
                                "severity": "none", "response": "unaffected",
                                "grounded_in": facts[pid][:1]}]} for pid in ids]})
            return json.dumps({"turns": [
                {"persona_id": pid, "round": 1, "position": 0.1, "confidence": 0.9,
                 "reasoning": "My stop is closing and I cannot walk the distance.",
                 "severity": "high", "response": "giving_up",
                 "grounded_in": facts[pid]}          # no changed_because
                for pid in ids]})

    geo, closed, _ = study_area()
    pop = build_population(geo, 120)
    world = build_world(pop, geo, closed)
    run = deliberate(pop, world, "unexplained movement policy", LLMClient(SilentlyMoves()),
                     social=build_social_graph(pop), limit=8)

    assert run.unexplained_moves > 0, "the flag must fire"
    harmed = [v for v in run.voices.values()
              if any(t.severity == "high" for t in v.turns)]
    assert harmed, "a harm claim was deleted for being inarticulate"
    assert run.coverage()["unexplained_moves"] == run.unexplained_moves


def test_every_consultation_comment_is_a_resident_s_own_words():
    """No pool, no fallback, no borrowed sentence.

    The comments used to come from seven strings in `consultation.py`; across 136
    synthetic responses one of them appeared 73 times. Every other figure on that screen
    is computed from the run, so the words beside them were the one piece of furniture
    left -- and a screen that presents furniture as public feedback is the exact claim
    this product exists to object to.

    A comment must now be the resident's own final reasoning from the recorded
    deliberation, and a resident who never deliberated must carry none. The tempting fix
    when that thins the screen out is to borrow a neighbour's sentence, which is the same
    fabrication in a better costume, so it is pinned here.
    """
    from app.deliberate import recorded_words
    from app.engine import build_run, study_area_for_town, DEFAULT_TOWN

    _, removed = study_area_for_town(DEFAULT_TOWN)
    said = recorded_words(removed)
    assert said, "no recording matched the demo closure; the rest of this proves nothing"

    run = build_run()
    commented = [r for r in run["consultation"]["responses"]
                 if r.get("is_seeded") and r.get("comment")]
    assert commented, "every synthetic comment vanished"

    for r in commented:
        assert r["comment"] == said.get(r["persona_id"]), (
            f"{r['persona_id']} carries a comment that is not their own recorded words"
        )

    # and the giveaway that a pool has crept back: the same sentence twice
    texts = [r["comment"] for r in commented]
    assert len(set(texts)) == len(texts), "a comment is repeated across residents"


def test_the_severity_check_compares_the_rule_with_the_residents():
    """Two judges, same question, same people -- and the product must show both.

    `severity_for()` produces every headline number; the residents judged themselves in
    the deliberation. They disagree on two people in five, and the disagreement is
    one-directional: the rule calls people unharmed who say they are not.
    """
    from app.engine import build_run

    c = build_run()["severity_check"]
    assert c is not None, "no recording matched the demo policy"
    assert c["cohort"] > 0
    assert c["agree"] <= c["cohort"]
    assert 0 <= c["agree_rate"] <= 1
    assert c["called_unharmed_but_severe"] <= c["by_residents"]


def test_no_recording_means_no_severity_check_rather_than_no_disagreement():
    """The dangerous default.

    With nothing to compare against, a zero-disagreement figure would be the most
    misleading number on the page: it reads as "the rule and the residents agree" when it
    means "nobody has been asked". Absent is the honest answer.
    """
    from app.engine import _severity_check

    assert _severity_check({"p1": object()}, {}) is None
