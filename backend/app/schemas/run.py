"""The typed target for the engine.

This is what W3, W4, W5, W6 and W7 must produce. It mirrors
frontend/src/types/simulation.ts field for field; if the two ever disagree, the frontend
breaks at runtime, so `backend/tests/test_contract.py` compares them on every run.

Implementers: build against these models, not against the fixture JSON. FastAPI validates
every response with them, so an engine that drifts from the contract fails loudly at the
route rather than quietly in the browser.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.core import HarmPattern, PatternDescription
from app.schemas.policy import PolicyChange

Severity = Literal["none", "moderate", "high"]
AgeBand = Literal["<18", "18-34", "35-54", "55-64", "65-74", "75+"]
Mobility = Literal["none", "mild", "moderate", "severe"]
IncomeBand = Literal["low", "mid", "high"]
Employment = Literal["employed", "unemployed", "retired", "student"]
AccessibilityStatus = Literal["ok", "degraded", "unreachable"]

#: Nine kinds, no more. scenario-v1.md H2. Adding one is a spec change, not a code change.
EventKind = Literal[
    "PATH_UNAVAILABLE", "EFFORT_INCREASED", "FRICTION_ADDED",
    "DURATION_INCREASED", "THRESHOLD_EXCEEDED",
    "ESSENTIAL_ACCESS_LOST", "DEPENDENCY_ABSORBED",
    "OBLIGATION_MISSED", "SERVICE_ABANDONED",
]

EdgeKind = Literal[
    "LIVES_IN", "MEMBER_OF", "USES", "WORKS_AT", "STUDIES_AT",
    "NEEDS", "CARES_FOR", "SERVES", "ROUTES_TO",
]

InterventionKind = Literal[
    "retain_stop_peak", "add_shuttle_feeder", "reroute_feeder",
    "targeted_support", "phase_rollout",
]


class Persona(BaseModel):
    """Seventeen fields, every one read by a named rule. scenario-v1.md C1."""
    persona_id: str
    age_band: AgeBand
    home_subzone: str
    household_id: str
    household_role: str
    income_band: IncomeBand
    employment_status: Employment

    mobility_level: Mobility
    max_walk_m: int
    transfer_tolerance: int
    work_start_time: str | None = None
    has_car_access: bool
    is_caregiver: bool

    inconvenience_tolerance: float = Field(ge=0, le=1)
    switching_propensity: float = Field(ge=0, le=1)
    baseline_trust: float = Field(ge=0, le=1)

    needs_clinic: bool
    xy: tuple[float, float]
    block_id: str | None = None


class PersonaOutcome(BaseModel):
    persona_id: str
    severity: Severity
    walk_distance_m: int
    journey_time_min: float
    essential_trips_completed: int
    essential_trips_total: int
    accessibility_status: AccessibilityStatus
    #: harmed through a CARES_FOR edge rather than directly. F3 clause 4.
    second_order: bool
    #: harmed by an alternative in a place the baseline never touched
    newly_exposed: bool = False


class SimEvent(BaseModel):
    event_id: str
    round: int = Field(ge=0, le=3)
    persona_id: str
    kind: EventKind
    before: dict
    after: dict
    #: upstream event_id. this is what makes the chain traversable, and what
    #: evaluation.md 9's Grounded Explanation Rate is computed from.
    cause: str | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: EdgeKind
    attrs: dict = Field(default_factory=dict)


class Metrics(BaseModel):
    """Six metrics, canonical. scenario-v1.md I1. n is never optional."""
    n: int
    avg_journey_time_delta: float
    severe_harm_count: int
    severe_harm_rate: float = Field(ge=0, le=1)
    essential_trip_completion: float | None = None
    walk_distance_p90: int


class SubgroupMetrics(BaseModel):
    """Four axes, reported independently. No cross-tabs in V1. I4."""
    age_band: dict[str, Metrics]
    mobility_level: dict[str, Metrics]
    home_subzone: dict[str, Metrics]
    is_caregiver: dict[str, Metrics]


class RunMetrics(BaseModel):
    overall: Metrics
    subgroup: SubgroupMetrics
    subgroup_disparity_pp: float
    operating_cost_index: float


class Intervention(BaseModel):
    intervention_id: str
    kind: InterventionKind
    name: str
    params: dict
    rationale: str
    valid: bool
    validation_errors: list[str] = Field(default_factory=list)
    estimated_cost_index: float
    #: MUST be None when valid is False. A rejected candidate was never simulated,
    #: so scoring it would be inventing a result. Enforced in test_contract.py.
    metrics: Metrics | None = None
    carers_harmed: int | None = None
    newly_harmed_elsewhere: int | None = None
    subgroup_disparity_pp: float | None = None


class FeedbackResponse(BaseModel):
    response_id: str
    persona_id: str
    support: int = Field(ge=1, le=5)
    perceived_fairness: int = Field(ge=1, le=5)
    clarity_of_explanation: int = Field(ge=1, le=5)
    confidence_in_delivery: int = Field(ge=1, le=5)
    expected_personal_impact: int = Field(ge=-2, le=2)
    comment: str | None = None
    cohort: dict[str, str | None] = Field(default_factory=dict)
    #: seeded rows are labelled and surfaced as such. AGENTS.md 22 and 28.
    is_seeded: bool


class CalibrationRow(BaseModel):
    cohort_axis: str
    cohort_value: str
    predicted_support: float
    observed_support: float
    signed_error: float
    n: int
    #: |error| > 10pp AND n >= 30. Both conditions. scenario-v1.md L2.
    flagged: bool


class DiscoveredConstraint(BaseModel):
    type: str
    location: str
    affects: list[str]
    source: str
    note: str


class ProposedAdjustment(BaseModel):
    parameter: str
    from_: float = Field(alias="from")
    to: float
    #: never "applied" without a human. scenario-v1.md L3.
    status: Literal["awaiting_human_approval", "applied", "rejected"]

    model_config = {"populate_by_name": True}


class PublicConfidence(BaseModel):
    score: int
    #: the score is never returned without these. scenario-v1.md K4.
    components: dict[str, int]


class BlindSpot(BaseModel):
    """K5, W12: harm the consultation is least likely to hear about.

    `harmed - expected_responses`, reported as cohorts with counts. An estimate over a
    synthetic population, and the UI says so. The point is operational: it names who to
    go and reach before deciding anything.
    """
    cohort_axis: str
    cohort_value: str
    harmed: int
    expected_responses: int
    score: float


class Consultation(BaseModel):
    responses: list[FeedbackResponse]
    response_count: int
    #: always False in V1, and shown in the UI. Never claim representativeness.
    is_representative: bool
    pcs: PublicConfidence
    calibration: list[CalibrationRow]
    blind_spots: list[BlindSpot] = Field(default_factory=list)
    discovered_constraint: DiscoveredConstraint
    proposed_adjustment: ProposedAdjustment


class Graph(BaseModel):
    edges: list[GraphEdge]


class SimulationRun(BaseModel):
    """The whole contract. Every route that returns a run returns exactly this."""
    run_id: str
    scenario_id: str
    #: which environment pack produced this run. V1 registers transport only, but the
    #: field is here so a reader never has to assume. app/environments/.
    environment: str = "transport"
    seed: int
    population_version: str
    policy_version: str
    rounds: int
    generated_by: str
    #: always True in V1. Surfaced in the UI, never hidden. AGENTS.md 16.
    is_synthetic: bool
    study_area: str
    policy: PolicyChange
    personas: list[Persona]
    graph: Graph
    #: the study area as the map draws it. display only; no rule consults it.
    geography: dict = Field(default_factory=dict)
    outcomes: list[PersonaOutcome]
    events: list[SimEvent]
    metrics: RunMetrics
    interventions: list[Intervention]
    consultation: Consultation
    #: the shapes of harm this run found, in terms that carry outside transport.
    #: shipped with the run so the UI never hardcodes a description. core.PATTERNS.
    harm_patterns: dict[str, PatternDescription]
