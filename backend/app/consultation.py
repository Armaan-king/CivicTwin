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

from dataclasses import dataclass, field

from app.population import Persona, Population
from app.rng import derived_rng
from app.simulation import Outcome

#: the subzone where the walk is worse than its distance suggests. The model does not know.
#: the real road name, as it appears in the LTA stop data. It was "AMK Ave 3"
#: while the estate was invented, so the penalty silently applied to nobody
#: once the cohorts became real roads.
TERRAIN_SUBZONE = "Ang Mo Kio Ave 3"
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


def _impact_score(o: Outcome) -> int:
    """How this person expects the policy to land on them, -2 to +2."""
    if o.severity == "high":
        return -2
    if o.severity == "moderate":
        return -1
    if o.journey_time_delta_min < -0.5:
        return 1
    return 0


def predicted_support(p: Persona, o: Outcome) -> float:
    """L1. An explicit function of three persona quantities and the computed outcome.

    Deliberately does not know about terrain. That omission is the thing calibration is
    supposed to find, and `baseline_trust` is therefore the parameter it tests.
    """
    base = 1.6 + 2.6 * p.baseline_trust
    base += 0.55 * _impact_score(o)
    base += 0.40 * p.inconvenience_tolerance
    return max(1.0, min(5.0, base))


def observed_support(p: Persona, o: Outcome, predicted: float) -> float:
    """What residents actually say. Prediction, plus what the model did not know."""
    rng = derived_rng(f"{p.persona_id}:support")
    value = predicted + rng.gauss(0, 0.45)
    if p.home_subzone == TERRAIN_SUBZONE:
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


COMMENTS = {
    "high": [
        "The walk to the next stop has a long uncovered stretch and a slope. In the rain "
        "with a walking stick it is not 400 metres, it is impossible.",
        "I take my mother to the polyclinic every Tuesday. Now I have to drive her and I "
        "am late for my shift.",
        "There was no consultation before the notice went up at the stop.",
    ],
    "moderate": [
        "It is a longer walk but manageable. The extra few minutes on the express make up "
        "for it on the way home.",
        "Fine for me, but I do not know how the older residents in my block will cope.",
    ],
    "none": [
        "The express is faster. I have not noticed any difference otherwise.",
        "Good use of money if it means the buses run more often.",
    ],
}


def build_consultation(pop: Population, outcomes: dict[str, Outcome]) -> ConsultationResult:
    by_id = pop.by_id()
    responses: list[Response] = []

    for p in pop.personas:
        o = outcomes[p.persona_id]
        rng = derived_rng(f"{p.persona_id}:respond")
        if rng.random() > response_probability(p, o):
            continue
        pred = predicted_support(p, o)
        obs = observed_support(p, o, pred)
        pool = COMMENTS[o.severity if o.severity in COMMENTS else "none"]
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
            comment=pool[rng.randrange(len(pool))] if rng.random() < 0.35 else None,
            cohort={"age_band": p.age_band, "mobility_level": p.mobility_level,
                    "home_subzone": p.home_subzone, "is_caregiver": str(p.is_caregiver)},
        ))

    calibration = _calibrate(responses, by_id, outcomes)
    blind = _blind_spots(pop, outcomes)

    def avg(field_: str) -> int:
        vals = [getattr(r, field_) for r in responses]
        return round(20 * sum(vals) / len(vals)) if vals else 0

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


def _calibrate(responses, by_id, outcomes) -> list[CalibrationRow]:
    """Predicted against observed, both averaged over **the same respondents**.

    Averaging the prediction over the whole population and the observation over the people
    who replied measures who turned up, not how wrong the model is. That mistake makes
    every cohort look badly calibrated and hides the one that actually is.
    """
    rows: list[CalibrationRow] = []

    def row(axis: str, value: str, members: list[Response]) -> CalibrationRow:
        pred = sum(predicted_support(by_id[r.persona_id], outcomes[r.persona_id])
                   for r in members) / len(members)
        obs = sum(r.support for r in members) / len(members)
        # on the 1-5 scale, one point is 25 percentage points of the usable range
        err = (obs - pred) * 25.0
        return CalibrationRow(
            cohort_axis=axis, cohort_value=value,
            predicted_support=round(pred, 2), observed_support=round(obs, 2),
            signed_error=round(err, 2), n=len(members),
            flagged=abs(err) > FLAG_ERROR_PP and len(members) >= FLAG_MIN_N,
        )

    rows.append(row("overall", "all respondents", responses))
    for axis in ("home_subzone", "age_band", "mobility_level", "is_caregiver"):
        buckets: dict[str, list[Response]] = {}
        for r in responses:
            buckets.setdefault(r.cohort[axis] or "unknown", []).append(r)
        for value, members in sorted(buckets.items()):
            rows.append(row(axis, value, members))
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
