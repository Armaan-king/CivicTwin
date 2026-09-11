"""The diagram and the run must describe the same graph.

`GET /api/orchestrator` draws the pipeline and `POST /api/orchestrator/run` executes it.
Both read `PIPELINE`, which is the point of declaring it as data -- but "both read the
same list" is only true until someone hand-maintains one of them, and the failure is
silent: a slide showing nine stages while ten run looks exactly like a correct slide.

That is not hypothetical. This module's own docstring claimed nine nodes and three models
while `describe()` reported ten and two, which is the same error the architecture slide
made and the reason any of this exists.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.orchestrator import PIPELINE, describe

client = TestClient(app)


def test_description_is_generated_from_what_executes():
    d = describe()
    assert [n["name"] for n in d["nodes"]] == [name for name, _, _ in PIPELINE]
    assert d["model_backed"] + d["deterministic"] == len(PIPELINE)
    # a linear pipeline has exactly one edge between each adjacent pair
    assert len(d["edges"]) == len(PIPELINE) - 1
    assert all(e["from"] and e["to"] for e in d["edges"])


def test_every_node_says_whether_it_reasons():
    """The whole claim rests on this label, so it may not be blank or invented."""
    assert all(kind in ("model", "deterministic") for _, kind, _ in PIPELINE)
    assert all(n["doc"] for n in describe()["nodes"]), "a stage with no docstring"


def test_the_graph_endpoint_matches_the_module():
    body = client.get("/api/orchestrator").json()
    assert body["nodes"] == describe()["nodes"]


def test_a_run_reports_every_stage():
    """Including the ones that fail: a stage that errors is recorded, not dropped."""
    body = client.post("/api/orchestrator/run", json={"policy_text": ""}).json()
    assert [n["name"] for n in body["nodes"]] == [name for name, _, _ in PIPELINE]
    assert body["total_ms"] == sum(n["ms"] for n in body["nodes"])
