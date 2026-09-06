"""The groundedness guard, watched failing.

`AGENTS.md` §20: "a guard nobody has watched fail is not a guard." Every test here plants
a specific lie and asserts it is caught, because the guard is the only thing standing
between a deliberation and a chat log.
"""
from __future__ import annotations

import pytest

from app.agents.deliberation import check_grounding
from app.schemas.deliberation import AgentTurn
from app.world import Fact, ResidentWorld


def world_with(**kw) -> ResidentWorld:
    """A resident who knows three things before the policy and two after."""
    w = ResidentWorld(persona_id="p_0001", **kw)
    w.facts = [
        Fact(id="p_0001:f1", text="Your nearest stop is Blk 129 (54231), 210 m away.", round=0),
        Fact(id="p_0001:f2", text="You are 72, retired.", round=0),
        Fact(id="p_0001:f3", text="Your household does not have a car.", round=0),
        Fact(id="p_0001:f4", text="The policy closes Blk 129 (54231).", round=1),
        Fact(id="p_0001:f5", text="A neighbour moved away.", round=3),
    ]
    return w


def turn(**kw) -> AgentTurn:
    base = dict(round=1, position=0.4, confidence=0.6, reasoning="I walk further now.",
                grounded_in=["p_0001:f4"])
    base.update(kw)
    return AgentTurn(**base)


def test_a_fabricated_fact_id_is_rejected():
    problems = check_grounding(turn(grounded_in=["p_0001:f9"]), world_with(), 1, set())
    assert any("f9" in p for p in problems)


def test_a_fact_from_a_later_round_is_rejected():
    """The bug this scoping fixed: f5 exists, but not yet.

    Checking against every fact the resident will *ever* hold let a round-1 turn cite a
    round-3 fact and pass. The question is not whether the fact exists somewhere, it is
    whether this resident had been told it when it spoke.
    """
    problems = check_grounding(turn(grounded_in=["p_0001:f5"]), world_with(), 1, set())
    assert any("f5" in p and "not given" in p for p in problems)
    # and it is legitimate once round 3 has actually arrived
    assert check_grounding(turn(round=3, grounded_in=["p_0001:f5"]), world_with(), 3, set()) == []


def test_harm_cited_only_from_pre_policy_facts_is_rejected():
    """A citation id proves the fact was supplied, not that it supports the claim.

    Being 72 and having no car were both true before anyone proposed anything. They cannot
    establish that the policy did something, so a harm claim resting only on them is not
    grounded even though every id is real.
    """
    problems = check_grounding(
        turn(severity="high", response="giving_up",
             grounded_in=["p_0001:f2", "p_0001:f3"]),
        world_with(), 1, set())
    assert any("already true before the policy" in p for p in problems)


def test_the_same_harm_claim_passes_when_it_reaches_a_policy_fact():
    assert check_grounding(
        turn(severity="high", response="giving_up",
             grounded_in=["p_0001:f2", "p_0001:f4"]),
        world_with(), 1, set()) == []


def test_citing_nothing_at_all_is_rejected():
    assert check_grounding(turn(grounded_in=[]), world_with(), 1, set()) != []


def test_an_unheard_neighbour_is_rejected():
    problems = check_grounding(
        turn(influenced_by="p_0777"), world_with(), 1, heard_from={"p_0002"})
    assert any("p_0777" in p for p in problems)


def test_a_heard_neighbour_is_allowed():
    assert check_grounding(
        turn(influenced_by="p_0002"), world_with(), 1, heard_from={"p_0002"}) == []


def test_household_membership_does_not_imply_being_heard():
    """Who you live with is not who you were shown this round.

    These were the same set before, so a resident could claim their spouse changed their
    mind in a round where the spouse never spoke.
    """
    w = world_with(household=["p_0002"])
    problems = check_grounding(turn(influenced_by="p_0002"), w, 1, heard_from=set())
    assert any("never heard from them" in p for p in problems)


def test_absorbing_for_a_stranger_is_rejected():
    w = world_with(household=["p_0002"])
    problems = check_grounding(turn(absorbing_for="p_0999"), w, 1, {"p_0002"})
    assert any("not in their household" in p for p in problems)


def test_absorbing_for_a_household_member_is_allowed():
    w = world_with(household=["p_0002"])
    assert check_grounding(turn(absorbing_for="p_0002"), w, 1, set()) == []


def test_influenced_by_itself_is_rejected():
    problems = check_grounding(turn(influenced_by="p_0001"), world_with(), 1, {"p_0001"})
    assert any("influenced by itself" in p for p in problems)


@pytest.mark.parametrize("field,value", [("position", 1.4), ("position", -0.2),
                                         ("confidence", 2.0), ("round", 9)])
def test_out_of_range_values_are_rejected_not_clamped(field, value):
    """Bounds are enforced by refusing the turn, never by quietly moving the number.

    A clamped value is a number the resident did not say, presented as one they did. The
    local grammar cannot enforce `minimum`/`maximum`, so this is the layer that must.
    """
    with pytest.raises(Exception):
        turn(**{field: value})
