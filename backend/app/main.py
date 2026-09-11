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

from app.config import env_int
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
from app.engine import DEFAULT_TOWN, build_run, study_area_for
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


class OrchestratorRun(BaseModel):
    """Optional body. `StartRunRequest` enforces a ten-character minimum, which is right
    for a proposal a planner typed and wrong here: running the graph with no policy at
    all is the ordinary case, and it exercises the prepared scenario."""

    policy_text: str = ""


@app.get("/api/orchestrator")
def orchestrator_graph() -> dict[str, Any]:
    """The execution graph as data: nodes, edges, and which of them reason.

    `AGENTS.md` §13 asks that the graph be explainable from a single diagram. This is the
    diagram's source, and it is generated from the list that executes, so a node cannot
    appear here without running or run without appearing.
    """
    from app.orchestrator import describe
    return describe()


@app.post("/api/orchestrator/run")
def orchestrator_run(req: OrchestratorRun | None = None) -> dict[str, Any]:
    """Execute the pipeline and report what each stage did.

    The answer to "what is the AI actually doing?" -- per node, with timings, and with
    the model-backed stages marked. `build_run()` produces the same result in one call
    and says nothing about how.
    """
    from app.orchestrator import run_pipeline

    # Counted from the telemetry, not inferred from how many model-backed nodes ran. The
    # two are not the same number and the difference is the interesting one: the
    # Deliberation node is model-backed and serves a recording, so a demo run reports two
    # model-backed stages and zero calls. Reporting the node count under the name
    # `model_calls` claimed a model had been consulted when none had, which is the exact
    # overstatement this project exists to object to.
    before = len(TELEMETRY.calls)
    state = run_pipeline(policy_text=(req.policy_text if req else ""))
    calls = TELEMETRY.calls[before:]
    return {
        "nodes": [{"name": r.name, "kind": r.kind, "ms": r.ms, "ok": r.ok,
                   "detail": r.detail, "error": r.error} for r in state.reports],
        "total_ms": sum(r.ms for r in state.reports),
        "model_backed_nodes": sum(1 for r in state.reports if r.kind == "model" and r.ok),
        "model_calls": len(calls),
        "tokens": sum(c.input_tokens + c.output_tokens for c in calls),
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "run_available": FIXTURE.exists(),
        "llm_provider": _llm.completion.name,
        "llm_calls": len(TELEMETRY.calls),
    }


def _deliberation_estimate_minutes(cohort: int) -> int:
    """Roughly how long deliberating this cohort would take, from measured throughput.

    Not a guess: 818 residents took 20 minutes on Claude 3 Haiku at this account's
    quota, and the same run on Sonnet was projected at over nine hours from its measured
    0.25 calls a minute. The cheaper figure is quoted because it is the one a person
    would actually wait for, and it is rounded hard -- a precise number here would imply
    a confidence the throttling does not support.
    """
    batches = max(1, cohort // BATCH_HINT) * ROUNDS_HINT
    return max(1, round(batches * SECONDS_PER_BATCH_HINT / 60))


#: measured on the Haiku run: 818 residents, ~161 calls, 20 minutes
BATCH_HINT = 12
ROUNDS_HINT = 2.4          # rounds 0 and 1 in full, later rounds far smaller
SECONDS_PER_BATCH_HINT = 7.4


class NotDeliberated(RuntimeError):
    """This policy has no recorded deliberation and the demo may not generate one.

    Not an error in the sense of something going wrong: it is an accurate description of
    a run whose residents have not been asked yet. The distinction matters because the
    alternative -- serving another policy's residents, or an empty list that reads as
    "nobody was affected" -- are both worse than saying so.
    """

    def __init__(self, policy: str, town: str, cohort: int):
        super().__init__("no recorded deliberation for this policy")
        self.policy = policy
        self.town = town
        self.cohort = cohort


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
def submit_feedback(consultation_id: str, body: FeedbackIn) -> dict[str, Any]:
    """Store one real submission, and mean it.

    This used to validate the body, mint an id, return `"status": "recorded"` and write
    nothing at all -- so a resident gave their view, the page confirmed it, and it was
    gone on the next restart. Saying "recorded" for something discarded is the exact
    failure `AGENTS.md` §28 forbids, and the loop this product demonstrates has its
    weakest link at precisely the "ask real people" step.
    """
    from app.consultation import record_feedback

    rid = record_feedback(consultation_id, body.model_dump())
    # the next run folds it in; the cached one predates it
    global _run_cache
    _run_cache = None
    return {"response_id": rid, "status": "recorded", "persisted": True}


class CalibrationDecision(BaseModel):
    approved: bool


@app.post("/api/runs/{run_id}/calibration/apply")
def apply_calibration(run_id: str, body: CalibrationDecision) -> dict[str, Any]:
    """Record a human ruling on the proposed correction, and act on it. L3.

    Never automatic: calibration proposes, a person decides, and the decision is stored
    either way. An approval puts the correction into force for subsequent runs, so the next
    calibration is computed against a model that has been told what it was missing -- and
    reports a smaller error, which is the point of measuring one.

    A rejection is recorded just as carefully. Knowing a change was put to someone and
    turned down is part of the audit trail, not the absence of one.
    """
    from app import calibration_state

    # A demo wants the human-approval boundary visible without a stray click rebuilding
    # every screen mid-presentation. The decision is still recorded -- that is the part
    # L3 actually requires -- but it is not put into force.
    ceremonial = os.getenv("CALIBRATION_APPLY_CEREMONIAL", "").strip().lower() in {"1", "true", "yes"}

    run = get_run(run_id)
    proposal = run.consultation.proposed_adjustment
    if not proposal or not proposal.parameter:
        raise HTTPException(422, "There is no proposed correction to rule on.")

    worst = min(run.consultation.calibration, key=lambda c: c.signed_error, default=None)
    live = calibration_state.record(calibration_state.Decision(
        parameter=proposal.parameter,
        value=float(proposal.to),
        # recorded either way; only put into force when this is not a demo
        approved=body.approved and not ceremonial,
        prompted_by_error_pp=float(worst.signed_error) if worst else 0.0,
        cohort=worst.cohort_value if worst else "",
    ))

    if not ceremonial:
        # the next run must be built against the corrected model, not the cached old one
        global _run_cache
        _run_cache = None
        _runs.pop(run_id, None)

    return {
        "status": "applied" if body.approved else "rejected",
        "recorded": True,
        "in_force": not ceremonial,
        "parameter": proposal.parameter,
        "value": float(proposal.to) if body.approved else None,
        "corrections_in_force": live,
        "history": len(calibration_state.history()),
    }


@app.get("/api/runs/{run_id}/calibration/history")
def calibration_history(run_id: str) -> dict[str, Any]:
    """Every ruling, approved or rejected, and what is in force now."""
    from app import calibration_state

    return {"in_force": calibration_state.applied(),
            "history": calibration_state.history()}


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
    from app.deliberate import REPLAY_ONLY, deliberate, load_recorded
    from app.engine import study_area_for
    from app.population import build_population
    from app.services.llm import build_deliberation_client
    from app.social import build_social_graph
    from app.world import build_world

    run = get_run(run_id)
    if run_id not in _deliberation_cache:
        # A finished run on disk wins over deliberating again.
        #
        # This is what makes a demo possible at all. Deliberating live is right for a
        # real study and takes hours on this account's quota, and the content-hash cache
        # cannot bridge the gap: it is keyed on the exact prompt, so the policy line
        # differing by three words misses every entry, and on a single model, while the
        # recorded run deliberately merges two. A replay is a real run shown again --
        # every turn was produced by a model and passed the grounding guard -- which is
        # exactly what `AGENTS.md` §22 sanctions and quite different from generating
        # substitute text when no model is available.
        town = (run.policy.study_area.town if run.policy.study_area
                and run.policy.study_area.town else DEFAULT_TOWN)
        recorded = load_recorded(town, run.policy.text)
        if recorded is not None:
            _deliberation_cache[run_id] = recorded
            return recorded

        # No recording for *this* policy, and replay-only forbids calling the model.
        #
        # Raise before building the world rather than after. Deliberating would take about
        # twenty minutes on the cheap model and hours on the better one, so a spinner here
        # would be a lie about what is happening; and running it anyway under replay-only
        # spends forty seconds constructing two thousand residents' facts only to skip
        # every batch and return nobody. The route turns this into a described state the
        # page can render honestly.
        if REPLAY_ONLY:
            from app.cohort import select_cohort
            from app.social import build_social_graph
            geo, closed, _ = study_area_for(run)
            pop = build_population(geo)
            raise NotDeliberated(
                policy=run.policy.text or "",
                town=town,
                cohort=len(select_cohort(
                    pop, build_world(pop, geo, closed, town=town),
                    build_social_graph(pop)).ids),
            )

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
            limit=env_int("DELIBERATION_LIMIT", 0) or None,
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
    except NotDeliberated as exc:
        # 202: the request is understood and the work has not been done. Carries what it
        # would take, so the page can say "818 residents, about 20 minutes" instead of
        # spinning on a promise nobody is keeping.
        raise HTTPException(202, detail={
            "status": "not_deliberated",
            "town": exc.town,
            "policy": exc.policy,
            "cohort": exc.cohort,
            "estimated_minutes": _deliberation_estimate_minutes(exc.cohort),
            "how": (f"python scripts/run_deliberation.py --town {exc.town}, then "
                    f"scripts/merge_deliberations.py, with DELIBERATION_REPLAY_ONLY=0"),
            "why": ("This policy closes different stops from the recorded run, so those "
                    "residents reasoned about a different question. Their answers are "
                    "not reused."),
        }) from exc
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
