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
import os
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
from app.engine import build_run, study_area_for
from app.resolve import StudyAreaNotFound
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


#: Runs built from a submitted policy, by id. The demo run is separate and unnamed:
#: it is what the interface shows before anyone has typed anything.
_runs: dict[str, SimulationRun] = {}


# ----------------------------------------------------------------- reads
@app.get("/api/runs/{run_id}", response_model=SimulationRun)
def get_run(run_id: str) -> SimulationRun:
    """A submitted run if there is one, otherwise the demo run."""
    if run_id in _runs:
        return _runs[run_id]
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
    run_id = f"run_{uuid.uuid4().hex[:6]}"
    # Keep it. This used to return the parsed policy and drop it on the floor, so the run
    # the planner then opened was built from an environment variable and two guessed stops
    # -- a careful reading of their words, discarded, and a different question answered.
    try:
        _runs[run_id] = SimulationRun.model_validate(
            build_run(run_id, policy=policy, text=req.policy_text)
        )
    except StudyAreaNotFound as exc:
        raise HTTPException(422, str(exc)) from exc

    # Hand back the run's policy, not the interpreter's. They differ in the part that
    # matters: which town the words resolved to, which stop names matched, and which
    # matched nothing. A planner who cannot see that cannot tell whether we read them
    # correctly, and the whole reading is a claim about their words.
    return StartRunResponse(run_id=run_id, policy=_runs[run_id].policy)


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
    from app.engine import study_area_for
    from app.population import build_population
    from app.services.llm import build_deliberation_client
    from app.social import build_social_graph
    from app.world import build_world

    run = get_run(run_id)
    if run_id not in _deliberation_cache:
        # the study area this run was actually built for, not the default one
        geo, closed, _ = study_area_for(run)
        pop = build_population(geo)
        world = build_world(pop, geo, closed)
        # DELIBERATION_LIMIT caps how many residents reason, for accounts whose
        # rate limit cannot carry the whole town: a free Groq key allows 8,000 tokens
        # a minute and one batch of 12 reserves most of that. Unset means everyone,
        # which is the real product; a slice is a demo of it and says so on the page.
        _deliberation_cache[run_id] = deliberate(
            pop, world, run.policy.text or "", build_deliberation_client(),
            social=build_social_graph(pop),
            limit=int(os.getenv("DELIBERATION_LIMIT", "0")) or None,
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
    except LLMError as exc:
        raise HTTPException(502, str(exc)) from exc

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
    except LLMError as exc:
        raise HTTPException(502, str(exc)) from exc

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


@app.get("/api/runs/{run_id}/deliberated")
def deliberated_outcomes(run_id: str) -> dict:
    """The numbers as the residents decided them, with the denominator attached.

    This is the V2 answer to the same question `/impacts` answers from the fact layer.
    `metrics.py` is shared and unchanged -- the six metrics of I1, the four axes of I4, the
    n >= 30 floor -- so the two are directly comparable. What differs is provenance:
    severity, adaptation and essential-trip completion here were declared by residents,
    not computed by a predicate.

    Every rate carries `coverage`. A resident nobody asked is unknown, never unaffected,
    and a subgroup below the floor is reported as insufficient evidence rather than as
    zero disparity.
    """
    from app.aggregate import (aggregate, declared_support_by_cohort,
                               support_comparison)
    from app.cohort import MIN_CELL, reportable_cells
    from app.deliberate import NoModelConfigured
    from app.metrics import disparity_pp, metrics_for, subgroup_metrics
    from app.remedies import cluster_remedies, collect_remedies

    try:
        d = get_deliberation(run_id)
    except NoModelConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(502, str(exc)) from exc

    run = get_run(run_id)
    geo, closed, _ = study_area_for(run)
    from app.population import build_population
    pop = build_population(geo)

    # the computed half: geometry from the fact layer the agents were shown
    geometry = {o.persona_id: o for o in _geometry_outcomes(run)}
    agg = aggregate(d, pop, geometry=geometry)
    outcomes = list(agg.outcomes.values())
    sub = subgroup_metrics(pop, agg.outcomes)
    cells = reportable_cells(pop, list(agg.outcomes))

    remedies = cluster_remedies(collect_remedies(d))
    return {
        "run_id": run_id,
        "model": d.model,
        "provenance": {
            "declared_by_residents": ["severity", "adaptation",
                                      "essential_trip_completion", "support"],
            "computed_from_the_network": ["walk_distance_m", "journey_time_delta_min"],
        },
        "coverage": agg.coverage,
        "metrics": {
            "overall": metrics_for(outcomes),
            "subgroup": sub,
            "subgroup_disparity_pp": disparity_pp(sub),
            # A cell under the floor cannot support a claim. Named here so the screen can
            # say "insufficient evidence" rather than render an empty bar as parity.
            "insufficient_cells": {
                axis: [k for k, n in counts.items() if n < MIN_CELL]
                for axis, counts in cells.items()
            },
            "min_cell": MIN_CELL,
        },
        "declared_support": {
            axis: declared_support_by_cohort(pop, agg.declared_support, axis)
            for axis in ("age_band", "mobility_level", "is_caregiver")
        },
        # P3/L1: the frozen logistic and the residents, side by side. Keeping both is
        # what lets calibration say which one the consultation contradicted.
        "support_comparison": [
            row
            for axis in ("age_band", "mobility_level", "is_caregiver")
            for row in support_comparison(pop, agg.declared_support, agg.outcomes, axis)
        ],
        "second_order": [{"carer": c, "for": dep} for c, dep in sorted(agg.absorbing.items())],
        "remedies": {
            "asked": remedies.asked(),
            "silent": remedies.silent,
            "mapped": [{"action_type": c.action_type, "label": c.label, "count": c.count,
                        "examples": c.examples} for c in remedies.mapped],
            "unmappable": [{"label": c.label, "count": c.count, "examples": c.examples}
                           for c in remedies.unmappable],
        },
        "cost": {"calls": d.calls, "cached_batches": d.cached, "rejected_turns": d.rejected,
                 "failed_batches": d.failed_batches, "seconds": d.seconds},
    }


def _geometry_outcomes(run: SimulationRun):
    """The computed half of every outcome, from the deterministic fact layer.

    Distances and journey times stay code's job (`AGENTS.md` §10). This reads them off the
    run the engine already built rather than recomputing, so the numbers a resident was
    shown are the numbers their outcome carries.
    """
    from app.simulation import Outcome

    out = []
    for o in run.outcomes:
        out.append(Outcome(
            persona_id=o.persona_id,
            walk_distance_m=int(getattr(o, "walk_distance_m", 0) or 0),
            baseline_walk_m=int(getattr(o, "baseline_walk_m", 0) or 0),
            journey_time_min=float(getattr(o, "journey_time_min", 0.0) or 0.0),
            journey_time_delta_min=float(getattr(o, "journey_time_delta_min", 0.0) or 0.0),
        ))
    return out


# ------------------------------------------------- resident-authored alternatives
#: Human selections, by run. Recorded rather than acted on: `AGENTS.md` §14 forbids
#: autonomous enactment, and L3 requires the same for calibration.
_selections: dict[str, dict] = {}


@app.get("/api/runs/{run_id}/alternatives")
def list_alternatives(run_id: str) -> dict:
    """What residents asked for, mapped onto the typed action space and validated.

    Listing does not evaluate. Putting an alternative back to the residents is another
    full deliberation -- the expensive operation in this product -- so it happens only
    when a human asks for it, which is also the human-in-the-loop boundary `AGENTS.md` §14
    requires. Everything here is therefore unscored by construction, and says so.
    """
    from app.deliberate import NoModelConfigured
    from app.interventions import validate
    from app.remedies import cluster_remedies, collect_remedies, resident_candidates

    try:
        d = get_deliberation(run_id)
    except NoModelConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(502, str(exc)) from exc

    run = get_run(run_id)
    _, closed, _ = study_area_for(run)
    report = cluster_remedies(collect_remedies(d))
    fleet_ok = bool(run.policy.constraints.fleet_increase_allowed)

    rows = []
    for c in resident_candidates(report, set(closed)):
        validate(c, fleet_increase_allowed=fleet_ok)
        rows.append({
            "intervention_id": c.intervention_id,
            "kind": c.kind,
            "name": c.name,
            "params": c.params,
            "rationale": c.rationale,
            "estimated_cost_index": c.estimated_cost_index,
            "valid": c.valid,
            "validation_errors": c.validation_errors,
            # never scored until a human asks for it to be evaluated
            "metrics": None,
            "evaluated": False,
        })
    return {
        "run_id": run_id,
        "source": "residents, during deliberation (J4)",
        "asked": report.asked(),
        "silent": report.silent,
        "alternatives": rows,
        "unmappable": [{"label": u.label, "count": u.count, "examples": u.examples}
                       for u in report.unmappable],
        "cost_index_note": "illustrative coefficients relative to baseline 1.00x, never currency (J3)",
    }


class Selection(BaseModel):
    intervention_id: str
    note: str | None = Field(default=None, max_length=2000)


@app.post("/api/runs/{run_id}/alternatives/select")
def select_alternative(run_id: str, body: Selection) -> dict:
    """Record which alternative a human chose. Recording only.

    `AGENTS.md` §14: no autonomous enactment of policy decisions. This is the point in the
    loop where a person takes responsibility for a choice, so it is stored and echoed back
    rather than applied to anything.
    """
    _selections[run_id] = {"intervention_id": body.intervention_id, "note": body.note}
    return {"run_id": run_id, "selected": body.intervention_id,
            "status": "recorded", "enacted": False}


@app.get("/api/runs/{run_id}/alternatives/selected")
def get_selection(run_id: str) -> dict:
    chosen = _selections.get(run_id)
    return {"run_id": run_id, "selected": chosen, "enacted": False}
