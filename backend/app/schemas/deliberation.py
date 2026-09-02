"""What an agent decides. V2, and it replaces the rules engine's outputs.

Under V1 a predicate in `simulation.py` decided severity from four conditions. Now the
resident decides, and this schema is the shape that decision has to take. The fields are
the same questions the predicate asked, because they were the right questions; what
changed is who answers them.

`grounded_in` is the guard and the reason this is evidence rather than chat. An agent is
handed a numbered list of world facts and may reason only from those. A conclusion citing
a fact it was not given is rejected and counted, never rendered.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

#: The four things V1's F3 predicate tested, kept as definitions rather than as an
#: algorithm. The agent judges itself against them.
Severity = Literal["none", "moderate", "high"]

#: What they actually do, which is what a planner can act on. Not a sentiment label.
Response = Literal[
    "unaffected",
    "absorbing",       # carrying it themselves
    "adapting",        # travelling differently: earlier, another stop, another route
    "substituting",    # paying another way: taxi, a lift, a car
    "delegating",      # somebody else makes the journey for them
    "giving_up",       # the trip stops happening
]


class AgentTurn(BaseModel):
    """One resident, one round of deliberation."""

    round: int = Field(ge=0, le=3)

    #: how this policy lands on them, judged against the same definitions V1 computed:
    #: an essential trip lost, a walk far past what they manage, a trip abandoned, or a
    #: journey taken on for somebody else.
    severity: Severity = "none"
    response: Response = "unaffected"

    #: support for the policy, 0 against to 1 for
    position: float = Field(ge=0.0, le=1.0)
    #: how settled they are. Someone not yet affected is often confident and wrong.
    confidence: float = Field(ge=0.0, le=1.0)

    #: two to four sentences, first person
    reasoning: str = Field(min_length=1, max_length=1400)
    #: what moved them since the last round: an event, or something a neighbour said
    changed_because: str | None = None
    #: the persona_id of a neighbour who moved them, when one did. This is what makes the
    #: run a deliberation rather than two thousand parallel monologues.
    influenced_by: str | None = None

    #: fact ids from the numbered list this agent was given. Empty is legitimate and means
    #: nothing happened to them; it is not a licence to invent something that did.
    grounded_in: list[str] = Field(default_factory=list)

    #: someone in their household whose journey they have taken on. The second-order
    #: finding, now claimed by the resident rather than derived by a rule.
    absorbing_for: str | None = None


class AgentVoice(BaseModel):
    """A resident's whole deliberation."""

    persona_id: str
    #: synthetic, and labelled as such wherever shown
    name: str
    summary: str
    turns: list[AgentTurn] = Field(default_factory=list)

    @property
    def final(self) -> AgentTurn | None:
        return self.turns[-1] if self.turns else None

    @property
    def moved(self) -> float:
        if len(self.turns) < 2:
            return 0.0
        return self.turns[-1].position - self.turns[0].position


class DeliberationBatch(BaseModel):
    """What one model call returns: several residents reasoning about the same round."""
    turns: list[AgentTurn] = Field(default_factory=list)
    #: parallel to `turns`, so a batch can be matched back to its residents
    persona_ids: list[str] = Field(default_factory=list)


class OpeningBatch(BaseModel):
    """Round 0: who these people are, and where they start."""
    voices: list[AgentVoice] = Field(default_factory=list)
