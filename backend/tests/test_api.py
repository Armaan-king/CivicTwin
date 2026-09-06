"""Routes hold their contract, and failures surface as the right status."""
from fastapi.testclient import TestClient
import pytest
from app import main
from app.main import app
from app.services.llm import build_client

client = TestClient(app)
GOOD = "Remove the two stops on Ang Mo Kio Avenue 3 from service 265 and run non-stop."


@pytest.fixture(autouse=True)
def offline_interpreter(monkeypatch):
    """API contract tests never use the developer's configured live provider."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(main, "_llm", build_client())


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


def test_a_blank_env_knob_reads_as_unset(monkeypatch):
    """`.env` documents an unused knob as `NAME=`, and int("") raises.

    DELIBERATION_LIMIT was cleared to mean "the whole cohort" and took the /voices route
    down with a 500 the moment anyone opened it.
    """
    from app.config import env_float, env_int

    monkeypatch.setenv("CIVICTWIN_TEST_KNOB", "")
    assert env_int("CIVICTWIN_TEST_KNOB", 12) == 12
    assert env_float("CIVICTWIN_TEST_KNOB", 0.8) == 0.8

    monkeypatch.setenv("CIVICTWIN_TEST_KNOB", "  ")
    assert env_int("CIVICTWIN_TEST_KNOB", 12) == 12

    monkeypatch.setenv("CIVICTWIN_TEST_KNOB", "6")
    assert env_int("CIVICTWIN_TEST_KNOB", 12) == 6


def test_a_nonsense_env_knob_says_which_one(monkeypatch):
    from app.config import env_int

    monkeypatch.setenv("CIVICTWIN_TEST_KNOB", "banana")
    with pytest.raises(ValueError, match="CIVICTWIN_TEST_KNOB"):
        env_int("CIVICTWIN_TEST_KNOB", 12)
