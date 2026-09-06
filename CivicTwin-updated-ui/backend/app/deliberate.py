"""The deliberation loop. This is what replaced the rules engine.

Four rounds. Round 0 asks every resident who they are and where they start. Round 1 is the
policy landing. Rounds 2 and 3 are the part that makes it a deliberation rather than a
survey: residents see what the people they know concluded, and move.

Who speaks in a later round is bounded rather than universal, and the rule is the honest
one: **you re-deliberate if something changed for you.** New facts about your own journey,
or a neighbour who moved. A resident with nothing new to react to has no reason to speak
again, and asking them anyway is a bill without an output.

Concurrency is bounded, every batch is cached on a content hash, and the run records what
it cost. `AGENTS.md` §8 requires all three.
"""
from __future__ import annotations

import json
import os
import pathlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import networkx as nx

from app.agents.deliberation import (
    BATCH_SIZE,
    DeliberationFailed,
    cache_key,
    check_grounding,
    opening_prompt,
    round_prompt,
    run_opening,
    run_round,
)
from app.population import Population
from app.schemas.deliberation import AgentTurn, AgentVoice
from app.services.llm import LLMClient
from app.social import build_social_graph, neighbours
from app.world import ResidentWorld

CACHE = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "deliberation_cache"

#: how many batches are in flight at once. Bounded so a run cannot become a stampede.
CONCURRENCY = 8

ROUNDS = (1, 2, 3)
#: how many neighbours a resident hears from in a round
HEARD = 4


class NoModelConfigured(RuntimeError):
    """Raised rather than producing something that reads like a resident and is not."""


@dataclass
class DeliberationRun:
    voices: dict[str, AgentVoice] = field(default_factory=dict)
    model: str = ""
    calls: int = 0
    cached: int = 0
    rejected: int = 0
    failed_batches: int = 0
    seconds: float = 0.0
    #: residents who spoke, per round
    participation: dict[int, int] = field(default_factory=dict)

    def ordered(self) -> list[AgentVoice]:
        """Most-moved first: the residents who changed their mind are the story."""
        return sorted(self.voices.values(), key=lambda v: (v.moved, -len(v.turns)))


def _cached_or_call(prompt: str, model: str, fn, run: DeliberationRun):
    """Content-hash cache. Written atomically, because eight threads share this directory.

    A plain write leaves the file readable while it is half-finished, so a second thread
    can find it, parse a truncated object and fail on a run that was working. Write to a
    temporary name and rename: on every platform we target that swap is atomic, so a
    reader sees either no file or a complete one.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{cache_key(prompt, model)}.json"
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            run.cached += 1
            return payload
        except json.JSONDecodeError:
            path.unlink(missing_ok=True)      # a corpse from an interrupted run

    result = fn(prompt)
    run.calls += 1
    tmp = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(result, indent=1), encoding="utf-8")
    tmp.replace(path)
    return result


def deliberate(
    pop: Population,
    world: dict[str, ResidentWorld],
    policy_text: str,
    llm: LLMClient,
    social: nx.Graph | None = None,
    limit: int | None = None,
    on_voice=None,
) -> DeliberationRun:
    """Run the whole deliberation. Raises if no model is configured.

    `on_voice` is called with each resident as they finish a round, so a stream can show
    the population reacting rather than waiting for all of it.
    """
    if llm is None or llm.provider_name == "mock":
        raise NoModelConfigured(
            "Deliberation needs a model. LLM_PROVIDER=bedrock with AWS credentials, "
            "or LLM_PROVIDER=anthropic with ANTHROPIC_API_KEY. There is no offline "
            "substitute: text that reads like a resident and is not one is worse than "
            "no output."
        )

    started = time.monotonic()
    run = DeliberationRun(model=llm.provider_name)
    social = social if social is not None else build_social_graph(pop)
    people = pop.personas[:limit] if limit else pop.personas
    index = {p.persona_id: p for p in people}

    # ---------------------------------------------------------------- round 0
    batches = [people[i:i + BATCH_SIZE] for i in range(0, len(people), BATCH_SIZE)]

    def opening(group):
        prompt = opening_prompt([(p, world[p.persona_id]) for p in group], policy_text)
        try:
            raw = _cached_or_call(prompt, run.model,
                                  lambda pr: run_opening(pr, llm).model_dump(), run)
        except DeliberationFailed:
            run.failed_batches += 1
            return []
        from app.schemas.deliberation import OpeningBatch
        return OpeningBatch.model_validate(raw).voices

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        for group, voices in zip(batches, pool.map(opening, batches)):
            for p, v in zip(group, voices):
                v.persona_id = p.persona_id          # never trust the model with identity
                w = world[p.persona_id]
                for t in v.turns:
                    if check_grounding(t, w.ids(), set(w.household)):
                        run.rejected += 1
                        t.grounded_in = []
                        t.severity = "none"
                run.voices[p.persona_id] = v
                if on_voice:
                    on_voice(v, 0)
    run.participation[0] = len(run.voices)

    # ---------------------------------------------------------------- rounds 1..3
    for rnd in ROUNDS:
        speakers = _participants(run, world, social, rnd, index)
        run.participation[rnd] = len(speakers)
        if not speakers:
            continue
        groups = [speakers[i:i + BATCH_SIZE] for i in range(0, len(speakers), BATCH_SIZE)]

        # Snapshot the round before dispatching any of it. Building prompts inside the
        # worker reads `run.voices` while earlier batches are already writing their turns
        # into it, so a batch that happens to run late shows a resident their neighbour's
        # *this-round* view. That collapses the round structure into a race, and it is
        # invisible except as a prompt that differs between two identical runs.
        prepared = []
        for group in groups:
            previous = {
                pid: run.voices[pid].turns[-1]
                for pid in group if run.voices.get(pid) and run.voices[pid].turns
            }
            heard = {pid: _heard(run, social, pid) for pid in group}
            prepared.append((group, heard, round_prompt(
                [(index[pid], world[pid]) for pid in group], rnd, previous, heard, policy_text
            )))

        def one_round(item, rnd=rnd):
            _group, _heard_map, prompt = item
            try:
                return _cached_or_call(prompt, run.model,
                                       lambda pr: run_round(pr, llm).model_dump(), run)
            except DeliberationFailed:
                run.failed_batches += 1
                return None

        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            for (group, heard, _), raw in zip(prepared, pool.map(one_round, prepared)):
                if raw is None:
                    continue
                from app.schemas.deliberation import DeliberationBatch
                batch = DeliberationBatch.model_validate(raw)
                for pid, turn in zip(group, batch.turns):
                    w = world[pid]
                    allowed_people = set(w.household) | {n for n, _ in heard.get(pid, [])}
                    if check_grounding(turn, w.ids(), allowed_people):
                        run.rejected += 1
                        continue
                    turn.round = rnd
                    run.voices[pid].turns.append(turn)
                    if on_voice:
                        on_voice(run.voices[pid], rnd)

    run.seconds = round(time.monotonic() - started, 1)
    return run


def _heard(run: DeliberationRun, social: nx.Graph, pid: str) -> list[tuple[str, AgentTurn]]:
    """What this resident's neighbours last concluded."""
    out = []
    for nid in neighbours(social, pid, limit=HEARD):
        v = run.voices.get(nid)
        if v and v.turns:
            out.append((nid, v.turns[-1]))
    return out


def _participants(
    run: DeliberationRun,
    world: dict[str, ResidentWorld],
    social: nx.Graph,
    rnd: int,
    index: dict,
) -> list[str]:
    """Who has something new to react to this round.

    Round 1 is everyone: the policy has just landed and nobody has considered it yet. After
    that, a resident speaks again if their own facts changed or if somebody they know moved.
    Asking a resident with nothing new to say produces a paraphrase and a bill.
    """
    if rnd == 1:
        return list(index)

    speakers: list[str] = []
    for pid in index:
        v = run.voices.get(pid)
        if not v or not v.turns:
            continue
        last = v.turns[-1]
        new_facts = any(f.round == rnd for f in world[pid].facts)
        moved_near = any(
            (nv := run.voices.get(nid)) and len(nv.turns) > 1
            and abs(nv.turns[-1].position - nv.turns[-2].position) > 0.08
            for nid in neighbours(social, pid, limit=HEARD)
        )
        # someone still working out what to do is not finished thinking
        unsettled = last.confidence < 0.55 or last.severity != "none"
        if new_facts or moved_near or unsettled:
            speakers.append(pid)
    return speakers
