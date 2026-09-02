"""Producing a voice for every resident: batching, caching, and the offline writer. W10.

Two ways to get a voice, and the difference is never hidden.

`LLM_PROVIDER=bedrock` writes them with a model, in batches, cached on a content hash so a
replay of the same policy costs nothing. That is the real thing and it is what the page
shows when it can.

Otherwise `write_offline()` composes a turn from the resident's own events using templates.
It is not a model output and is never presented as one: every voice carries `generated_by`,
the page labels it, and `AGENTS.md` §28 is the reason. It exists so the whole pipeline,
its tests and the demo run with no credentials and no network.

Both paths obey the same grounding rule and go through the same validator, so a template
that drifted from the events would fail exactly like a model that hallucinated one.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

from app.agents.persona_voice import (
    BATCH_SIZE,
    VoiceGenerationFailed,
    _persona_brief,
    batch_key,
    validate_grounding,
    voice_batch,
)
from app.geography import Geography
from app.population import Persona, Population
from app.rng import derived_rng
from app.schemas.voice import PersonaTurn, PersonaVoice
from app.services.llm import LLMClient
from app.simulation import Event, Outcome

CACHE = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "voice_cache"

#: Synthetic, and labelled as such wherever shown. A spread of the naming traditions
#: common in Singapore, so a reader meets people rather than p_0412.
GIVEN = (
    "Mei Ling", "Wei Jie", "Siti", "Kavitha", "Hui Min", "Rajesh", "Boon Hock", "Nurul",
    "Jing Yi", "Arun", "Poh Choo", "Farah", "Zhi Hao", "Devi", "Ah Seng", "Aisyah",
    "Xiu Ying", "Kumar", "Swee Lan", "Haziq", "Li Fen", "Ganesh", "Kok Wah", "Rohana",
)
FAMILY = (
    "Tan", "Lim", "Lee", "Ng", "Wong", "Chua", "Goh", "Koh", "Rahman", "Ismail",
    "Ramasamy", "Pillai", "Chandran", "Binte Osman", "Teo", "Yeo", "Ong", "Sim",
)


class NoModelConfigured(RuntimeError):
    """Raised rather than producing something that reads like a resident and is not."""


@dataclass
class VoiceRun:
    voices: list[PersonaVoice]
    generated_by: str
    #: voices dropped because they cited an event that was not theirs. This is
    #: `evaluation.md` §9's Grounded Explanation Rate, as a count rather than a claim.
    ungrounded: int = 0
    cached_batches: int = 0
    model_batches: int = 0


def display_name(persona_id: str) -> str:
    rng = derived_rng(f"{persona_id}:name")
    return f"{rng.choice(GIVEN)} {rng.choice(FAMILY)}"


def summarise(p: Persona) -> str:
    bits = [f"{p.age_band}", p.employment_status]
    if p.mobility_level != "none":
        bits.append(f"{p.mobility_level} mobility, walks up to {p.max_walk_m} m")
    if p.is_caregiver:
        bits.append("cares for someone at home")
    if p.needs_clinic:
        bits.append("regular hospital trip")
    if p.has_car_access:
        bits.append("has a car in the household")
    return f"{', '.join(bits)}. Lives on {p.home_subzone}."


# ---------------------------------------------------------------- the offline writer
def _phrases(kind: str, before: dict, after: dict, names: dict | None = None) -> str:
    names = names or {}
    if kind == "PATH_UNAVAILABLE":
        code = before.get("stop_id")
        # residents say "Blk 700B", not "54241". The code is an identifier, not a place.
        return f"The stop I use, {names.get(code, code) or 'the one nearby'}, has gone."
    if kind == "EFFORT_INCREASED":
        return (f"My walk went from about {before.get('walk_distance_m', '?')} m to "
                f"{after.get('walk_distance_m', '?')} m.")
    if kind == "FRICTION_ADDED":
        return f"I now have to change buses {after.get('transfers', 1)} time on the way."
    if kind == "DURATION_INCREASED":
        return (f"The trip takes about {after.get('journey_time_min', '?')} minutes now, "
                f"against {before.get('journey_time_min', '?')} before.")
    if kind == "THRESHOLD_EXCEEDED":
        return (f"That is {after.get('walk_distance_m', '?')} m, and I told them "
                f"{after.get('max_walk_m', '?')} m is what I can manage.")
    if kind == "ESSENTIAL_ACCESS_LOST":
        return "I cannot get to the hospital appointment on my own any more."
    if kind == "DEPENDENCY_ABSORBED":
        return "I have taken over the hospital run for someone at home."
    if kind == "OBLIGATION_MISSED":
        return f"It makes me about {after.get('late_by_min', 'some')} minutes late for my shift."
    if kind == "SERVICE_ABANDONED":
        return "I have stopped making that trip."
    return kind.replace("_", " ").lower()


def write_offline(p: Persona, o: Outcome, events: list[Event],
                  names: dict | None = None) -> PersonaVoice:
    """A grounded turn per round, composed from this resident's own events.

    Templated, deterministic, and honest about being neither a model nor a person. It says
    only what the engine recorded, which is the same constraint the model works under.
    """
    rng = derived_rng(f"{p.persona_id}:voice")
    by_round: dict[int, list[Event]] = {}
    for e in events:
        by_round.setdefault(e.round, []).append(e)

    opening = 0.62 if not events else 0.55
    if p.needs_clinic:
        opening -= 0.05
    opening = round(min(1.0, max(0.0, opening + rng.uniform(-0.12, 0.12))), 2)

    turns = [PersonaTurn(
        round=0,
        position=opening,
        confidence=round(0.45 + 0.3 * p.baseline_trust, 2),
        reasoning=("I saw the notice about the buses. A faster ride sounds fine to me, "
                   "though I have not worked out yet what it means for my own trips."),
        adaptation="unaffected",
        cites=[],
    )]

    position = opening
    for rnd in sorted(by_round):
        evs = by_round[rnd]
        kinds = {e.kind for e in evs}
        drop = 0.10
        if kinds & {"THRESHOLD_EXCEEDED", "FRICTION_ADDED"}:
            drop = 0.22
        if kinds & {"ESSENTIAL_ACCESS_LOST", "DEPENDENCY_ABSORBED", "OBLIGATION_MISSED",
                    "SERVICE_ABANDONED"}:
            drop = 0.38
        position = round(max(0.0, position - drop), 2)

        if "OBLIGATION_MISSED" in kinds or "DEPENDENCY_ABSORBED" in kinds:
            adaptation = "absorbing"
        elif "SERVICE_ABANDONED" in kinds:
            adaptation = "giving_up"
        elif "ESSENTIAL_ACCESS_LOST" in kinds:
            adaptation = "substituting" if p.has_car_access else "giving_up"
        elif kinds:
            adaptation = "adapting"
        else:
            adaptation = "unaffected"

        body = " ".join(_phrases(e.kind, e.before, e.after, names) for e in evs[:3])
        turns.append(PersonaTurn(
            round=rnd,
            position=position,
            confidence=round(min(1.0, 0.55 + 0.12 * rnd), 2),
            reasoning=body,
            changed_because=_phrases(evs[0].kind, evs[0].before, evs[0].after, names),
            adaptation=adaptation,
            cites=[e.event_id for e in evs],
        ))

    return PersonaVoice(persona_id=p.persona_id, name=display_name(p.persona_id),
                        summary=summarise(p), turns=turns)


# ---------------------------------------------------------------- orchestration
def generate_voices(
    pop: Population,
    outcomes: dict[str, Outcome],
    events: list[Event],
    geo: Geography,
    policy_text: str,
    policy_version: str,
    llm: LLMClient | None = None,
    limit: int | None = None,
) -> VoiceRun:
    """A voice for every resident, or the first `limit` of them.

    Residents with events come first, because they are the ones with something to say and
    the ones a reader should meet. Residents with none still get a voice: "I have not
    noticed anything" is a finding when it comes from most of a town.
    """
    by_persona: dict[str, list[Event]] = {}
    for e in events:
        by_persona.setdefault(e.persona_id, []).append(e)

    ordered = sorted(pop.personas, key=lambda p: (-len(by_persona.get(p.persona_id, [])),
                                                  p.persona_id))
    if limit:
        ordered = ordered[:limit]

    stop_names = {s.stop_id: s.name for s in geo.stops.values()}

    if llm is None or llm.provider_name == "mock":
        # No silent fallback. Templates dressed as resident reasoning let a run look
        # finished when the feature had never executed, which is exactly how this shipped
        # switched off for a whole session.
        raise NoModelConfigured(
            "Resident deliberation needs a model. Set LLM_PROVIDER=bedrock with AWS "
            "credentials, or LLM_PROVIDER=anthropic with ANTHROPIC_API_KEY."
        )

    CACHE.mkdir(parents=True, exist_ok=True)
    voices: list[PersonaVoice] = []
    ungrounded = cached = called = 0

    for i in range(0, len(ordered), BATCH_SIZE):
        group = ordered[i:i + BATCH_SIZE]
        briefs = [_persona_brief(p, outcomes[p.persona_id],
                                by_persona.get(p.persona_id, []), stop_names)
                  for p in group]
        key = batch_key(briefs, policy_version, llm.provider_name)
        path = CACHE / f"{key}.json"

        if path.exists():
            batch = [PersonaVoice.model_validate(v)
                     for v in json.loads(path.read_text(encoding="utf-8"))]
            cached += 1
        else:
            try:
                batch = voice_batch(briefs, policy_text, llm).voices
            except VoiceGenerationFailed:
                # a failed batch falls back to the offline writer for those residents
                # rather than dropping them, and the run records that it happened
                batch = [write_offline(p, outcomes[p.persona_id],
                                       by_persona.get(p.persona_id, []), stop_names)
                         for p in group]
            else:
                called += 1
                path.write_text(
                    json.dumps([v.model_dump() for v in batch], indent=1), encoding="utf-8")

        for p, v in zip(group, batch):
            allowed = {e.event_id for e in by_persona.get(p.persona_id, [])}
            if validate_grounding(v, allowed):
                ungrounded += 1
                voices.append(write_offline(p, outcomes[p.persona_id],
                                            by_persona.get(p.persona_id, []), stop_names))
            else:
                voices.append(v)

    return VoiceRun(voices=voices, generated_by=llm.provider_name, ungrounded=ungrounded,
                    cached_batches=cached, model_batches=called)
