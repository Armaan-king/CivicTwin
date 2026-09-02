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

from app.population import Persona
from app.schemas.deliberation import AgentTurn, DeliberationBatch, OpeningBatch
from app.services.llm import LLMClient, LLMOutputInvalid
from app.world import ResidentWorld

#: residents per model call
BATCH_SIZE = 12

#: bump when a prompt changes, so cached deliberations from an older prompt are not reused
PROMPT_VERSION = "v2"

OPENING_SYSTEM = """You are simulating residents of a Singapore housing estate reacting to a
transport policy. For each resident you are given numbered facts about their life and their
bus network. Speak as them.

Absolute rules:
- Use ONLY the numbered facts given for that resident. Every distance, stop name, service
  number, age and circumstance must come from their own list. Invent nothing: no illnesses,
  no jobs, no family members, no stops.
- `grounded_in` lists the fact ids you actually reasoned from.
- `reasoning` is 2 to 4 sentences, first person, plain speech. No slogans, no policy
  language, no quotation marks around the whole thing.
- `name` is a plausible Singapore name fitting their age. It is synthetic and labelled as
  such, so make it ordinary rather than distinctive.
- `position` is support for the policy, 0 against to 1 for. This is round 0: most people
  have only heard that buses will be faster and have not worked out what it means for them.
- `confidence` is how settled they are, not how strongly they feel.
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
- `grounded_in` lists the fact ids you reasoned from this round.
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
- Most people are not affected. Do not manufacture drama: "nothing has changed for me" is a
  legitimate and common answer.

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


def run_opening(prompt: str, llm: LLMClient) -> OpeningBatch:
    try:
        return llm.structured(OpeningBatch, OPENING_SYSTEM, prompt, max_tokens=8000)
    except LLMOutputInvalid as exc:
        raise DeliberationFailed("opening batch was not valid", exc.raw) from exc


def run_round(prompt: str, llm: LLMClient) -> DeliberationBatch:
    try:
        return llm.structured(DeliberationBatch, ROUND_SYSTEM, prompt, max_tokens=8000)
    except LLMOutputInvalid as exc:
        raise DeliberationFailed("round batch was not valid", exc.raw) from exc


def check_grounding(
    turn: AgentTurn, allowed_facts: set[str], allowed_neighbours: set[str]
) -> list[str]:
    """What this agent was not entitled to say.

    Returns problems rather than raising: one bad turn in a batch of twelve is dropped and
    counted, not thrown away with the other eleven. The count is the honesty number the
    evaluation reports.
    """
    problems: list[str] = []
    for fid in turn.grounded_in:
        if fid not in allowed_facts:
            problems.append(f"cites fact {fid}, which it was not given")
    if turn.influenced_by and turn.influenced_by not in allowed_neighbours:
        problems.append(f"claims {turn.influenced_by} influenced it, but never heard from them")
    if turn.absorbing_for and turn.absorbing_for not in allowed_neighbours:
        problems.append(f"claims to absorb for {turn.absorbing_for}, who is not in their household")
    if turn.severity != "none" and not turn.grounded_in:
        problems.append("claims harm while citing no fact at all")
    return problems
