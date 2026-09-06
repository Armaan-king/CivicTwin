"""Resident alternatives reach a human, and nothing is enacted without one.

`AGENTS.md` §14 forbids autonomous enactment of policy decisions. This is the point in the
loop where a person takes responsibility, so the selection is recorded and echoed back
rather than applied.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def client():
    from app import main
    return TestClient(main.app)


@pytest.fixture
def harmed(monkeypatch):
    from app import main
    from app.deliberate import DeliberationRun
    from app.schemas.deliberation import AgentTurn, AgentVoice

    run = main.get_run("latest")
    ids = [p.persona_id for p in run.personas[:6]]
    d = DeliberationRun(model="stub")
    d.population = len(run.personas)
    d.cohort = ids
    remedies = ["Keep the stop open at peak hours.", "Keep the stop open please.",
                "A shuttle bus would fix it.", "Somewhere to sit while I wait.",
                "Give us a fare subsidy.", "Bring it in gradually."]
    d.voices = {
        pid: AgentVoice(persona_id=pid, name="Tan Wei Ming", summary="", turns=[
            AgentTurn(persona_id=pid, round=1, severity="high", response="giving_up",
                      position=0.1, confidence=0.8, reasoning="My stop is closing.",
                      grounded_in=[f"{pid}:f4"], remedy=r)])
        for pid, r in zip(ids, remedies)
    }
    monkeypatch.setattr(main, "get_deliberation", lambda _r: d)
    return d


def test_listing_alternatives_never_scores_them(harmed):
    """Evaluation is another full deliberation, so it waits for a human to ask."""
    body = client().get("/api/runs/latest/alternatives").json()
    assert body["alternatives"], "residents asked for things and none were mapped"
    for alt in body["alternatives"]:
        assert alt["evaluated"] is False
        assert alt["metrics"] is None, "nothing is scored before it is evaluated"


def test_the_validator_runs_and_a_rejection_says_why(harmed):
    body = client().get("/api/runs/latest/alternatives").json()
    kinds = {a["kind"]: a for a in body["alternatives"]}
    assert "retain_stop_peak" in kinds
    for alt in body["alternatives"]:
        if not alt["valid"]:
            assert alt["validation_errors"], "a rejection must state a reason"


def test_what_the_action_space_cannot_express_reaches_the_screen(harmed):
    """The gap between what people need and what the model can represent is a finding."""
    body = client().get("/api/runs/latest/alternatives").json()
    labels = [u["label"] for u in body["unmappable"]]
    assert any("sit" in l or "shelter" in l for l in labels)
    assert body["asked"] == 6


def test_a_selection_is_recorded_and_never_enacted(harmed):
    c = client()
    posted = c.post("/api/runs/latest/alternatives/select",
                    json={"intervention_id": "resident_01", "note": "cheapest relief"}).json()
    assert posted["status"] == "recorded"
    assert posted["enacted"] is False

    got = c.get("/api/runs/latest/alternatives/selected").json()
    assert got["selected"]["intervention_id"] == "resident_01"
    assert got["selected"]["note"] == "cheapest relief"
    assert got["enacted"] is False


def test_no_selection_is_made_on_the_users_behalf(harmed):
    got = client().get("/api/runs/run_never_chosen/alternatives/selected").json()
    assert got["selected"] is None
