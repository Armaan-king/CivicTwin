"""The domain-neutral core: what CivicTwin is about, before any one policy area.

The product is not a transport tool. It detects a mechanism that recurs wherever an
institution optimises an aggregate:

    a threshold, a dependency, and someone who absorbs a loss that was not theirs.

Change the nouns and it is clinic consolidation, benefits digitisation, catchment redraws,
appointment systems, tariff restructuring. The vocabulary here is stated in those general
terms; an environment pack supplies the words a particular domain uses for them.

Transport is the only environment implemented in V1 (`scenario-v1.md` A1). It is the proof,
not the product.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --------------------------------------------------------------- what can happen
#: Nine kinds, unchanged in number from the transport vocabulary they replace, because
#: each transport event was already an instance of one of these. See `EVENT_LABELS` in an
#: environment pack for the words a domain puts on them.
EventKind = Literal[
    "PATH_UNAVAILABLE",       # the way they reached the service is gone
    "EFFORT_INCREASED",       # reaching it costs more: distance, steps, forms, fare
    "FRICTION_ADDED",         # an extra handoff or transfer appeared
    "DURATION_INCREASED",     # it simply takes longer
    "THRESHOLD_EXCEEDED",     # past what this person said they can manage
    "ESSENTIAL_ACCESS_LOST",  # something they depend on became unreachable
    "DEPENDENCY_ABSORBED",    # someone else took the loss on for them
    "OBLIGATION_MISSED",      # a competing commitment failed as a result
    "SERVICE_ABANDONED",      # they stopped trying
]

#: The relationships that let harm travel. `DEPENDS_ON` and `CARES_FOR` are the two that
#: make second-order harm possible; the rest situate a person in a place and a routine.
EdgeKind = Literal[
    "LIVES_IN", "MEMBER_OF", "USES", "WORKS_AT", "STUDIES_AT",
    "NEEDS", "CARES_FOR", "DEPENDS_ON", "SERVES", "CONNECTS_TO",
]

Severity = Literal["none", "moderate", "high"]
AccessStatus = Literal["ok", "degraded", "unreachable"]


# --------------------------------------------------------------- how it goes wrong
#: Four shapes of harm that recur across policy areas. Naming them is what lets a finding
#: in transport be recognised by someone working on clinics or benefits.
HarmPattern = Literal[
    "threshold_cliff",
    "dependency_cascade",
    "capacity_displacement",
    "participation_gap",
]


class PatternDescription(BaseModel):
    """A pattern, in terms a policymaker outside this domain would recognise."""
    pattern: HarmPattern
    name: str
    mechanism: str
    #: other policy areas where the same shape appears, so the finding travels
    also_seen_in: list[str]


PATTERNS: dict[str, PatternDescription] = {
    "threshold_cliff": PatternDescription(
        pattern="threshold_cliff",
        name="Threshold cliff",
        mechanism=(
            "A limit is crossed and the service stops being usable, rather than simply "
            "getting worse. Averages miss this because the mean moves smoothly while "
            "individuals fall off an edge."
        ),
        also_seen_in=[
            "eligibility rule changes",
            "appointment and queue redesign",
            "fare and tariff restructuring",
        ],
    ),
    "dependency_cascade": PatternDescription(
        pattern="dependency_cascade",
        name="Dependency cascade",
        mechanism=(
            "Harm lands on someone the policy never touched, because they absorb the loss "
            "for a person who depends on them. They are invisible to any analysis that "
            "looks only at who uses the service."
        ),
        also_seen_in=[
            "clinic and school consolidation",
            "service digitisation",
            "opening-hours reductions",
        ],
    ),
    "capacity_displacement": PatternDescription(
        pattern="capacity_displacement",
        name="Capacity displacement",
        mechanism=(
            "Relief for one group creates load somewhere else. The total looks unchanged "
            "or improved while a different population quietly absorbs the difference."
        ),
        also_seen_in=[
            "catchment redraws",
            "facility closures and mergers",
            "route or caseload rebalancing",
        ],
    ),
    "participation_gap": PatternDescription(
        pattern="participation_gap",
        name="Participation gap",
        mechanism=(
            "The people most affected are the least able to respond to a consultation, so "
            "the feedback that arrives systematically understates the harm."
        ),
        also_seen_in=[
            "any public consultation",
            "user research and pilot recruitment",
            "complaint-driven service review",
        ],
    ),
}


# --------------------------------------------------------------- the neutral records
class NeutralOutcome(BaseModel):
    """What happened to one person, in terms any environment can express.

    An environment pack adds its own measured quantities alongside these; it never
    replaces them, because these are what the audit, the comparison and the calibration
    all read.
    """
    persona_id: str
    severity: Severity
    access_status: AccessStatus
    essential_needs_met: int
    essential_needs_total: int
    #: harmed through a dependency rather than directly. the finding the product exists for.
    second_order: bool
    #: harmed by an alternative, in a place the baseline never touched
    newly_exposed: bool = False


class NeutralEvent(BaseModel):
    event_id: str
    round: int = Field(ge=0, le=3)
    persona_id: str
    kind: EventKind
    before: dict
    after: dict
    #: upstream event_id; the chain is what makes a root cause provable
    cause: str | None = None


class Finding(BaseModel):
    """An audit result, tagged with the pattern it instantiates."""
    finding_id: str
    title: str
    severity: Severity
    n: int
    pattern: HarmPattern
    body: str
