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

from app.config import env_int
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
    check_continuity,
    check_grounding,
    normalise_citations,
    opening_prompt,
    round_prompt,
    run_opening,
    run_round,
)
from app.cohort import select_cohort
from app.population import Population
from app.schemas.deliberation import AgentTurn, AgentVoice
from app.services.llm import LLMClient
from app.social import build_social_graph, neighbours
from app.world import ResidentWorld

CACHE = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "deliberation_cache"

#: How many batches are in flight at once. Bounded so a run cannot become a stampede
#: (`AGENTS.md` §8). The right ceiling depends on what is behind the client: a hosted
#: API wants several, one local GPU wants one, and eight against Ollama merely builds a
#: queue while making the failure modes concurrent.
CONCURRENCY = env_int("DELIBERATION_CONCURRENCY", 8)

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

    # ---------------------------------------------------------------- coverage
    #: everyone in the study area, whether or not they were asked
    population: int = 0
    #: who this run selected to reason. The rest are unknown, not unaffected.
    cohort: list[str] = field(default_factory=list)
    #: how the cohort was chosen, for the screen that has to state it
    cohort_strata: dict[str, int] = field(default_factory=dict)
    #: residents whose every turn was rejected, so nothing they said can be counted
    ungrounded: list[str] = field(default_factory=list)
    #: turns that changed course without saying why. Kept and counted: a resident who
    #: cannot articulate what moved them has still declared what happened to them.
    unexplained_moves: int = 0

    def ordered(self) -> list[AgentVoice]:
        """Most-moved first: the residents who changed their mind are the story."""
        return sorted(self.voices.values(), key=lambda v: (v.moved, -len(v.turns)))

    @property
    def evaluated(self) -> list[str]:
        """Residents with at least one turn that survived the grounding guard.

        The denominator for every rate this run reports. It is not the population and it
        is not the cohort: a resident who was asked and whose answer was rejected has been
        evaluated to no conclusion, which is a third thing.
        """
        return [pid for pid, v in self.voices.items() if v.turns]

    def coverage(self) -> dict:
        """What this run can and cannot speak for.

        `goal.md` and the brief agree on the rule that makes this necessary: a resident
        nobody asked is *unknown*, never *unaffected*. Reporting a harm rate over the
        cohort while implying the population is the exact error the product exists to
        criticise, so the denominator travels with the number.
        """
        ev = self.evaluated
        return {
            "population": self.population,
            "cohort": len(self.cohort),
            "evaluated": len(ev),
            "unevaluated": max(0, self.population - len(ev)),
            "ungrounded": len(self.ungrounded),
            "unexplained_moves": self.unexplained_moves,
            "strata": dict(self.cohort_strata),
        }


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
    cohort_ids: list[str] | None = None,
) -> DeliberationRun:
    """Run the whole deliberation. Raises if no model is configured.

    `on_voice` is called with each resident as they finish a round, so a stream can show
    the population reacting rather than waiting for all of it.
    """
    if llm is None or llm.provider_name == "mock":
        raise NoModelConfigured(
            "Deliberation needs a model. Set LLM_PROVIDER=groq and GROQ_API_KEY "
            "in the project root .env. There is no offline "
            "substitute: text that reads like a resident and is not one is worse than "
            "no output."
        )

    started = time.monotonic()
    run = DeliberationRun(model=llm.provider_name)
    social = social if social is not None else build_social_graph(pop)
    run.population = len(pop.personas)

    # Who reasons. The cohort is the honest middle between asking everyone -- four hours
    # locally, most of it spent on residents the policy never reaches -- and asking only
    # the harmed, which leaves every rate without a denominator.
    if cohort_ids is not None:
        # An explicit cohort, for comparing an alternative against the policy over the
        # same residents. Re-selecting here would be wrong twice: under an alternative
        # that reopens the stop nobody is "affected", so selection returns an empty
        # cohort -- and a delta measured across two different groups of people is not a
        # delta at all.
        ordered_ids = [pid for pid in cohort_ids if pid in world]
        run.cohort_strata = {"affected": 0, "tied": 0, "comparison": 0,
                             "carried_over": len(ordered_ids)}
    elif limit:
        # An explicit cap still selects rather than slicing: `personas[:12]` returns
        # whoever the generator happened to emit first, and on this population that is
        # twelve people nowhere near the closure, all of whom correctly report nothing.
        cohort = select_cohort(pop, world, social, comparison=0)
        ordered_ids = cohort.ids[:limit]
        run.cohort_strata = {
            "affected": sum(1 for p in ordered_ids if p in set(cohort.affected)),
            "tied": sum(1 for p in ordered_ids if p in set(cohort.tied)),
            "comparison": 0,
        }
    else:
        cohort = select_cohort(pop, world, social)
        ordered_ids = cohort.ids
        run.cohort_strata = cohort.strata()

    run.cohort = ordered_ids
    index = {p.persona_id: p for p in pop.personas if p.persona_id in set(ordered_ids)}
    people = [index[pid] for pid in ordered_ids if pid in index]

    # ---------------------------------------------------------------- round 0
    batches = [people[i:i + BATCH_SIZE] for i in range(0, len(people), BATCH_SIZE)]

    def opening(group):
        ids = [p.persona_id for p in group]
        prompt = opening_prompt([(p, world[p.persona_id]) for p in group], policy_text)
        try:
            raw = _cached_or_call(
                prompt, run.model,
                lambda pr: run_opening(pr, llm, len(ids)).model_dump(), run)
        except DeliberationFailed:
            run.failed_batches += 1
            return []
        from app.schemas.deliberation import OpeningBatch
        return OpeningBatch.model_validate(raw).voices

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        for group, voices in zip(batches, pool.map(opening, batches)):
            # Match on the id the model returned rather than on position. Writing our id
            # over theirs cannot detect a batch that came back reordered -- it relabels
            # it, and twelve residents' reasoning attached to the wrong twelve people
            # still looks like evidence.
            returned = {v.persona_id: v for v in voices}
            for p in group:
                v = returned.get(p.persona_id)
                if v is None:
                    run.failed_batches += 1
                    continue
                w = world[p.persona_id]
                kept = []
                for t in v.turns:
                    normalise_citations(t, p.persona_id)
                    if check_grounding(t, w, 0, heard_from=set()):
                        run.rejected += 1
                        continue
                    kept.append(t)
                if not kept:
                    # Nothing this resident said survived. They are unevaluated, which is
                    # not the same as unaffected, so no blanked turn is invented for them.
                    run.ungrounded.append(p.persona_id)
                    continue
                v.turns = kept
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
            group, _heard_map, prompt = item
            try:
                return _cached_or_call(
                    prompt, run.model,
                    lambda pr: run_round(pr, llm, list(group)).model_dump(), run)
            except DeliberationFailed:
                run.failed_batches += 1
                return None

        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            for (group, heard, _), raw in zip(prepared, pool.map(one_round, prepared)):
                if raw is None:
                    continue
                from app.schemas.deliberation import DeliberationBatch
                batch = DeliberationBatch.model_validate(raw)
                by_id = {t.persona_id: t for t in batch.turns if t.persona_id}
                for pid in group:
                    turn = by_id.get(pid)
                    if turn is None:
                        continue
                    # Only the neighbours this resident was actually shown this round.
                    # Their household is who they live with, not who they heard from.
                    heard_from = {n for n, _ in heard.get(pid, [])}
                    normalise_citations(turn, pid)
                    if check_grounding(turn, world[pid], rnd, heard_from):
                        run.rejected += 1
                        continue
                    # Continuity is recorded, not enforced. Rejecting on it deleted every
                    # resident who declared harm and kept every one who reported nothing,
                    # because only a change needs explaining.
                    prior = run.voices[pid].turns[-1] if run.voices[pid].turns else None
                    if check_continuity(turn, prior):
                        run.unexplained_moves += 1
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
        # Everyone who actually has an opening view. A resident whose round-0 turn was
        # rejected has no voice to continue from, and including them here crashed the
        # loop the first time a real model produced an ungrounded opening -- with a
        # reliable model round 0 never failed, so this never fired.
        return [pid for pid in index if run.voices.get(pid)]

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
