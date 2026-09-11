"""The planner's output is treated as a proposal, never as a result.

A model now selects and parameterises the alternatives. That is only safe because of what
happens to what it returns: the kind is pinned by the tool schema, every parameter
`run_candidate` reaches into is validated, and whatever survives is re-simulated by the
same engine over the same residents with the same seeds.

These tests use a hand-written plan file rather than a live call, on purpose. The question
is not whether the model writes good alternatives -- the comparison screen answers that in
public, by simulating them. It is whether a bad one can do damage, and the cheapest way to
ask is to write the bad one deliberately.
"""
from __future__ import annotations

import json

import pytest

from app import engine, plan
from app.engine import DEFAULT_TOWN, study_area_for_town


@pytest.fixture
def planned(tmp_path, monkeypatch):
    """Install a plan for the demo closure, containing one good and two poisoned rows."""
    _, removed = study_area_for_town(DEFAULT_TOWN)
    closed = sorted(removed)
    rows = [
        # a sane one, so the good path is exercised too
        {"intervention_id": "iv_a", "kind": "retain_stop_peak", "name": "Peak retention",
         "params": {"stops": closed, "hours": "07:00-09:30"},
         "rationale": "Give the corridor back during the commute.",
         "estimated_cost_index": 1.02},
        # the expensive honest one the prompt asks for: rejected, never scored
        {"intervention_id": "iv_b", "kind": "add_shuttle_feeder", "name": "Full network",
         "params": {"serves": ["54247"], "headway_min": 8, "vehicles": 6},
         "rationale": "Cover every subzone at commuter frequency.",
         "estimated_cost_index": 1.40},
        # the dangerous one: a shuttle calling at the stop the policy closed
        {"intervention_id": "iv_c", "kind": "add_shuttle_feeder", "name": "Undo in a hat",
         "params": {"serves": closed, "headway_min": 10},
         "rationale": "Serve the closed stops directly.",
         "estimated_cost_index": 1.01},
    ]
    monkeypatch.setattr(plan, "RUNS", tmp_path)
    (tmp_path / "interventions-test.json").write_text(json.dumps(
        {"town": "test", "closed": closed, "model": "test-model-v1", "candidates": rows}),
        encoding="utf-8")
    engine._INTERVENTION_CACHE.clear()
    yield rows
    engine._INTERVENTION_CACHE.clear()


def test_the_plan_is_used_and_says_who_wrote_it(planned):
    ivs = engine.build_run()["interventions"]
    assert [i["intervention_id"] for i in ivs] == ["iv_a", "iv_b", "iv_c"]
    assert {i["planned_by"] for i in ivs} == {"test-model-v1"}


def test_a_proposal_serving_the_closed_stop_is_rejected(planned):
    """The failure that would look like the best result on the screen.

    A shuttle calling at the stop the policy shut drives harm to zero. It reads as a
    brilliant intervention and is the original service wearing a hat, and because it
    scores well it is the one a human would pick.
    """
    undo = next(i for i in engine.build_run()["interventions"]
                if i["intervention_id"] == "iv_c")
    assert not undo["valid"]
    assert undo["metrics"] is None
    assert "closed stop" in " ".join(undo["validation_errors"])


def test_an_over_budget_proposal_is_rejected_with_its_reason(planned):
    over = next(i for i in engine.build_run()["interventions"]
                if i["intervention_id"] == "iv_b")
    assert not over["valid"] and over["metrics"] is None
    assert any("ceiling" in e or "fleet" in e for e in over["validation_errors"])


def test_a_valid_proposal_is_actually_simulated(planned):
    """Scored by the engine, not by the planner. The model supplies no number here."""
    good = next(i for i in engine.build_run()["interventions"]
                if i["intervention_id"] == "iv_a")
    assert good["valid"]
    assert good["metrics"]["n"] == 2000
    assert good["carers_harmed"] is not None


def test_without_a_plan_the_hand_written_list_still_runs():
    """The fallback has to work, and has to admit that it is the fallback."""
    engine._INTERVENTION_CACHE.clear()
    ivs = engine.build_run()["interventions"]
    engine._INTERVENTION_CACHE.clear()
    assert ivs, "no alternatives at all"
    assert {i["planned_by"] for i in ivs} == {"enumerated in code"}
