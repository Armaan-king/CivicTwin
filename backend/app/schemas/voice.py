"""What a resident thinks, per round. W10, scenario-v1.md §6A.

The shape is adapted from PropSim's `Stance`, which is the good idea in that project:
a position, a confidence, first-person reasoning, and — the part most models forget —
**what changed their mind this round**. A trajectory, not a snapshot.

Two things here are ours and are the reason this is not a chat transcript.

`cites` is the guard. A resident may only reason about events the engine actually recorded
for them. If a persona mentions a stop closing that never touched them, that is a test
failure and not a quirk: the whole claim of this page is that these are consequences, not
opinions. `test_voice.py` enforces it.

`position` is support for the policy on 0-1, so a run produces a distribution that can be
compared against the deterministic support function in **L1**. The logistic stays as the
inspectable baseline; the two disagreeing is a finding about the model, which is what
calibration is for.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

#: How a resident is coping. Deliberately not a sentiment label: the useful question is
#: what they do next, because that is what a planner can act on.
Adaptation = Literal[
    "unaffected",        # nothing about their journey changed
    "absorbing",         # it got worse and they are carrying it
    "adapting",          # changing how or when they travel
    "substituting",      # paying for another way: taxi, car, a lift from family
    "giving_up",         # dropping the trip
]


class PersonaTurn(BaseModel):
    """One resident, one round."""

    round: int = Field(ge=0, le=3)
    #: support for the policy. 0 is strongly against, 1 strongly for.
    position: float = Field(ge=0.0, le=1.0)
    #: how settled they are. A resident who has not been affected yet is often confident
    #: and wrong, which is exactly the pattern a consultation picks up and mistakes for
    #: agreement.
    confidence: float = Field(ge=0.0, le=1.0)
    #: two to four sentences, first person, in their own register
    reasoning: str = Field(min_length=1, max_length=1200)
    #: what moved them since the previous round, or None in round 0 and when nothing did
    changed_because: str | None = None
    adaptation: Adaptation = "unaffected"
    #: event_ids from this persona's own trace. Empty means they were not affected this
    #: round, which is a legitimate state and not a licence to invent one.
    cites: list[str] = Field(default_factory=list)


class PersonaVoice(BaseModel):
    """A resident's whole trajectory through the policy."""

    persona_id: str
    #: a plausible name, so a reader meets a person rather than a row id. Synthetic, and
    #: labelled as such wherever it is shown (`AGENTS.md` §16).
    name: str
    #: one line placing them: age, household, how they travel
    summary: str
    turns: list[PersonaTurn] = Field(default_factory=list)

    @property
    def final(self) -> PersonaTurn | None:
        return self.turns[-1] if self.turns else None

    @property
    def moved(self) -> float:
        """How far their position travelled. The interesting residents are not the
        unhappiest, they are the ones who changed their mind."""
        if len(self.turns) < 2:
            return 0.0
        return self.turns[-1].position - self.turns[0].position


class VoiceBatch(BaseModel):
    """What one model call returns: several residents at once.

    Batching is PropSim's other good idea. One call per resident is 2,000 round trips of
    latency for text that is independent; a batch of twenty is a hundred calls and the
    same output. The batch is the unit the cache is keyed on.
    """
    voices: list[PersonaVoice]
