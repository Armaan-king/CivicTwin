"""Simulated consultation, calibration, and the blind spot. K1-K5, L1-L3.

The point of this module is not to generate plausible survey data. It is to make the model
**wrong in a way it can be caught being wrong**, because a calibration screen that always
agrees with itself proves nothing.

So there are two functions of support and they differ on purpose:

`predicted_support` is what the model believes, from three persona quantities and the
outcome it computed. `observed_support` is what residents actually say, and it carries a
**terrain penalty the prediction function does not have**: on AMK Ave 3 the covered walkway
ends partway and there is a slope, so the same 400 metres costs more than the model thinks.

That gap is a real, attributable error rather than injected noise. It is discoverable only
by cohort, it stays under the flag line in aggregate, and finding it is the demonstration.

Two guards that are not optional (**L2**, **L3**): nothing is flagged on fewer than 30
responses, and no adjustment is ever applied without a human.
"""
from __future__ import annotations

from collections.abc import Mapping

import json
import pathlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.population import Persona, Population
from app.rng import derived_rng
from app.simulation import Outcome

#: the subzone where the walk is worse than its distance suggests. The model does not know.
#: The road whose walk is worse than its distance suggests, and which the model does not
#: know about. It is **the road the closures are on**, passed in by the caller rather than
#: named here: the story is that a planner's model costed a distance and not a walk, and
#: that is true of whichever road the policy touches. Naming one road made the penalty
#: apply to nobody in every other town, so calibration flagged nothing and the screen
#: quietly proved that the model was perfect.
DEFAULT_TERRAIN_ROAD = ""
#: points of support lost, on the 1-5 scale, at a full-length walk. The covered walkway
#: ends partway and there is a slope, so the penalty scales with how far someone actually
#: walks rather than switching on at a threshold: 200 m of it is an irritation, 600 m in
#: the rain with shopping is a different journey from the one the model costed.
TERRAIN_PENALTY = 1.10
TERRAIN_FULL_EFFECT_M = 600.0
FLAG_ERROR_PP = 10.0            # L2: both conditions, always
FLAG_MIN_N = 30


@dataclass
class Response:
    response_id: str
    persona_id: str
    support: int
    perceived_fairness: int
    clarity_of_explanation: int
    confidence_in_delivery: int
    expected_personal_impact: int
    comment: str | None
    cohort: dict[str, str | None]
    is_seeded: bool = True
    #: "model" for a simulated resident, "form" for a person who used the page,
    #: "demo-seed" for invented data staged to populate a screen.
    source: str = "model"


@dataclass
class CalibrationRow:
    cohort_axis: str
    cohort_value: str
    predicted_support: float
    observed_support: float
    signed_error: float
    n: int
    flagged: bool


@dataclass
class BlindSpot:
    """W12, K5. Who the consultation is least likely to hear from, weighted by harm."""
    cohort_axis: str
    cohort_value: str
    harmed: int
    expected_responses: int
    score: float


@dataclass
class ConsultationResult:
    responses: list[Response]
    calibration: list[CalibrationRow]
    blind_spots: list[BlindSpot] = field(default_factory=list)
    pcs_components: dict[str, int] = field(default_factory=dict)
    pcs: int = 0


# --------------------------------------------------------------- real submissions
#: Feedback actually submitted by a person, appended one JSON object per line.
#:
#: The endpoint used to validate a submission, mint a response id, return
#: `"status": "recorded"` and write nothing. A resident gave their view, the page
#: confirmed it, and it was gone -- which is the one failure mode `AGENTS.md` §28 names
#: outright: never describe a mocked path as live. The comment beside it said "W7
#: persists this", a promise that had not been kept.
FEEDBACK = pathlib.Path(__file__).resolve().parents[2] / "data" / "feedback"


def record_feedback(consultation_id: str, payload: dict) -> str:
    """Append one real submission. Returns its id."""
    import uuid

    FEEDBACK.mkdir(parents=True, exist_ok=True)
    rid = f"h_{uuid.uuid4().hex[:8]}"
    row = dict(payload, response_id=rid, consultation_id=consultation_id,
               submitted_at=datetime.now(timezone.utc).isoformat(),
               # "form" is a person who used the page. "demo-seed" is invented data put
               # here to populate the screen. They must never be indistinguishable: a
               # file of fabricated submissions counted as real replies is precisely the
               # claim this product exists to object to.
               source=payload.get("source", "form"))
    path = FEEDBACK / f"{consultation_id}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return rid


def load_feedback(consultation_id: str) -> list[Response]:
    """Real submissions, as Responses. `is_seeded=False` is the whole point.

    A real reply carries no persona: nobody submitting a form is one of the synthetic
    residents. It therefore has no *predicted* support -- prediction is a function of a
    persona's traits and computed outcome -- so these are counted in the public
    confidence score and in any cohort they self-report, and excluded from the
    prediction-versus-report comparison, which would otherwise average a prediction that
    does not exist.
    """
    path = FEEDBACK / f"{consultation_id}.jsonl"
    if not path.exists():
        return []
    out: list[Response] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue                      # a torn write is skipped, never guessed at
        out.append(Response(
            response_id=raw.get("response_id", "h_?"),
            persona_id="",                # deliberately empty: not a synthetic resident
            support=int(raw.get("support", 3)),
            perceived_fairness=int(raw.get("perceived_fairness") or 3),
            clarity_of_explanation=int(raw.get("clarity_of_explanation") or 3),
            confidence_in_delivery=int(raw.get("confidence_in_delivery") or 3),
            expected_personal_impact=int(raw.get("expected_personal_impact") or 0),
            comment=raw.get("comment"),
            cohort=raw.get("cohort") or {},
            is_seeded=False,
            source=raw.get("source", "form"),
        ))
    return out


def _impact_score(o: Outcome) -> int:
    """How this person expects the policy to land on them, -2 to +2."""
    if o.severity == "high":
        return -2
    if o.severity == "moderate":
        return -1
    if o.journey_time_delta_min < -0.5:
        return 1
    return 0


def walk_cost_key(subzone: str) -> str:
    """The name a correction is stored under, so proposal and application agree."""
    return f"walk_cost_multiplier[{subzone}]"


def predicted_support(p: Persona, o: Outcome,
                      corrections: dict[str, float] | None = None) -> float:
    """L1. An explicit function of three persona quantities and the computed outcome.

    Deliberately does not know about terrain. That omission is the thing calibration is
    supposed to find, and `baseline_trust` is therefore the parameter it tests.

    `corrections` are the adjustments a human has approved. Unapplied -- the default -- this
    is the original function and reproduces the original error, which is what makes the
    error attributable in the first place. With a walk-cost multiplier in force for a
    subzone, the model finally costs the *walk* rather than the distance, and its prediction
    for that road drops toward what residents there actually reported.

    Three declared coefficients and one optional correction, all visible here. `GOAL.md` §20
    forbids hiding weights inside prompts; the same applies to a correction, which is why it
    is a number in a file a human approved rather than a nudge buried in a model call.
    """
    base = 1.6 + 2.6 * p.baseline_trust
    base += 0.55 * _impact_score(o)
    base += 0.40 * p.inconvenience_tolerance

    if corrections:
        multiplier = corrections.get(walk_cost_key(p.home_subzone))
        if multiplier and multiplier > 1.0:
            # the walk this resident actually faces, priced at the corrected rate
            share = min(1.0, o.walk_distance_m / TERRAIN_FULL_EFFECT_M)
            base -= (multiplier - 1.0) * share

    return max(1.0, min(5.0, base))


def observed_support(p: Persona, o: Outcome, predicted: float,
                     terrain_road: str = DEFAULT_TERRAIN_ROAD) -> float:
    """What residents actually say. Prediction, plus what the model did not know."""
    rng = derived_rng(f"{p.persona_id}:support")
    value = predicted + rng.gauss(0, 0.45)
    if terrain_road and p.home_subzone == terrain_road:
        share = min(1.0, o.walk_distance_m / TERRAIN_FULL_EFFECT_M)
        value -= TERRAIN_PENALTY * share
    return max(1.0, min(5.0, value))


def response_probability(p: Persona, o: Outcome) -> float:
    """Who answers a consultation. The participation gap, as a function rather than a claim.

    Response falls with age and with mobility limitation, and those are exactly the people
    the policy hurts most. This is not cynicism about surveys; it is the reason a
    consultation that looks reassuring can be reassuring about the wrong population, and
    it is what `blind_spots` below quantifies.
    """
    q = 0.24
    q -= {"<18": 0.14, "18-34": 0.02, "35-54": 0.0,
          "55-64": 0.02, "65-74": 0.07, "75+": 0.12}[p.age_band]
    q -= {"none": 0.0, "mild": 0.03, "moderate": 0.07, "severe": 0.11}[p.mobility_level]
    q += 0.10 * (p.baseline_trust - 0.5)
    if o.severity in ("high", "moderate"):
        q += 0.05          # the harmed are motivated, but not enough to close the gap
    return max(0.02, min(0.60, q))




def build_consultation(pop: Population, outcomes: dict[str, Outcome],
                       terrain_road: str = DEFAULT_TERRAIN_ROAD,
                       corrections: dict[str, float] | None = None,
                       words: Mapping[str, str] | None = None) -> ConsultationResult:
    """`corrections` are the adjustments a human has approved.

    `words` maps a persona to what they said in the recorded deliberation, and is the only
    source of a comment. A resident who did not deliberate leaves the field empty; there
    is no pool to fall back on, because a pool is what this replaced.

    They move the *prediction* only. What residents reported is fixed -- `observed_support`
    is seeded per persona and does not change -- so applying a correction narrows the gap
    from one side, which is the side that was wrong.
    """
    by_id = pop.by_id()
    responses: list[Response] = []

    for p in pop.personas:
        o = outcomes[p.persona_id]
        rng = derived_rng(f"{p.persona_id}:respond")
        if rng.random() > response_probability(p, o):
            continue
        # The reported answer is anchored to the *uncorrected* prediction: a resident's
        # experience does not change because the model revised its opinion of the walk.
        baseline_pred = predicted_support(p, o)
        pred = predicted_support(p, o, corrections)
        obs = observed_support(p, o, baseline_pred, terrain_road)
        responses.append(Response(
            response_id=f"r_{len(responses):04d}",
            persona_id=p.persona_id,
            support=round(obs),
            perceived_fairness=max(1, min(5, round(obs - 0.3 + 0.6 * rng.random()))),
            clarity_of_explanation=max(1, min(5, round(2.4 + 1.6 * p.baseline_trust
                                                       + 0.5 * rng.random()))),
            confidence_in_delivery=max(1, min(5, round(1.9 + 2.2 * p.baseline_trust
                                                       + 0.5 * rng.random()))),
            expected_personal_impact=_impact_score(o),
            # the gate is unchanged: it models who bothers to write, which is a separate
            # question from what they would say. Only the source of the text moved.
            comment=(words or {}).get(p.persona_id) if rng.random() < 0.35 else None,
            cohort={"age_band": p.age_band, "mobility_level": p.mobility_level,
                    "home_subzone": p.home_subzone, "is_caregiver": str(p.is_caregiver)},
        ))

    # Real submissions sit alongside the synthetic ones and are never merged into them.
    # They count toward the public confidence score, because that score describes the
    # people who replied and a person who replied is exactly that. They are excluded from
    # the prediction-versus-report rows, because a real respondent has no persona and
    # therefore no prediction -- averaging one in would compare a reported number against
    # a prediction that was never made.
    real = load_feedback("c1")
    responses.extend(real)

    calibration = _calibrate(responses, by_id, outcomes, corrections)
    blind = _blind_spots(pop, outcomes)

    def avg(field_: str) -> int:
        vals = [getattr(r, field_) for r in responses]
        return round(20 * sum(vals) / len(vals)) if vals else 0

    def avg_of(field_: str, rows: list[Response]) -> float | None:
        vals = [getattr(r, field_) for r in rows]
        return round(sum(vals) / len(vals), 2) if vals else None

    components = {
        "support": avg("support"),
        "perceived_fairness": avg("perceived_fairness"),
        "clarity_of_explanation": avg("clarity_of_explanation"),
        "confidence_in_delivery": avg("confidence_in_delivery"),
    }
    return ConsultationResult(
        responses=responses, calibration=calibration, blind_spots=blind,
        pcs_components=components,
        pcs=round(sum(components.values()) / len(components)),
    )


def _cohort_matches(persona_cohort: dict, reported: dict) -> bool:
    """Does a synthetic respondent look like this real one?

    Every axis the real respondent reported has to agree. An unreported axis is not a
    constraint -- a person who left age blank is compared against everyone, which widens
    the comparison rather than inventing an answer for them.
    """
    if not reported:
        return False
    for axis, value in reported.items():
        if value in (None, "", "unknown"):
            continue
        if str(persona_cohort.get(axis)) != str(value):
            return False
    return True


def _calibrate(responses, by_id, outcomes, corrections=None) -> list[CalibrationRow]:
    """Predicted against observed, both averaged over **the same respondents**.

    Averaging the prediction over the whole population and the observation over the people
    who replied measures who turned up, not how wrong the model is. That mistake makes
    every cohort look badly calibrated and hides the one that actually is.
    """
    rows: list[CalibrationRow] = []

    def predict_for(r: Response) -> float | None:
        """What the model would have predicted for this respondent.

        A seeded respondent is a persona, so the prediction is theirs directly. A real
        respondent is not: nobody filling in a form is one of the two thousand synthetic
        residents, and they have no computed outcome to predict from.

        They are not therefore unusable. They report a cohort, and the model does have a
        prediction for people in that cohort -- so the comparison becomes "what would we
        have predicted for someone like you, and what did you actually say". That is a
        weaker claim than the per-persona version and it is the honest one available, and
        it is the difference between real feedback driving the learning loop and sitting
        beside it doing nothing.

        Returns None when their cohort matches nobody, in which case they count toward
        the confidence score and not toward calibration.
        """
        if r.is_seeded:
            return predicted_support(by_id[r.persona_id], outcomes[r.persona_id],
                                     corrections)
        matches = [
            predicted_support(by_id[s.persona_id], outcomes[s.persona_id], corrections)
            for s in responses
            if s.is_seeded and _cohort_matches(s.cohort, r.cohort)
        ]
        return sum(matches) / len(matches) if matches else None

    def row(axis: str, value: str, members: list[Response]) -> CalibrationRow:
        priced = [(r, predict_for(r)) for r in members]
        usable = [(r, pr) for r, pr in priced if pr is not None]
        if not usable:
            return CalibrationRow(cohort_axis=axis, cohort_value=value,
                                  predicted_support=0.0, observed_support=0.0,
                                  signed_error=0.0, n=0, flagged=False)
        pred = sum(pr for _, pr in usable) / len(usable)
        obs = sum(r.support for r, _ in usable) / len(usable)
        members = [r for r, _ in usable]
        # on the 1-5 scale, one point is 25 percentage points of the usable range
        err = (obs - pred) * 25.0
        return CalibrationRow(
            cohort_axis=axis, cohort_value=value,
            predicted_support=round(pred, 2), observed_support=round(obs, 2),
            signed_error=round(err, 2), n=len(members),
            flagged=abs(err) > FLAG_ERROR_PP and len(members) >= FLAG_MIN_N,
        )

    # The overall row gets the same guard as the per-axis ones. It is appended first and
    # was therefore exempt from the emptiness check applied below -- which is only ever
    # visible when nobody is comparable at all, and is exactly the state a run reaches
    # when the only responses are real ones with no cohort to match against.
    overall = row("overall", "all respondents", responses)
    if overall.n:
        rows.append(overall)
    for axis in ("home_subzone", "age_band", "mobility_level", "is_caregiver"):
        buckets: dict[str, list[Response]] = {}
        for r in responses:
            # `.get`, not `[...]`. Every synthetic response carries all four axes because
            # they are read off a persona; a real submission carries only what the person
            # chose to tell us, and the form does not ask at all -- so this indexed into
            # an empty dict and took the whole run down with a KeyError the moment
            # somebody actually used the page.
            #
            # A respondent who did not report an axis is not "unknown" in that axis by
            # accident: they declined to say, and grouping them under a single "unknown"
            # bucket is the honest reading rather than dropping them.
            value = r.cohort.get(axis) if r.cohort else None
            buckets.setdefault(value or "not stated", []).append(r)
        for value, members in sorted(buckets.items()):
            r = row(axis, value, members)
            # A row with no usable respondents is not a finding, it is an empty bucket.
            # Respondents who reported no cohort at all land here: they still count in the
            # public confidence score, which describes who replied, but there is nobody to
            # compare a prediction against, so the row would render as 0.00 vs 0.00.
            if r.n:
                rows.append(r)
    return rows


def _blind_spots(pop: Population, outcomes: dict[str, Outcome]) -> list[BlindSpot]:
    """W12, K5: harm the consultation is least likely to hear about.

        blind_spot = harmed x (1 - expected response rate)

    Reported as cohorts with counts, and only as an estimate over a synthetic population.
    The point is operational: it names who to go and reach before deciding anything.
    """
    spots: list[BlindSpot] = []
    for axis, key in (("age_band", lambda p: p.age_band),
                      ("mobility_level", lambda p: p.mobility_level)):
        buckets: dict[str, list[Persona]] = {}
        for p in pop.personas:
            buckets.setdefault(key(p), []).append(p)
        for value, members in buckets.items():
            harmed = [p for p in members
                      if outcomes[p.persona_id].severity in ("high", "moderate")]
            if not harmed:
                continue
            expected = sum(response_probability(p, outcomes[p.persona_id]) for p in harmed)
            spots.append(BlindSpot(
                cohort_axis=axis, cohort_value=value, harmed=len(harmed),
                expected_responses=round(expected),
                score=round(len(harmed) - expected, 1),
            ))
    return sorted(spots, key=lambda s: -s.score)[:5]


# ------------------------------------------------------- the discovered constraint
"""What the flagged cohort is actually saying, read off their own words.

This was fixed prose in `engine.py`: *"The covered walkway ends partway and there is a
slope."* The **effect** is real and modelled -- `observed_support` applies a terrain
penalty scaled by how far someone walks -- but that sentence is a story about its cause,
and it was printed for whichever road the policy happened to touch. Run Bedok and it
claimed a covered walkway nobody had modelled.

Two honest cautions about what this does and does not prove:

  - On the seeded population the cause is **planted**. The terrain penalty is ours, and
    one of the canned comments names a slope outright, so a model reading those comments
    is partly reading back a sentence we wrote. The *mechanism* is real; the discovery on
    demo data is a fixture exercising it.
  - Alongside those sit real submissions, which are not canned. Summarising the whole
    cohort's text is genuine work on genuine input, and it is the only version of this
    that survives contact with a town nobody scripted.

So it is generated from the comments, cached per town, and labelled as a hypothesis
drawn from free text rather than as a finding.
"""

CONSTRAINTS = pathlib.Path(__file__).resolve().parents[2] / "data" / "runs"


def constraint_path(town: str) -> pathlib.Path:
    return CONSTRAINTS / f"constraint-{town}.json"


CONSTRAINT_SYSTEM = """You read consultation free-text from one group of residents and say
what they appear to be telling the planner that the planner's model did not know.

You are given only their comments. Do not invent a cause that nothing in the text
supports, and do not restate the numbers: the gap is already measured, the question is
what explains it.

- `note`: two sentences. What these residents describe, and what a model costing only
  distance would have missed about it.
- `affects`: which model quantities this would change, from: walk_distance_m,
  inconvenience_tolerance, journey_time_min, transfer_tolerance.
- `type`: a short slug for the kind of thing it is, such as walk_quality, service_gap,
  information, affordability.
- `confidence`: "clear" when several residents describe the same thing, "tentative" when
  it rests on one or two comments, "insufficient" when the text does not support any
  conclusion -- in which case say so in `note` rather than guessing.

Respond with a single JSON object matching the DiscoveredConstraint schema."""


def discover_constraint(town: str, cohort_value: str, comments: list[str], llm=None) -> dict:
    """Load the cached reading for this town, or generate one from the comments.

    Cached because it is a property of a finished run, not of a request, and because a
    demo must not depend on a model being reachable. A cache miss with no model returns
    the honest empty answer rather than a plausible sentence.
    """
    from pydantic import BaseModel, Field

    path = constraint_path(town)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            path.unlink(missing_ok=True)

    if llm is None or not comments:
        return {"type": "unknown", "location": cohort_value, "affects": [],
                "confidence": "insufficient", "source": "not generated",
                "note": "No reading has been generated for this cohort. The gap is "
                        "measured; its cause is not claimed."}

    class DiscoveredConstraint(BaseModel):
        note: str = Field(max_length=400)
        affects: list[str] = Field(default_factory=list)
        type: str = "walk_quality"
        confidence: str = "tentative"

    listing = "\n".join(f"- {c}" for c in comments[:40])
    result = llm.structured(
        DiscoveredConstraint, CONSTRAINT_SYSTEM,
        f"Residents in {cohort_value} wrote:\n\n{listing}", max_tokens=800)
    payload = {
        "type": result.type,
        "location": cohort_value,
        "affects": result.affects,
        "note": result.note,
        "confidence": result.confidence,
        "source": "consultation free text, read by a model",
        "model": getattr(llm, "provider_name", "unknown"),
        "n_comments": len(comments),
    }
    CONSTRAINTS.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return payload
