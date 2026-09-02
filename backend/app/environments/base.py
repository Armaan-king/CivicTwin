"""The seam architecture.md 7 asked for, built now that breadth is the claim.

Not a plugin framework. A Protocol and a registry, so a second policy area is an added
module rather than an edit to the core. V1 registers exactly one environment.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.core import EventKind, HarmPattern


@runtime_checkable
class EnvironmentPack(Protocol):
    """What a policy area must supply to be simulable.

    The core owns severity, dependency, thresholds and the audit. A pack owns the nouns:
    what a person's constraints are, what counts as reaching a service, and what the
    domain calls each kind of event.
    """

    name: str
    #: display words for the neutral vocabulary, e.g. EFFORT_INCREASED -> "walk lengthened"
    event_labels: dict[str, str]
    #: which harm patterns this environment can produce at all
    patterns: tuple[HarmPattern, ...]

    def persona_fields(self) -> dict[str, type]:
        """Domain constraints carried on every persona, beyond the neutral record."""
        ...

    def apply_policy(self, state: dict, policy: dict) -> dict: ...

    def evaluate(self, persona: dict, state: dict) -> dict:
        """Deterministic outcome for one person. No model call. See AGENTS.md 10."""
        ...

    def metric_names(self) -> tuple[str, ...]:
        """The domain quantities reported alongside the neutral six."""
        ...


_REGISTRY: dict[str, EnvironmentPack] = {}


def register(pack: EnvironmentPack) -> EnvironmentPack:
    _REGISTRY[pack.name] = pack
    return pack


def get(name: str) -> EnvironmentPack:
    if name not in _REGISTRY:
        raise KeyError(
            f"No environment '{name}'. Registered: {sorted(_REGISTRY) or 'none'}. "
            "V1 implements transport only (scenario-v1.md A1)."
        )
    return _REGISTRY[name]


def registered() -> list[str]:
    return sorted(_REGISTRY)


def label(pack: EnvironmentPack, kind: EventKind) -> str:
    """The domain's word for a neutral event, falling back to the neutral one."""
    return pack.event_labels.get(kind, kind.replace("_", " ").lower())
