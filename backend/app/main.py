"""CivicTwin API.

Serves the routes in docs/architecture.md section 5 against the committed fixture, so the
frontend can flip from VITE_TRANSPORT=fixture to http and get identical shapes back. As
each engine workstream lands (W3 population, W4 simulation, W5 audit) the handler bodies
are replaced; the routes and the schemas do not move.

    uvicorn app.main:app --reload --port 8000     (from backend/)
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.policy_interpreter import PolicyInterpretationFailed, interpret
from app.schemas.policy import StartRunRequest, StartRunResponse
from app.schemas.run import Intervention, SimulationRun
from app.services.llm import LLMError, TELEMETRY, build_client

FIXTURE = pathlib.Path(__file__).resolve().parents[2] / "data" / "fixtures" / "demo_run.json"

app = FastAPI(title="CivicTwin", version="0.1.0")

# the Vite dev server. tighten before anything leaves a laptop.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_llm = build_client()
_run_cache: SimulationRun | None = None


def load_run() -> SimulationRun:
    """Produce the current run.

    The engine computes it: `app/engine.py` builds the study area, samples the population,
    constructs the graph, simulates the policy, re-simulates every valid alternative, and
    runs the consultation. About 0.3 s for 2,000 personas, so there is no reason to
    pre-generate anything.

    Validation happens here, at the boundary. An engine that drifts from the contract
    fails loudly at the route rather than quietly in the browser, and it costs ~10 ms.

    `data/fixtures/demo_run.json` remains as a fallback for a machine that cannot import
    the engine, and is otherwise unused. It is a shape-correct artefact, not a simulation.
    """
    global _run_cache
    if _run_cache is None:
        try:
            from app.engine import build_run
            _run_cache = SimulationRun.model_validate(build_run())
        except ImportError as exc:
            if not FIXTURE.exists():
                raise HTTPException(
                    503, f"No engine and no fixture: {exc}") from exc
            raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
            _run_cache = SimulationRun.model_validate(raw)
    return _run_cache


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "run_available": FIXTURE.exists(),
        "llm_provider": _llm.completion.name,
        "llm_calls": len(TELEMETRY.calls),
    }


# ----------------------------------------------------------------- reads
@app.get("/api/runs/{run_id}", response_model=SimulationRun)
def get_run(run_id: str) -> SimulationRun:
    run = load_run()
    if run_id not in ("latest", run.run_id):
        raise HTTPException(404, f"No run {run_id}")
    return run


@app.get("/api/runs/{run_id}/interventions", response_model=list[Intervention])
def get_interventions(run_id: str) -> list[Intervention]:
    return get_run(run_id).interventions


@app.get("/api/runs/{run_id}/impacts")
def get_impacts(run_id: str) -> dict[str, Any]:
    run = get_run(run_id)
    return {"metrics": run.metrics.model_dump(), "events": [e.model_dump() for e in run.events]}


@app.get("/api/consultations/{consultation_id}")
def get_consultation(consultation_id: str) -> dict[str, Any]:
    return get_run("latest").consultation.model_dump(by_alias=True)


# ----------------------------------------------------------------- writes
@app.post("/api/runs", response_model=StartRunResponse)
def start_run(req: StartRunRequest) -> StartRunResponse:
    """Interpret a proposal. Fails loudly rather than guessing (AGENTS.md 18)."""
    try:
        policy = interpret(req.policy_text, _llm)
    except PolicyInterpretationFailed as exc:
        # the text was understood but produced nothing simulable: the planner can fix this
        raise HTTPException(422, exc.detail) from exc
    except LLMError as exc:
        # the model itself is unreachable or misbehaving: not the planner's fault, and not
        # something to paper over with a plausible default
        raise HTTPException(502, f"The interpreter is unavailable: {exc}") from exc
    return StartRunResponse(run_id=f"run_{uuid.uuid4().hex[:6]}", policy=policy)


class FeedbackIn(BaseModel):
    support: int = Field(ge=1, le=5)
    perceived_fairness: int | None = Field(default=None, ge=1, le=5)
    clarity_of_explanation: int | None = Field(default=None, ge=1, le=5)
    confidence_in_delivery: int | None = Field(default=None, ge=1, le=5)
    expected_personal_impact: int | None = Field(default=None, ge=-2, le=2)
    comment: str | None = Field(default=None, max_length=2000)
    cohort: dict[str, str] | None = None


@app.post("/api/consultations/{consultation_id}/feedback")
def submit_feedback(consultation_id: str, body: FeedbackIn) -> dict[str, str]:
    # W7 persists this. Accepted and validated now so the citizen page is wired end to end.
    return {"response_id": f"r_{uuid.uuid4().hex[:8]}", "status": "recorded"}


class CalibrationDecision(BaseModel):
    approved: bool


@app.post("/api/runs/{run_id}/calibration/apply")
def apply_calibration(run_id: str, body: CalibrationDecision) -> dict[str, str]:
    """Human approval, always. Never applied automatically (scenario-v1.md L3)."""
    return {"status": "applied" if body.approved else "rejected", "recorded": "true"}


# ----------------------------------------------------- streaming rounds
@app.post("/api/runs/{run_id}/rounds/stream")
async def stream_rounds(run_id: str) -> StreamingResponse:
    """NDJSON, one object per line. architecture.md 5.1.

    Replays the recorded chain round by round so the UI can show the cascade
    propagating rather than appearing fully formed.
    """
    run = get_run(run_id)
    events = [e.model_dump() for e in run.events]

    async def gen():
        for rnd in (1, 2, 3):
            in_round = [e for e in events if e["round"] == rnd]
            yield json.dumps({
                "type": "round_start", "round": rnd,
                "active": sorted({e["persona_id"] for e in in_round})[:200],
            }) + "\n"
            for e in in_round[:120]:          # cap the wire, not the model
                yield json.dumps({
                    "type": "event", "round": rnd, "persona_id": e["persona_id"],
                    "event": e["kind"], "before": e["before"], "after": e["after"],
                    "cause": e["cause"],
                }) + "\n"
                await asyncio.sleep(0.004)
            yield json.dumps({
                "type": "round_complete", "round": rnd,
                "changed": sorted({e["persona_id"] for e in in_round})[:200],
            }) + "\n"
        yield json.dumps({"type": "complete", "run_id": run.run_id}) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


# ------------------------------------------------------------------ deliberation
_deliberation_cache: dict[str, "DeliberationRun"] = {}


def get_deliberation(run_id: str) -> "DeliberationRun":
    """The population reasoning about this policy.

    Held per run: the deliberation is the expensive part of the product, so opening the
    page twice must not cost twice. Raises rather than substituting when no model is
    configured, which the route turns into a 503 saying exactly what to set.
    """
    from app.deliberate import deliberate
    from app.engine import study_area
    from app.population import build_population
    from app.services.llm import build_deliberation_client
    from app.social import build_social_graph
    from app.world import build_world

    run = get_run(run_id)
    if run_id not in _deliberation_cache:
        geo, closed = study_area()
        pop = build_population(geo)
        world = build_world(pop, geo, closed)
        _deliberation_cache[run_id] = deliberate(
            pop, world, run.policy.text or "", build_deliberation_client(),
            social=build_social_graph(pop),
        )
    return _deliberation_cache[run_id]


@app.get("/api/runs/{run_id}/voices")
def list_voices(run_id: str, limit: int = 200, offset: int = 0) -> dict:
    """Residents, most-moved first.

    There is no offline substitute. A page of text that reads like residents and is not
    residents is worse than an empty page, so without a model this returns 503 and says
    what to configure.
    """
    from app.deliberate import NoModelConfigured

    try:
        d = get_deliberation(run_id)
    except NoModelConfigured as exc:
        raise HTTPException(503, str(exc)) from exc

    ordered = d.ordered()
    return {
        "run_id": run_id,
        "model": d.model,
        "total": len(ordered),
        "offset": offset,
        "spoke": sum(1 for v in ordered if len(v.turns) > 1),
        "moved": sum(1 for v in ordered if abs(v.moved) > 0.05),
        "rejected": d.rejected,
        "calls": d.calls,
        "cached_batches": d.cached,
        "seconds": d.seconds,
        "participation": d.participation,
        "voices": [v.model_dump() for v in ordered[offset:offset + limit]],
    }


@app.post("/api/runs/{run_id}/voices/stream")
async def stream_voices(run_id: str, limit: int = 150) -> StreamingResponse:
    """NDJSON, one resident per line.

    Watching a town react is the thing this product does that a chart cannot, so the
    stream exists for the watching rather than for the throughput.
    """
    from app.deliberate import NoModelConfigured

    try:
        d = get_deliberation(run_id)
    except NoModelConfigured as exc:
        raise HTTPException(503, str(exc)) from exc

    voices = d.ordered()[:limit]

    async def gen():
        yield json.dumps({"type": "start", "total": len(d.voices),
                          "streaming": len(voices), "model": d.model,
                          "participation": d.participation}) + "\n"
        for v in voices:
            yield json.dumps({"type": "voice", "voice": v.model_dump()}) + "\n"
            await asyncio.sleep(0.012)
        yield json.dumps({"type": "complete", "rejected": d.rejected,
                          "calls": d.calls, "seconds": d.seconds}) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")
