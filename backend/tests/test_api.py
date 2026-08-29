"""Routes hold their contract, and failures surface as the right status."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
GOOD = "Remove the two stops on Ang Mo Kio Avenue 3 from service 265 and run non-stop."


def test_health():
    assert client.get("/health").json()["ok"] is True


def test_run_carries_the_fields_the_frontend_reads():
    run = client.get("/api/runs/latest").json()
    for key in ("personas", "outcomes", "events", "metrics", "interventions", "consultation"):
        assert key in run, key
    assert run["is_synthetic"] is True


def test_unknown_run_is_404():
    assert client.get("/api/runs/does-not-exist").status_code == 404


def test_vague_proposal_is_422_not_a_guess():
    r = client.post("/api/runs", json={"policy_text": "make the buses nicer somehow please"})
    assert r.status_code == 422


def test_good_proposal_interprets():
    r = client.post("/api/runs", json={"policy_text": GOOD})
    assert r.status_code == 200
    assert r.json()["policy"]["modifications"]["remove_stops"]


def test_feedback_validates_the_scale():
    assert client.post("/api/consultations/c1/feedback", json={"support": 9}).status_code == 422
    assert client.post("/api/consultations/c1/feedback", json={"support": 4}).status_code == 200


def test_rejected_interventions_are_never_scored():
    for i in client.get("/api/runs/latest/interventions").json():
        if not i["valid"]:
            assert i["metrics"] is None
            assert i["validation_errors"]


def test_round_stream_is_ndjson_and_chains():
    with client.stream("POST", "/api/runs/latest/rounds/stream", json={}) as r:
        assert r.headers["content-type"].startswith("application/x-ndjson")
        kinds = [line for line in r.iter_lines() if line]
    assert any('"type": "complete"' in k or '"type":"complete"' in k for k in kinds)
