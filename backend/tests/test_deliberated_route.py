"""The route that serves resident-declared numbers, and how it refuses.

The refusal matters as much as the result: without a model there is no substitute for a
deliberation, and a page of text that reads like residents and is not residents is worse
than an empty page (`AGENTS.md` §20, §22).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services.llm import LLMError


def client():
    from app import main
    return TestClient(main.app)


def test_it_refuses_rather_than_substituting_when_no_model_is_configured(monkeypatch):
    from app import main
    from app.deliberate import NoModelConfigured

    def refuse(_run_id):
        raise NoModelConfigured("Set LLM_PROVIDER=ollama in the project root .env")

    monkeypatch.setattr(main, "get_deliberation", refuse)
    response = client().get("/api/runs/latest/deliberated")
    assert response.status_code == 503
    assert "LLM_PROVIDER" in response.json()["detail"]


def test_a_provider_failure_is_reported_not_hidden(monkeypatch):
    from app import main

    def fail(_run_id):
        raise LLMError("Ollama could not be reached")

    monkeypatch.setattr(main, "get_deliberation", fail)
    response = client().get("/api/runs/latest/deliberated")
    assert response.status_code == 502
    assert "Ollama" in response.json()["detail"]


def test_the_payload_states_what_was_declared_and_what_was_computed(monkeypatch):
    """Provenance travels with the numbers, because the whole V2 claim is about where
    severity came from."""
    from app import main
    from app.deliberate import DeliberationRun
    from app.schemas.deliberation import AgentTurn, AgentVoice

    run = main.get_run("latest")
    ids = [p.persona_id for p in run.personas[:8]]
    d = DeliberationRun(model="deepseek-r1:8b")
    d.population = len(run.personas)
    d.cohort = ids
    d.cohort_strata = {"affected": len(ids), "tied": 0, "comparison": 0}
    d.voices = {
        pid: AgentVoice(persona_id=pid, name="Tan Wei Ming", summary="", turns=[
            AgentTurn(round=1, severity="high", response="giving_up", position=0.1,
                      confidence=0.8, reasoning="My stop is closing and I cannot walk it.",
                      grounded_in=[f"{pid}:f4"], remedy="Keep the stop open at peak hours.")])
        for pid in ids
    }
    monkeypatch.setattr(main, "get_deliberation", lambda _r: d)

    body = client().get("/api/runs/latest/deliberated").json()
    assert body["model"] == "deepseek-r1:8b"
    assert "severity" in body["provenance"]["declared_by_residents"]
    assert "walk_distance_m" in body["provenance"]["computed_from_the_network"]

    # the denominator travels with the rate
    cov = body["coverage"]
    assert cov["population"] == len(run.personas)
    assert cov["evaluated"] == len(ids)
    assert cov["unevaluated"] == len(run.personas) - len(ids)

    # residents declared harm, so the metrics must show it
    assert body["metrics"]["overall"]["severe_harm_count"] == len(ids)

    # and their own words became a candidate of a typed kind
    assert body["remedies"]["asked"] == len(ids)
    assert body["remedies"]["mapped"][0]["action_type"] == "retain_stop_peak"


def test_subgroup_cells_below_the_floor_are_named_insufficient(monkeypatch):
    """Insufficient evidence is not zero disparity, and the payload has to say which."""
    from app import main
    from app.cohort import MIN_CELL
    from app.deliberate import DeliberationRun
    from app.schemas.deliberation import AgentTurn, AgentVoice

    run = main.get_run("latest")
    ids = [p.persona_id for p in run.personas[:5]]      # deliberately tiny
    d = DeliberationRun(model="test")
    d.population = len(run.personas)
    d.cohort = ids
    d.voices = {
        pid: AgentVoice(persona_id=pid, name="n", summary="", turns=[
            AgentTurn(round=1, severity="none", response="unaffected", position=0.5,
                      confidence=0.5, reasoning="Nothing changed.", grounded_in=[f"{pid}:f1"])])
        for pid in ids
    }
    monkeypatch.setattr(main, "get_deliberation", lambda _r: d)

    body = client().get("/api/runs/latest/deliberated").json()
    assert body["metrics"]["min_cell"] == MIN_CELL
    flagged = body["metrics"]["insufficient_cells"]
    assert any(cells for cells in flagged.values()), \
        "five residents cannot fill any subgroup cell, and the payload must say so"
