"""The grounding rule, tested.

A page of two thousand residents saying plausible things is worthless if any of it is
invented. These tests are the difference between a transcript and evidence.
"""
from __future__ import annotations

import pytest

from app.agents.persona_voice import batch_key, validate_grounding
from app.engine import EXPRESS_SAVING_MIN, study_area
from app.population import build_population
from app.schemas.voice import PersonaTurn, PersonaVoice
from app.simulation import simulate
from app.voices import generate_voices, write_offline


@pytest.fixture(scope="module")
def world():
    geo, removed = study_area()
    pop = build_population(geo, 400)
    return geo, pop, simulate(geo, pop, removed, EXPRESS_SAVING_MIN)


@pytest.fixture(scope="module")
def run(world):
    geo, pop, sim = world
    return generate_voices(pop, sim.outcomes, sim.events, geo, "test policy", "1", llm=None)


def test_every_resident_gets_a_voice(world, run):
    _, pop, _ = world
    assert {v.persona_id for v in run.voices} == {p.persona_id for p in pop.personas}


def test_no_voice_cites_an_event_that_is_not_theirs(world, run):
    """The rule the whole page rests on. A resident reasons about what happened to them."""
    _, _, sim = world
    mine: dict[str, set[str]] = {}
    for e in sim.events:
        mine.setdefault(e.persona_id, set()).add(e.event_id)
    for v in run.voices:
        assert not validate_grounding(v, mine.get(v.persona_id, set())), v.persona_id


def test_a_resident_with_no_events_claims_nothing(world, run):
    _, _, sim = world
    touched = {e.persona_id for e in sim.events}
    quiet = [v for v in run.voices if v.persona_id not in touched]
    assert quiet, "everyone was affected, so this proves nothing"
    for v in quiet:
        assert len(v.turns) == 1 and not v.turns[0].cites


def test_a_planted_hallucination_is_caught():
    """The validator must actually reject, or the tests above are decorative."""
    bad = PersonaVoice(
        persona_id="p_0001", name="Test", summary="",
        turns=[PersonaTurn(round=1, position=0.2, confidence=0.5,
                           reasoning="My stop closed.", cites=["e_99999"])],
    )
    assert validate_grounding(bad, {"e_00001"})


def test_positions_move_only_when_something_happened(world, run):
    _, _, sim = world
    touched = {e.persona_id for e in sim.events}
    for v in run.voices:
        if v.persona_id not in touched:
            assert v.moved == 0.0, v.persona_id


def test_harm_pushes_support_down(world, run):
    """If the worst-hit residents are not the least supportive, the voice layer is
    decorative and the page is theatre."""
    _, _, sim = world
    harmed = [v for v in run.voices if sim.outcomes[v.persona_id].severity == "high"]
    unaffected = [v for v in run.voices if sim.outcomes[v.persona_id].severity == "none"]
    assert harmed and unaffected
    avg = lambda vs: sum(v.turns[-1].position for v in vs) / len(vs)
    assert avg(harmed) < avg(unaffected) - 0.15


def test_voices_are_reproducible(world):
    geo, pop, sim = world
    a = generate_voices(pop, sim.outcomes, sim.events, geo, "p", "1", llm=None)
    b = generate_voices(pop, sim.outcomes, sim.events, geo, "p", "1", llm=None)
    assert [v.turns[-1].reasoning for v in a.voices] == [v.turns[-1].reasoning for v in b.voices]
    assert [v.name for v in a.voices] == [v.name for v in b.voices]


def test_the_cache_key_tracks_content_not_order():
    briefs = [{"persona_id": "p_1", "x": 1}, {"persona_id": "p_2", "x": 2}]
    assert batch_key(briefs, "1", "m") == batch_key(list(briefs), "1", "m")
    assert batch_key(briefs, "1", "m") != batch_key(briefs, "2", "m")
    assert batch_key(briefs, "1", "m") != batch_key([{"persona_id": "p_1", "x": 9}], "1", "m")


def test_the_offline_writer_is_labelled(run):
    """AGENTS.md 28: a template is never presented as a model output."""
    assert run.generated_by == "offline-template"
