"""A life per resident, generated once and grounded in a real place.

The problem this solves is measurable. `Persona` carries eighteen fields; before this
module six of them reached the model, four of those were about buses, and the deliberation
prompt then said "invent nothing". A model asked for first-person speech from six coarse
bands, and forbidden to elaborate, returns two thousand people who sound like one. The
literature calls it variance collapse and it is the documented failure of conditioning an
agent on demographics alone.

The fix is the one Park et al. use in *Generative Agent Simulations of 1,000 People*: stop
conditioning on attributes and condition on a rich grounding document instead. They ground
each agent in a two-hour interview with a real person. We have no real people and will not
pretend otherwise, so the backstory is generated -- once -- from the attributes and the
real network around that resident, and it is labelled synthetic wherever it surfaces.

Two design rules, both load-bearing:

**No policy text goes into this prompt.** A backstory is who someone is, not what they
think of a proposal. Keeping the policy out means the cache survives every
`PROMPT_VERSION` bump and every new policy in the same town, which is the difference
between two dollars once and two dollars per iteration.

**Place is in the prompt, therefore in the cache key.** `subzone` is the stop's real road
name from the LTA extract, so a resident is written into the road they actually live on
with the services that actually call there. Change town and the key changes and the town
gets its own people, which is the point: someone on Ang Mo Kio Ave 3 has no reason to
sound like someone living at East Coast.

What this does *not* do is condition the underlying distributions on the town. Income and
car ownership are still drawn from one national table for every study area, so a mature
HDB estate and a coastal private one draw the same numbers. That needs planning-area data
and is a real limitation, recorded rather than papered over.
"""
from __future__ import annotations

import json
import os
import pathlib
import time

from pydantic import BaseModel, Field

from app.geography import Geography
from app.graph import TransitNetwork
from app.population import Persona, Population
from app.config import env_float, env_int
from app.services.llm import (LLMClient, LLMError, LLMOutputInvalid,
                              call_with_retries, exact_items)
from app.world import _nearest, _service_names

#: Written per town, and meant to be committed. It is synthetic data with a real
#: provenance -- generated from the LTA extract for that town -- so regenerating it on a
#: demo machine is a cost with no benefit.
STORE = pathlib.Path(__file__).resolve().parents[2] / "data" / "personas"

#: Residents per call. Smaller than the deliberation batch: the output is longer per
#: person and there are no neighbour views to carry, so the ratio lands differently.
#:
#: Back to 10 after measuring. Raising it to 15 was meant to cut the call count, on the
#: assumption that Bedrock throttles per request -- it does not, or not only. The observed
#: limit behaves like a tokens-per-minute quota, so a bigger batch spends the same budget
#: in fewer, larger bites and throttles sooner rather than later. 10 sustained roughly one
#: call a minute for seven minutes; 15 threw on the first call.
BATCH_SIZE = env_int("BACKSTORY_BATCH_SIZE", 10)

#: Seconds to wait between batches. The account's quota is the binding constraint, not our
#: throughput, and pacing under it is cheaper than discovering it by being throttled: a
#: refusal still costs the wait, and it costs the retry as well.
#:
#: 15s, from measurement: 8s produced 36 throttle retries across ~350 residents, and
#: each retry waits 20-240s. Seven more seconds per batch costs about seventeen
#: minutes over a full cohort and buys back more than that in avoided backoff.
PACE_SECONDS = env_float("BACKSTORY_PACE_SECONDS", 15.0)

#: How many times a batch is retried when the *call* fails rather than the answer.
#: Throttling is transient by definition and a long unattended run must not die of one --
#: the first attempt at this lost 768 residents of queued work to a single refusal,
#: because the loop caught a bad answer and let a failed call through.
CALL_RETRIES = env_int("BACKSTORY_CALL_RETRIES", 6)

#: How many times one batch may renew credentials before the session is judged broken.
#: Generous, because a renewal is cheap and a long run legitimately crosses several
#: one-hour credential windows; bounded, so a session that cannot actually authorise
#: stops instead of renewing forever.
MAX_RENEWALS = env_int("BACKSTORY_MAX_RENEWALS", 20)


# --------------------------------------------------------------------------- names
#: A name is a world fact, not a judgement, so the model does not get to invent one.
#:
#: Measured on 60 residents from Claude 3 Haiku: 49 distinct names, with "Lim Mei Ling"
#: appearing four times and three more names repeating. That is not really the model
#: failing -- each call sees ten residents and knows nothing of the other 1,990, so
#: collisions across 200 batches are guaranteed for *any* model. Asking a batch to invent
#: unique identifiers across a population it cannot see is asking for the one thing it
#: structurally cannot do.
#:
#: So it is drawn here instead, seeded per persona exactly like every other attribute
#: (`AGENTS.md` §10: names are lookup, not reasoning). Unique by construction, free, and
#: reproducible -- persona 1847 is the same person on every machine.
#:
#: The mix is roughly Singapore's resident ethnic composition. Synthetic, and labelled as
#: such wherever it surfaces.
_SURNAMES_ZH = ("Tan Lim Lee Ng Ong Wong Goh Chua Koh Teo Sim Yeo Chan Low Toh Chia Heng "
                "Loh Neo Quek Seah Tay Yap Ho Foo Chew Kwek Boon Soh Lau").split()
#: Built from syllables rather than listed whole. A fixed list of thirty given names gives
#: 900 combinations for 1,480 Chinese residents, so roughly every name lands twice; two
#: syllable pools give 900 given names and 27,000 full names, which is enough for the town
#: to have no accidental twins.
_ZH_A = ("Wei Mei Jun Hui Zhi Xin Li Kok Siew Boon Jia Yong Poh Chee Ai Wen Swee Tiong "
         "Hwee Kah Bee Guan Shu Cheng Lay Wee Geok Han Yan Ser").split()
_ZH_B = ("Ming Ling Kai Shan Hao Yi Liang Fang Wah Kim Hock Hua Sheng Choo Keong Leng Jie "
         "Lian Seng Peng Meng Hoon Hin Fen Kiat Lan Chuan Yee Hong Teck").split()

#: Malay names are patronymic -- given name, then bin (son of) or binte (daughter of),
#: then the father's name. Constructing them that way is both more accurate than a flat
#: list and combinatorially large enough to avoid repeats.
_MALAY_GIVEN_M = ("Muhammad Rizal Ahmad Faizal Mohd Hakim Ismail Zainal Hafiz Iskandar "
                  "Shahrul Ridzuan Khairul Amir").split()
_MALAY_GIVEN_F = ("Nur Aisyah Siti Zubaidah Nurul Huda Farah Adilah Rohana Aminah Sharifah "
                  "Zaleha Hidayah Suriani Marlina").split()
_MALAY_FATHER = ("Rahman Yusof Salleh Bakar Osman Hamid Latif Ibrahim Kassim Samad Jalil "
                 "Wahab Karim Aziz Hashim").split()

#: Split by gender because the patronymic is gendered too: s/o is "son of" and d/o is
#: "daughter of", so drawing the marker independently produced "Kavitha s/o Menon".
_INDIAN_GIVEN_M = "Rajesh Suresh Anand Ravi Vijay Arun Ganesh Mohan Prakash Senthil".split()
_INDIAN_GIVEN_F = "Priya Kavitha Meena Lakshmi Shanti Deepa Radha Usha Vasanthi Anitha".split()
_INDIAN_FATHER = ("Kumar Menon Nair Pillai Raman Iyer Krishnan Subramaniam Devan Naidu "
                  "Rajan Balakrishnan").split()


def name_for(persona_id: str) -> str:
    """A stable, unique name for this resident. Same seed, same machine, same person.

    Seeded on the persona id alone, so Bedok's `p_0003` shares a name with Ang Mo Kio's.
    That is deliberate rather than overlooked: adding the town to the seed is two lines,
    and it would invalidate every store already generated for the sake of a collision no
    viewer can encounter, because a run renders one study area and the two are never
    shown together. Revisit if a screen ever compares towns side by side.
    """
    from app.rng import derived_rng
    rng = derived_rng(f"{persona_id}:name")
    r = rng.random()
    if r < 0.74 or r >= 0.96:          # Chinese, plus the small "other" share
        return f"{rng.choice(_SURNAMES_ZH)} {rng.choice(_ZH_A)} {rng.choice(_ZH_B)}"
    if r < 0.87:
        male = rng.random() < 0.5
        given = rng.choice(_MALAY_GIVEN_M if male else _MALAY_GIVEN_F)
        return f"{given} {'bin' if male else 'binte'} {rng.choice(_MALAY_FATHER)}"
    male = rng.random() < 0.5
    given = rng.choice(_INDIAN_GIVEN_M if male else _INDIAN_GIVEN_F)
    return f"{given} {'s/o' if male else 'd/o'} {rng.choice(_INDIAN_FATHER)}"
    if r < 0.87:
        return rng.choice(_MALAY)
    if r < 0.96:
        return rng.choice(_INDIAN)
    return f"{rng.choice(_SURNAMES_ZH)} {rng.choice(_GIVEN_ZH)}"


class Backstory(BaseModel):
    """One resident's life, as much of it as the deliberation can legitimately cite."""

    persona_id: str
    #: Assigned by `name_for`, never by the model -- see the note above the name tables.
    #: Kept on the record so everything downstream reads one field.
    name: str = ""
    #: Assigned by `occupation_for`, never by the model. See the note above `_JOBS`.
    occupation: str = ""
    years_in_estate: int = Field(ge=0, le=80)
    #: A week, in their words. This is what makes the bus matter to a specific life.
    routine: str
    #: What they rely on the network for. Not an opinion about any policy -- there is
    #: none in this prompt -- just what a change would land on.
    depends_on: str
    #: How they talk, so 2,000 residents do not share one register.
    voice: str
    #: Which model wrote this life. The store is a file that gets appended to across
    #: several sittings, and without this a run that switched models halfway leaves a
    #: population that is half one voice and half another with nothing recording it.
    #: A quality comparison between two models needs to know which is which, and so does
    #: anyone reading the export later.
    model: str = ""


class Backstories(BaseModel):
    people: list[Backstory] = Field(default_factory=list)


SYSTEM = """You write short factual biographies of residents of a Singapore housing estate,
for a synthetic population used in transport planning. These are invented people. Write
them as ordinary and specific.

For each resident you are given their demographic record and the real bus network around
their home. Write a life that is consistent with all of it.

Absolute rules:
- Never contradict the record. If it says retired, they are retired. If it says no car,
  they have no car. If it says no difficulty walking, do not give them a bad hip.
- Invent no medical conditions beyond the stated mobility level, and no family members
  beyond the household described.
- `years_in_estate` must be possible for their age. Nobody is 30 and has lived somewhere
  for 40 years.
- Refer to the resident by the name given in their record, and by no other name. The
  name is assigned, not yours to choose: writing "Mr Tan" for a resident recorded as Koh
  Mei Hua puts one person's week under another person's heading, and 13% of an earlier
  run did exactly that.
- `routine` is one or two sentences about an ordinary week, naming the roads, stops and
  services they were given. This is the part that makes them a person rather than a row.
- `depends_on` is one sentence: what they actually need the bus for. Concrete. A Tuesday
  morning at the polyclinic beats "healthcare access".
- `voice` is two to four words for how they speak, such as "brisk, practical" or
  "warm, roundabout".
- Vary them. Different jobs, different registers, different lengths of residence. Two
  neighbours of the same age should not read as the same person.
- Do not mention any policy, closure or proposed change. None has been made.

Respond with a single JSON object matching the Backstories schema. No prose, no fences."""


# ---------------------------------------------------------------- occupations
#: Derived, for the same reason names are. A batch of ten cannot know what the other 820
#: residents do for a living, so it reaches for the most plausible job every time and the
#: town fills up with one profession: measured on the finished cohort, 63 of 155 retirees
#: -- 41% -- were "retired teacher". Nobody in a batch did anything wrong; the population
#: is simply not visible from inside one.
#:
#: So the *job* is drawn here from the resident's own employment status, income band and
#: age, and the model is told what it is. Judging what that life is like remains the
#: model's work; deciding how many teachers a town has is not judgement, it is a
#: distribution.
_JOBS = {
    ("employed", "low"): ("cleaner", "security guard", "hawker assistant", "bus captain",
                          "retail assistant", "kitchen helper", "delivery rider",
                          "childcare assistant", "warehouse packer", "car park attendant"),
    ("employed", "mid"): ("nurse", "primary school teacher", "administrative assistant",
                          "technician", "bank teller", "logistics coordinator",
                          "physiotherapist", "draughtsman", "HR executive", "chef",
                          "insurance agent", "lab technician", "social worker"),
    ("employed", "high"): ("software engineer", "civil engineer", "accountant",
                           "project manager", "doctor", "lawyer", "architect",
                           "financial analyst", "operations director", "dentist"),
    ("unemployed", "low"): ("between jobs", "looking for work", "homemaker"),
    ("unemployed", "mid"): ("between jobs", "homemaker", "retraining"),
    ("unemployed", "high"): ("between jobs", "taking a career break"),
}
#: What a retiree used to do. Retirement is not itself an occupation, and a town of
#: retired teachers is the specific failure this exists to prevent.
_RETIRED = ("retired teacher", "retired shopkeeper", "retired clerk", "retired technician",
            "retired nurse", "retired hawker", "retired driver", "retired accountant",
            "retired seamstress", "retired civil servant", "retired mechanic",
            "retired factory worker", "retired storeman", "retired cook",
            "retired bus captain", "retired policeman")


def occupation_for(p: Persona) -> str:
    """This resident's job, drawn from their own record rather than invented per batch."""
    from app.rng import derived_rng
    rng = derived_rng(f"{p.persona_id}:occupation")
    if p.age_band == "<18":
        return "primary student" if rng.random() < 0.45 else "secondary student"
    if p.employment_status == "student":
        return rng.choice(("polytechnic student", "junior college student",
                           "university student", "ITE student"))
    if p.employment_status == "retired":
        return rng.choice(_RETIRED)
    return rng.choice(_JOBS.get((p.employment_status, p.income_band),
                                _JOBS[("employed", "mid")]))


def _brief(p: Persona, geo: Geography, net: TransitNetwork, pop: Population) -> str:
    """One resident's record and the real network at their door.

    Every field the deliberation never saw goes in here: income band, household role,
    whether anyone depends on them. They were generated, stored, read by the rules engine
    and withheld from the only component asked to speak as this person.
    """
    lines = [
        f"RESIDENT {p.persona_id}",
        f"  name: {name_for(p.persona_id)}",
        f"  occupation: {occupation_for(p)}",
        f"  age band: {p.age_band}",
        f"  household role: {p.household_role} in a household of "
        f"{sum(1 for q in pop.personas if q.household_id == p.household_id)}",
        f"  employment: {p.employment_status}"
        + (f", starts work at {p.work_start_time}" if p.work_start_time else ""),
        f"  income band: {p.income_band}",
        f"  mobility: {p.mobility_level} difficulty walking, "
        f"comfortable up to about {p.max_walk_m} m to a stop",
        f"  car in household: {'yes' if p.has_car_access else 'no'}",
        f"  lives on: {p.home_subzone}",
    ]
    if p.needs_clinic:
        dest = geo.stops[geo.clinic_stops[0]].name if geo.clinic_stops else "the polyclinic"
        lines.append(f"  makes a regular trip to {dest} that cannot be skipped")

    near = _nearest(net, p.xy, geo.clinic_stops, set())
    if near:
        sid, d = near
        lines.append(f"  nearest stop: {geo.stops[sid].name} ({sid}), about {round(d)} m walk")
        services = _service_names(geo, sid)
        if services:
            lines.append(f"  services calling there: {', '.join(services)}")

    by_id = pop.by_id()
    for e in pop.care_edges:
        if e.carer == p.persona_id:
            lines.append(f"  helps {by_id[e.dependent].age_band} household member "
                         f"{e.dependent} get about")
        if e.dependent == p.persona_id:
            lines.append(f"  is helped to get about by household member {e.carer}")
    return "\n".join(lines)


def _prompt(people: list[Persona], geo: Geography, net: TransitNetwork,
            pop: Population, town: str) -> str:
    briefs = "\n\n".join(_brief(p, geo, net, pop) for p in people)
    return (
        f"TOWN: {town}. All roads, stops and services named below are real and come from "
        f"Singapore's LTA network extract for this town.\n\n"
        f"{len(people)} RESIDENTS:\n\n{briefs}\n\n"
        f"Return a Backstories object with exactly {len(people)} entries, one per "
        f"resident, in this order, with persona_id copied exactly."
    )


class BackstoryFailed(RuntimeError):
    """The batch came back short, empty, or for the wrong people."""


def _run_batch(people: list[Persona], geo: Geography, net: TransitNetwork,
               pop: Population, town: str, llm: LLMClient) -> list[Backstory]:
    ids = [p.persona_id for p in people]
    try:
        batch = llm.structured(
            Backstories, SYSTEM, _prompt(people, geo, net, pop, town),
            # 4096 is the hard ceiling on Claude 3 Haiku and asking for more is a
            # ValidationException, not a truncation. Ten biographies at ~210 tokens plus
            # JSON scaffolding lands near 2,700, so 4,000 leaves headroom without
            # shrinking the batch.
            max_tokens=4000,
            schema_override=exact_items(Backstories, "people", len(ids)))
    except LLMOutputInvalid as exc:
        raise BackstoryFailed(f"batch was not valid: {exc.detail}") from exc
    returned = [b.persona_id for b in batch.people]
    if returned != ids:
        # Validated, never repaired. Overwriting the ids would attach ten lives to the
        # wrong ten people, and the result would still look like a population.
        raise BackstoryFailed(f"batch named {returned or 'nobody'}, expected {ids}")
    return batch.people


def _write_store(town: str, have: dict[str, Backstory]) -> None:
    """Write the store atomically: temp file, then rename.

    A plain `write_text` leaves the file readable while it is half-written, so anything
    reading it mid-write gets truncated JSON. That is not hypothetical -- two generation
    runs were briefly alive at once and both had this file open, and a plain write would
    have let one of them read a half-finished object and lose every resident in it. The
    deliberation cache has done it this way from the start; this did not, for no reason
    other than that nobody had run two at once yet.
    """
    path = path_for(town)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(
        json.dumps({k: v.model_dump() for k, v in sorted(have.items())}, indent=1),
        encoding="utf-8")
    tmp.replace(path)


def _call_with_retries(group, geo, net, pop, town, llm, on_batch):
    """One batch, retried on transport failure.

    This used to be a second, separate implementation of the retry/backoff/credential
    renewal logic that also lives in `services.llm.call_with_retries`. Keeping two was
    the single most expensive habit of the night: a fix landed in one copy and not the
    other three separate times -- the deliberation had no LLMError handling at all while
    this module did, then this module had pacing while the deliberation did not, then a
    renewal consumed a retry attempt here after being fixed there.

    One implementation. `BackstoryFailed` is not an `LLMError` and so passes straight
    through to the caller, which counts it and moves on -- a bad answer is not worth
    retrying, only a failed call is.
    """
    return call_with_retries(
        lambda: _run_batch(group, geo, net, pop, town, llm),
        retries=CALL_RETRIES,
        renewals=MAX_RENEWALS,
        on_note=(lambda m: on_batch(-1, -1, m)) if on_batch else None,
    )


def path_for(town: str) -> pathlib.Path:
    return STORE / f"{town}.json"


def load(town: str) -> dict[str, Backstory]:
    """Whatever has already been written for this town. Empty is a normal state."""
    p = path_for(town)
    if not p.exists():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    return {pid: Backstory.model_validate(b) for pid, b in raw.items()}


def build_backstories(
    pop: Population,
    geo: Geography,
    town: str,
    llm: LLMClient,
    only: list[str] | None = None,
    on_batch=None,
) -> dict[str, Backstory]:
    """Generate what is missing for this town and write the store back.

    Resumable on purpose. This is the one bulk spend in the project and a run that dies
    two thirds through must not have to buy the first two thirds again, so the store is
    written after each batch. `LLMClient.structured` caches on a content hash underneath,
    so a rerun costs nothing for the batches that already succeeded.

    `only` restricts generation to a list of persona ids -- the cohort, when the whole
    town is not worth paying for yet.
    """
    have = load(town)
    keep = set(only) if only is not None else None
    wanted = [p for p in pop.personas
              if (keep is None or p.persona_id in keep)
              and p.persona_id not in have]
    if not wanted:
        return have

    net = TransitNetwork(geo)          # baseline network: no policy, no closures
    STORE.mkdir(parents=True, exist_ok=True)
    failed: list[str] = []
    by_id = pop.by_id()

    for i in range(0, len(wanted), BATCH_SIZE):
        group = wanted[i:i + BATCH_SIZE]
        if i:
            time.sleep(PACE_SECONDS)
        try:
            for b in _call_with_retries(group, geo, net, pop, town, llm, on_batch):
                b.model = llm.provider_name
                b.name = name_for(b.persona_id)
                b.occupation = occupation_for(by_id[b.persona_id])
                have[b.persona_id] = b
        except (BackstoryFailed, LLMError) as exc:
            # Counted and reported, never substituted. A resident with no backstory falls
            # back to their bare record, which is the old behaviour and is honest.
            failed.extend(p.persona_id for p in group)
            if on_batch:
                on_batch(len(have), len(wanted), str(exc))
            continue
        _write_store(town, have)
        if on_batch:
            on_batch(len(have), len(wanted), None)

    if failed:
        print(f"  {len(failed)} residents have no backstory and will use their bare "
              f"record: {', '.join(failed[:6])}{' ...' if len(failed) > 6 else ''}")
    return have
