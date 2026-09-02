"""Persona Voice: what each resident makes of the policy, round by round. W10.

The LLM earns its place here for the same reason it does in the interpreter — this is
language, not arithmetic. It computes nothing. Every number it is allowed to mention has
already been computed by the engine and is handed to it in the prompt.

**The grounding rule.** A resident may only reason about events the engine recorded for
them. That is enforced three ways: the prompt carries their trace and nothing else, the
schema requires `cites` to name event ids, and `validate_grounding()` rejects a turn that
cites an event belonging to somebody else. A page of two thousand residents saying
plausible things is worthless if any of it is invented; the whole claim is that these are
consequences.

**Cost.** One batched call per group of residents, plus a re-run only for residents whose
state actually changed in a later round (`scenario-v1.md` §6A). At batch size 20 that is
around 100 calls for a 2,000-resident run rather than 8,000, and every batch is cached on
a content hash so a replay costs nothing at all.
"""
from __future__ import annotations

import hashlib
import json

from app.population import Persona
from app.schemas.voice import PersonaVoice, VoiceBatch
from app.services.llm import LLMClient, LLMOutputInvalid
from app.simulation import Event, Outcome

#: residents per model call. Twenty fits comfortably in one response and cuts a
#: 2,000-resident run from thousands of round trips to about a hundred.
BATCH_SIZE = 20

#: bump when the prompt changes, so cached voices from an older prompt are not reused
PROMPT_VERSION = "v1"

SYSTEM = """You write what residents of a town make of a transport policy that affects them.

You are given, for each resident: their record, what the simulation computed happened to
them, and the exact events it recorded. Write their view in their own voice.

Rules, all of them absolute:
- Use ONLY facts from that resident's record and their listed events. Every number you
  mention must appear there. Do not invent a stop, a distance, a time, an illness, a job,
  or a family member.
- `cites` must list the event_ids you actually reasoned from. If they have no events,
  cite nothing and write someone who has not noticed a change.
- Write 2 to 4 sentences, first person, plain speech. No slogans, no policy language, no
  quotation marks around the whole thing.
- `position` is their support for the policy from 0 to 1. Someone unaffected who likes a
  faster bus is high. Someone who lost a trip they depend on is low.
- `confidence` is how settled they are, not how strongly they feel. A resident who has not
  been affected yet is often confident and wrong.
- `changed_because` names what moved them since the previous round, in a few words, or is
  null if nothing did.
- Vary the voices. These are different people, not one person with different numbers.

Respond with a single JSON object matching the VoiceBatch schema. No prose, no fences."""


def _persona_brief(p: Persona, o: Outcome, events: list[Event], stop_names: dict) -> dict:
    """Everything the model is allowed to know about one resident."""
    return {
        "persona_id": p.persona_id,
        "age_band": p.age_band,
        "household": f"{p.household_role} in a household of the same road",
        "lives_on": p.home_subzone,
        "employment": p.employment_status,
        "works_from": p.work_start_time,
        "mobility": p.mobility_level,
        "will_walk_m": p.max_walk_m,
        "has_car": p.has_car_access,
        "is_caregiver": p.is_caregiver,
        "depends_on_hospital_trip": p.needs_clinic,
        "outcome": {
            "severity": o.severity,
            "walk_before_m": o.baseline_walk_m,
            "walk_after_m": o.walk_distance_m,
            "journey_change_min": o.journey_time_delta_min,
            "essential_trips_kept": f"{o.essential_trips_completed} of {o.essential_trips_total}",
            "access": o.accessibility_status,
            "harmed_through_someone_else": o.second_order,
        },
        "events": [
            {"event_id": e.event_id, "round": e.round, "what": e.kind,
             "before": _readable(e.before, stop_names), "after": _readable(e.after, stop_names)}
            for e in events
        ],
    }


def _readable(d: dict, stop_names: dict) -> dict:
    """Swap stop codes for the names residents would actually use."""
    return {k: (stop_names.get(v, v) if k == "stop_id" else v) for k, v in d.items()}


def batch_key(briefs: list[dict], policy_version: str, model_id: str) -> str:
    """Content hash. Same residents, same events, same prompt -> same voices, free."""
    payload = json.dumps(briefs, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(
        f"{PROMPT_VERSION}:{policy_version}:{model_id}:{payload}".encode()
    ).hexdigest()[:32]


def voice_batch(briefs: list[dict], policy_text: str, llm: LLMClient) -> VoiceBatch:
    """One model call for a group of residents. Raises rather than inventing."""
    prompt = (
        f"THE POLICY:\n{policy_text.strip()}\n\n"
        f"RESIDENTS ({len(briefs)}), with what the simulation computed for each:\n"
        f"{json.dumps(briefs, indent=1)}\n\n"
        f"Return a VoiceBatch with exactly {len(briefs)} voices, one per resident, "
        f"in the same order, each with one turn per round that resident has events for "
        f"plus a round 0 opening view."
    )
    try:
        return llm.structured(VoiceBatch, SYSTEM, prompt, max_tokens=400 * len(briefs) + 600)
    except LLMOutputInvalid as exc:
        raise VoiceGenerationFailed(
            f"The model did not return a valid VoiceBatch for {len(briefs)} residents.",
            exc.raw,
        ) from exc


class VoiceGenerationFailed(RuntimeError):
    def __init__(self, detail: str, raw: str | None = None):
        super().__init__(detail)
        self.detail = detail
        self.raw = raw


def validate_grounding(voice: PersonaVoice, allowed_event_ids: set[str]) -> list[str]:
    """Every citation must be one of this resident's own events.

    Returns the problems rather than raising, because one ungrounded voice in a batch of
    twenty should be dropped and counted, not throw the batch away. The count is an
    evaluation number in its own right: `evaluation.md` §9's Grounded Explanation Rate.
    """
    problems: list[str] = []
    for turn in voice.turns:
        for eid in turn.cites:
            if eid not in allowed_event_ids:
                problems.append(
                    f"{voice.persona_id} round {turn.round} cites {eid}, "
                    f"which is not one of their events"
                )
    return problems
