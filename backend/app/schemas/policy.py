"""Typed policy shapes. Mirrors frontend/src/types/simulation.ts."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ExpressSegment(BaseModel):
    from_stop: str
    to_stop: str


class Modifications(BaseModel):
    remove_stops: list[str] = Field(default_factory=list)
    add_express_segment: ExpressSegment | None = None
    frequency_delta_pct: int = 0


class Constraints(BaseModel):
    fleet_increase_allowed: bool = False
    operating_budget_delta_pct: int = 0


class ReadingStep(BaseModel):
    n: str
    claim: str
    why: str
    assumed: bool = False


class PolicyChange(BaseModel):
    """What the Policy Interpreter must produce. Anything else is rejected."""
    objective: str
    modifications: Modifications
    constraints: Constraints
    reading: list[ReadingStep] = Field(default_factory=list)


class StartRunRequest(BaseModel):
    policy_text: str = Field(min_length=10, max_length=4000)


class StartRunResponse(BaseModel):
    run_id: str
    policy: PolicyChange
