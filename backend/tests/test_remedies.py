"""J4: residents author remedies, and what cannot be mapped is reported rather than dropped."""
from __future__ import annotations

from app.remedies import cluster_remedies, collect_remedies
from app.deliberate import DeliberationRun
from app.schemas.deliberation import AgentTurn, AgentVoice


def test_requests_map_onto_the_typed_action_space():
    report = cluster_remedies({
        "p_1": "Just keep the stop open in the morning when I go to the clinic.",
        "p_2": "Please do not close the bus stop outside my block.",
        "p_3": "A shuttle to the stop that is staying open would be enough.",
        "p_4": "Give us a fare subsidy so I can take a taxi.",
        "p_5": "Bring it in gradually so we can get used to it.",
    })
    kinds = {c.action_type: c.count for c in report.mapped}
    assert kinds["retain_stop_peak"] == 2
    assert kinds["add_shuttle_feeder"] == 1
    assert kinds["targeted_support"] == 1
    assert kinds["phase_rollout"] == 1
    assert report.unmappable == []


def test_what_the_action_space_cannot_express_is_reported_not_discarded():
    """The gap between what people need and what the model can represent is a finding.

    A model that quietly dropped these would be hiding exactly the thing J4 exists to show.
    """
    report = cluster_remedies({
        "p_1": "Somewhere to sit and wait would make all the difference.",
        "p_2": "A shelter over the new walk, it is very hot.",
        "p_3": "If the clinic gave me a later appointment I could manage.",
        "p_4": "Someone to walk with me would help.",
    })
    assert report.mapped == []
    labels = {c.label: c.count for c in report.unmappable}
    assert labels["somewhere to sit or shelter while waiting"] == 2
    assert labels["a different appointment or working time"] == 1
    assert labels["someone to go with them"] == 1


def test_every_resident_asked_is_accounted_for():
    """Mapped, unmappable, or silent. Nothing falls off the edge."""
    remedies = {
        "p_1": "Keep the stop open.",
        "p_2": "Somewhere to sit.",
        "p_3": "",
        "p_4": "   ",
        "p_5": "A feeder bus please.",
    }
    report = cluster_remedies(remedies)
    assert report.asked() == len(remedies)
    assert report.silent == 2


def test_clusters_carry_the_residents_and_their_own_words():
    """A reader must be able to check the cluster against what was actually said."""
    report = cluster_remedies({"p_9": "Please keep the bus stop open at peak hours."})
    c = report.mapped[0]
    assert c.residents == ["p_9"]
    assert c.examples == ["Please keep the bus stop open at peak hours."]
    assert c.count == 1


def voice(pid, severity, remedy, rounds=1):
    return AgentVoice(persona_id=pid, name="n", summary="", turns=[
        AgentTurn(round=r, severity=severity, response="adapting" if severity != "none" else "unaffected",
                  position=0.3, confidence=0.6, reasoning="x", grounded_in=[f"{pid}:f4"],
                  remedy=remedy if r == rounds else None)
        for r in range(1, rounds + 1)])


def test_only_harmed_residents_are_asked():
    run = DeliberationRun(model="t")
    run.voices = {
        "p_1": voice("p_1", "high", "Keep the stop open."),
        "p_2": voice("p_2", "none", None),
    }
    collected = collect_remedies(run)
    assert "p_1" in collected
    assert "p_2" not in collected, "an unaffected resident has nothing to remedy"


def test_a_remedy_given_in_an_earlier_round_is_still_heard():
    """Someone who said what they needed once and then stopped repeating it still counts."""
    run = DeliberationRun(model="t")
    v = voice("p_1", "high", "A shuttle would do it.", rounds=3)
    run.voices = {"p_1": v}
    assert collect_remedies(run)["p_1"] == "A shuttle would do it."


def test_a_harmed_resident_who_offered_nothing_is_counted_as_silent():
    run = DeliberationRun(model="t")
    run.voices = {"p_1": voice("p_1", "high", None)}
    collected = collect_remedies(run)
    assert collected == {"p_1": ""}
    assert cluster_remedies(collected).silent == 1


def test_resident_proposals_go_through_the_same_validator():
    """J4: no shortcut, no exemption. And they arrive unscored."""
    from app.interventions import validate
    from app.remedies import resident_candidates

    report = cluster_remedies({
        "p_1": "Keep the stop open at peak hours.",
        "p_2": "A shuttle bus would fix it.",
    })
    cands = resident_candidates(report, removed={"54231", "54239"})
    assert {c.kind for c in cands} == {"retain_stop_peak", "add_shuttle_feeder"}
    for c in cands:
        assert c.result is None, "a candidate must carry no outcome before it is evaluated"

    # the constraint the policy declares still binds a resident's proposal
    shuttle = next(c for c in cands if c.kind == "add_shuttle_feeder")
    validate(shuttle, fleet_increase_allowed=False)
    assert shuttle.valid is False
    assert any("fleet" in e for e in shuttle.validation_errors)
    assert shuttle.result is None, "a rejected candidate is never scored"

    keep = next(c for c in cands if c.kind == "retain_stop_peak")
    validate(keep, fleet_increase_allowed=False)
    assert keep.valid is True


def test_a_resident_proposal_carries_who_asked_and_in_whose_words():
    from app.remedies import resident_candidates

    report = cluster_remedies({"p_1": "Keep the stop open.", "p_2": "Do not close the stop."})
    c = resident_candidates(report, removed={"54231"})[0]
    assert "2 residents asked for this" in c.rationale
    assert "Keep the stop open." in c.rationale
