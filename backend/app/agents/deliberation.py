"""The deliberation agent. V2's engine.

Each resident is an agent that decides for itself what a policy does to it. There is no
rules engine underneath deciding first and asking the model to narrate; the agent's answer
*is* the outcome, and the metrics are counted from what the agents said.

Two prompts, because the two questions are different. Round 0 asks who this person is and
where they start. Rounds 1 to 3 ask what has changed — in the world, and in what the people
around them are saying — and let them move.

The safeguard is not determinism, it is grounding. An agent is handed a numbered list of
facts and may cite only those ids. `check_grounding()` rejects anything else, and the
rejection is counted rather than hidden, because a deliberation nobody can check is a
chat log.
"""
from __future__ import annotations

import hashlib
import json
import os

from app.population import Persona
from app.schemas.deliberation import AgentTurn, DeliberationBatch, OpeningBatch
from app.services.llm import (LLMClient, LLMOutputInvalid, exact_items,
                              require_citations)
from app.world import ResidentWorld

#: Residents per model call. `AGENTS.md` §8 requires batching -- residents per call, not a
#: call per resident -- and the right size is bounded from above by the context window,
#: because a round prompt carries each resident's facts, their last position and up to four
#: neighbours' views. Twelve of those overflowed an 8192-token window, and `num_predict`
#: draws from the same window, so every batch came back truncated and was rejected.
#: Six fits with room to generate on a local 8B; a hosted model with a wide context can
#: raise it and save calls.
BATCH_SIZE = int(os.getenv("DELIBERATION_BATCH_SIZE", "12"))

#: Bump when a prompt OR the output schema changes, so cached deliberations produced under
#: older rules are not replayed as if they had passed the current ones. v3: grounding is
#: scoped to the round, a citation must reach a policy fact to support a harm claim, and
#: identity is validated rather than overwritten. v4: harmed residents are asked
#: what would make the policy workable for them (J4). v5: the 0..1 support scale is
#: stated explicitly, after a local model read a field named `position` as a signed
#: -1..+1 scale and every turn was rejected for it.
PROMPT_VERSION = "v7"

OPENING_SYSTEM = """You are simulating residents of a Singapore housing estate reacting to a
transport policy. For each resident you are given numbered facts about their life and their
bus network. Speak as them.

Absolute rules:
- Use ONLY the numbered facts given for that resident. Every distance, stop name, service
  number, age and circumstance must come from their own list. Invent nothing: no illnesses,
  no jobs, no family members, no stops.
- `grounded_in` lists the fact ids you actually reasoned from. It must never be empty:
  every judgement rests on something you were told. Use the exact ids, like "p_0007:f3".
- `reasoning` is 2 to 4 sentences, first person, plain speech. No slogans, no policy
  language, no quotation marks around the whole thing.
- `name` is a plausible Singapore name fitting their age. It is synthetic and labelled as
  such, so make it ordinary rather than distinctive.
- `position` is a number from 0.0 to 1.0 and is NEVER negative. 0.0 is completely against,
  0.5 is neutral, 1.0 is completely in favour. Do not use a -1 to +1 scale. This is round 0:
  most people have only heard that buses will be faster and have not worked out what it
  means for them, so most sit near 0.5 to 0.7.
- `confidence` is how settled they are, not how strongly they feel. Also 0.0 to 1.0.
- `summary` is one short phrase describing this person. Do not put fact ids in it.
- `severity` is "none" at round 0 unless a fact already says otherwise.
- Vary the voices. These are different people.

Respond with a single JSON object matching the OpeningBatch schema. No prose, no fences."""

ROUND_SYSTEM = """You are simulating residents of a Singapore housing estate as a transport
policy takes effect. Each resident is given: their numbered facts, what they said last
round, and what the people they know are saying now.

They decide for themselves what this policy does to them. Nothing has been computed for
you: judge it.

Absolute rules:
- Use ONLY that resident's numbered facts. Every number must appear in their list. Invent
  nothing.
- `grounded_in` lists the fact ids you reasoned from this round, and is never empty. If
  you say this policy affected you at all, one of those ids must be a fact about the
  policy itself -- your age and your household were true before it existed and cannot on
  their own show that it did anything to you.
- If a neighbour moved them, name them in `influenced_by` and say so in `changed_because`.
  A resident whose own journey did not change can still move because of what they heard.
  Only cite a neighbour who is actually in the list you were given.
- `severity` is your judgement of how badly this lands on them:
    "high"     an essential trip they cannot make any more; a walk far past what they
               manage; a trip they have given up; or a journey they have taken on for
               someone else at real cost to themselves
    "moderate" a longer or harder journey they can still make
    "none"     nothing meaningful changed for them
- `response` is what they actually do about it.
- `absorbing_for` is the persona id of a household member whose journey they have taken on,
  when they have. Only someone named in their facts.
- `reasoning` is 2 to 4 sentences, first person. Say what changed and why it matters to
  them specifically.
- `position` is a number from 0.0 to 1.0 and is NEVER negative. 0.0 is completely against,
  0.5 is neutral, 1.0 is completely in favour. Do not use a -1 to +1 scale. `confidence` is
  also 0.0 to 1.0.
- Most people are not affected. Do not manufacture drama: "nothing has changed for me" is a
  legitimate and common answer.
- `persona_id` on every turn is the id of the resident that turn is for, copied exactly
  from the RESIDENT heading above their facts.
- `remedy`: if and only if this resident is harmed (severity "moderate" or "high"), answer
  one further question in their own words, one sentence: what would make this workable for
  you? Ask for what they need, not for a policy instrument -- "somewhere to sit while I
  wait" is a real answer. Leave it null for anyone who is not harmed.

Respond with a single JSON object matching the DeliberationBatch schema, with one turn per
resident in the order given. No prose, no fences."""


class DeliberationFailed(RuntimeError):
    def __init__(self, detail: str, raw: str | None = None):
        super().__init__(detail)
        self.detail = detail
        self.raw = raw


def _facts_block(world: ResidentWorld, rnd: int) -> str:
    return "\n".join(f"  [{f.id}] {f.text}" for f in world.upto(rnd))


def opening_prompt(people: list[tuple[Persona, ResidentWorld]], policy: str) -> str:
    blocks = []
    for p, w in people:
        blocks.append(f"RESIDENT {p.persona_id}\n{_facts_block(w, 0)}")
    return (
        f"THE POLICY BEING PROPOSED:\n{policy.strip()}\n\n"
        f"{len(people)} RESIDENTS:\n\n" + "\n\n".join(blocks) +
        f"\n\nReturn an OpeningBatch with exactly {len(people)} voices, one per resident, "
        f"in this order, each with a single round 0 turn."
    )


def round_prompt(
    people: list[tuple[Persona, ResidentWorld]],
    rnd: int,
    previous: dict[str, AgentTurn],
    neighbour_views: dict[str, list[tuple[str, AgentTurn]]],
    policy: str,
) -> str:
    blocks = []
    for p, w in people:
        prev = previous.get(p.persona_id)
        said = (f"  Last round you said: \"{prev.reasoning}\" "
                f"(support {prev.position:.2f})" if prev else "  This is your first view.")
        heard = neighbour_views.get(p.persona_id, [])
        if heard:
            lines = "\n".join(
                f"    {nid}: \"{t.reasoning}\" (support {t.position:.2f}, {t.response})"
                for nid, t in heard
            )
            heard_block = f"  People you know are saying:\n{lines}"
        else:
            heard_block = "  You have not heard from anyone about this."
        blocks.append(
            f"RESIDENT {p.persona_id}\n{_facts_block(w, rnd)}\n{said}\n{heard_block}"
        )
    return (
        f"THE POLICY:\n{policy.strip()}\n\nROUND {rnd}.\n\n"
        f"{len(people)} RESIDENTS:\n\n" + "\n\n".join(blocks) +
        f"\n\nReturn a DeliberationBatch with exactly {len(people)} turns and the matching "
        f"persona_ids, in this order, each with round = {rnd}."
    )


def cache_key(prompt: str, model: str) -> str:
    return hashlib.sha256(
        f"{PROMPT_VERSION}:{model}:{prompt}".encode()
    ).hexdigest()[:32]


def run_opening(prompt: str, llm: LLMClient, expected: int) -> OpeningBatch:
    """Round 0, with the batch checked for shape before anything downstream trusts it.

    A schema-valid answer is not necessarily an answer. `{"voices": []}` satisfies the
    model and says nothing, and it is the documented failure mode of both providers we
    use: DeepSeek's own docs warn the API "may occasionally return empty content", and an
    8B model asked for twelve residents without a grammar returns exactly that. Counting
    it as a result would silently shrink the population and report the survivors as if
    they were everyone.
    """
    try:
        batch = llm.structured(
            OpeningBatch, OPENING_SYSTEM, prompt, max_tokens=8000,
            schema_override=require_citations(
                exact_items(OpeningBatch, "voices", expected)))
    except LLMOutputInvalid as exc:
        raise DeliberationFailed("opening batch was not valid", exc.raw) from exc
    if len(batch.voices) != expected:
        raise DeliberationFailed(
            f"opening batch returned {len(batch.voices)} voices, expected {expected}")
    return batch


def run_round(prompt: str, llm: LLMClient, expected_ids: list[str]) -> DeliberationBatch:
    """A later round, checked for shape and for identity.

    The identity check replaces an assignment. This used to write the resident's id over
    whatever the model returned -- "never trust the model with identity" -- which is the
    right instinct and the wrong action: it cannot detect a batch returned in the wrong
    order, it relabels it. Twelve residents' reasoning silently attached to the wrong
    twelve people is worse than a rejected batch, because it still looks like evidence.
    """
    try:
        batch = llm.structured(
            DeliberationBatch, ROUND_SYSTEM, prompt, max_tokens=8000,
            schema_override=require_citations(
                exact_items(DeliberationBatch, "turns", len(expected_ids))))
    except LLMOutputInvalid as exc:
        raise DeliberationFailed("round batch was not valid", exc.raw) from exc
    if len(batch.turns) != len(expected_ids):
        raise DeliberationFailed(
            f"round batch returned {len(batch.turns)} turns, expected {len(expected_ids)}")
    if batch.persona_ids != expected_ids:
        raise DeliberationFailed(
            f"round batch named {batch.persona_ids or 'nobody'}, expected {expected_ids}")
    return batch


def check_grounding(
    turn: AgentTurn,
    world: ResidentWorld,
    rnd: int,
    heard_from: set[str],
) -> list[str]:
    """What this agent was not entitled to say.

    Returns problems rather than raising: one bad turn in a batch of twelve is dropped and
    counted, not thrown away with the other eleven. The count is the honesty number the
    evaluation reports.

    Scoped to the round on purpose. An earlier version checked against `world.ids()`, every
    fact the resident would *ever* be given, so a round-1 turn could cite a fact only
    revealed in round 3 and pass. The question is not whether a fact exists somewhere; it
    is whether this resident had been told it when it spoke.

    The second rule here is the one that makes a citation mean something. A fact id proves
    the agent was handed that fact, not that the fact supports the claim. A resident
    declaring harm while citing only their own age and household -- facts true before the
    policy existed -- has cited nothing capable of establishing that the policy did it. So
    a claim of harm must rest on at least one fact from the policy rounds.
    """
    problems: list[str] = []

    supplied = {f.id for f in world.upto(rnd)}
    for fid in turn.grounded_in:
        if fid not in supplied:
            problems.append(
                f"cites fact {fid}, which it was not given in round {rnd}")

    if not turn.grounded_in:
        problems.append("reached a conclusion while citing no fact at all")

    # facts that only became true because of the policy
    policy_facts = {f.id for f in world.upto(rnd) if f.round >= 1}
    claims_impact = turn.severity != "none" or turn.response != "unaffected"
    if claims_impact and policy_facts and not (set(turn.grounded_in) & policy_facts):
        problems.append(
            f"claims {turn.severity} severity / {turn.response} citing only facts that were "
            "already true before the policy")

    if turn.influenced_by:
        if turn.influenced_by == world.persona_id:
            problems.append("claims to have been influenced by itself")
        elif turn.influenced_by not in heard_from:
            problems.append(
                f"claims {turn.influenced_by} influenced it, but never heard from them "
                f"in round {rnd}")

    if turn.absorbing_for and turn.absorbing_for not in set(world.household):
        problems.append(
            f"claims to absorb for {turn.absorbing_for}, who is not in their household")

    return problems
