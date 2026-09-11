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


def test_a_demo_run_reports_zero_model_calls():
    """Model-backed nodes are not model calls, and the report must not conflate them.

    Both stages that can reason are served without asking: the Policy Interpreter gets no
    proposal on the prepared scenario, and the Deliberation loads a recording. So the
    honest report is two model-backed nodes and zero calls.

    This asserted the opposite until a run with deliberately broken credentials printed
    `model_calls: 1` while the telemetry showed none -- the count was of nodes, under a
    name that claimed a model had been consulted.
    """
    body = client.post("/api/orchestrator/run", json={"policy_text": ""}).json()
    assert body["model_backed_nodes"] == 2
    assert body["model_calls"] == 0, "the demo path must not call a model"
    assert body["tokens"] == 0


def test_running_the_graph_does_not_change_what_the_demo_shows():
    """The graph shares the engine's memoised functions with every screen.

    If it seeded them with arguments differing from `build_run()`'s by one field, the
    demo would read the graph's version instead, show a different number than it did in
    rehearsal, and fail nothing -- which is what makes it worth a test rather than a
    one-off check.
    """
    import hashlib

    paths = ["/api/runs/latest", "/api/runs/latest/interventions",
             "/api/runs/latest/alternatives", "/api/runs/latest/deliberated"]
    digest = lambda: {p: hashlib.sha256(client.get(p).content).hexdigest() for p in paths}

    before = digest()
    client.post("/api/orchestrator/run", json={"policy_text": ""})
    assert digest() == before
