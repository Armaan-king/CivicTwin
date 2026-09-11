"""What residents said would make the policy workable, clustered and mapped. J4 · LOCKED.

The planner's five typed actions in **J1** stay exactly as they are. This is the other
source of candidates: harmed residents are asked one further question during the
deliberation they were already paying for, and their answers become proposals that go
through the same validator and the same re-evaluation as a planner candidate. No shortcut,
no exemption.

**Unmappable requests are reported, not discarded.** When residents ask for something the
action space cannot express -- somewhere to sit, a shelter over the new walk, a different
appointment time -- that gap between what people need and what the model can represent is
itself a finding, and J4 requires it on the screen rather than in a dropped list.

The mapping is a declared keyword table rather than a model call, for three reasons: it is
inspectable, it is testable, and a second model pass over free text is exactly where a
"remedy" the resident never asked for would get invented.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Phrases that map a resident's words onto a typed action from J1. Ordered: the first
#: matching rule wins, so the rule naming a specific instrument comes before the general
#: one. "A shuttle to the stop that is staying open" is a request for a shuttle, and a
#: retain-the-stop rule reading only the words "stop ... open" would claim it first.
MAPPING: list[tuple[str, str, str]] = [
    # (action type, human label for the cluster, regex over the lowercased remedy)
    # Ordered so the rule naming a specific instrument wins. "A shuttle to the stop that
    # is staying open" is a request for a shuttle; a retain-the-stop rule reading only the
    # words "stop ... open" would otherwise claim it first.
    ("add_shuttle_feeder", "a shuttle or feeder bus to the stop that stays open",
     r"\b(shuttle|feeder|minibus|mini-bus|another bus|extra bus|direct bus)\b"),
    ("reroute_feeder", "route an existing service past me",
     r"\b(re-?route|divert|detour|pass(es)? by|come(s)? past|go(es)? via)\b"),
    ("targeted_support", "help with the cost of getting there another way",
     r"\b(subsid|voucher|concession|discount|fare|free ride|taxi fare|cheaper)\b"),
    ("retain_stop_peak", "keep the stop open at the times I travel",
     r"\b(keep|retain|reopen|re-open|not close|don'?t close|leave)\b.*\b(stop|bus stop)\b"
     r"|\b(stop|bus stop)\b.*\b(open|stay|remain)\b"
     r"|\bpeak\b.*\b(hour|time|morning|evening)\b"),
    # Deliberately narrow. An earlier version matched a bare "later", which swallowed
    # "if the clinic gave me a later appointment" -- a request about the resident's own
    # schedule, which this action space cannot express and J4 requires be reported as such.
    ("phase_rollout", "bring it in gradually",
     r"\b(phase|phased|gradual|gradually|slowly|trial|pilot|postpone)\b"
     r"|\bdelay\b.*\b(roll ?out|change|closure|policy)\b"
     r"|\bnotice period\b"),
]


@dataclass
class RemedyCluster:
    """A distinct proposal, and how many residents asked for it."""
    action_type: str
    label: str
    count: int = 0
    residents: list[str] = field(default_factory=list)
    #: verbatim, so a reader can check the cluster against what was actually said
    examples: list[str] = field(default_factory=list)


@dataclass
class UnmappableCluster:
    """Something residents asked for that the action space cannot express."""
    label: str
    count: int = 0
    residents: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


@dataclass
class RemedyReport:
    mapped: list[RemedyCluster] = field(default_factory=list)
    unmappable: list[UnmappableCluster] = field(default_factory=list)
    #: residents who were harmed and asked, but said nothing usable
    silent: int = 0

    def asked(self) -> int:
        return (sum(c.count for c in self.mapped)
                + sum(c.count for c in self.unmappable) + self.silent)


#: Recurring shapes of request the five typed actions cannot represent. Named so the
#: report can group them, because "31 residents asked for something we cannot simulate"
#: is only a finding if it says what they asked for.
UNMAPPABLE_KINDS: list[tuple[str, str]] = [
    ("somewhere to sit or shelter while waiting",
     r"\b(seat|sit|bench|shelter|shade|cover|rain|sun|canopy|sheltered)\b"),
    ("help with the walk itself",
     r"\b(ramp|handrail|rail|lift|escalator|even pavement|kerb|curb|slope|steps?)\b"),
    ("a different appointment or working time",
     r"\b(appointment|clinic time|working hours|shift|start later|reschedul)\b"),
    ("someone to go with them",
     r"\b(someone to|help me|accompan|escort|carer|volunteer)\b"),
]


def _match(text: str, table) -> tuple | None:
    low = text.lower()
    for entry in table:
        if re.search(entry[-1], low):
            return entry
    return None


def cluster_remedies(remedies: dict[str, str]) -> RemedyReport:
    """Group what residents asked for. `remedies` is persona_id -> their own words.

    Every resident who was asked appears in exactly one place: a mapped cluster, an
    unmappable cluster, or the silent count. Nothing is dropped, because the whole point
    of J4 is that the gap is visible.
    """
    report = RemedyReport()
    mapped: dict[str, RemedyCluster] = {}
    unmapped: dict[str, UnmappableCluster] = {}

    for pid, text in sorted(remedies.items()):
        if not text or not text.strip():
            report.silent += 1
            continue

        # Unmappable shapes are tested first. They name a concrete human need -- a seat,
        # a shelter, a different appointment -- and the policy vocabulary is loose enough
        # that a general rule would otherwise claim them and quietly convert a need this
        # model cannot meet into a typed action nobody asked for.
        kind = _match(text, UNMAPPABLE_KINDS)
        if kind:
            u = unmapped.setdefault(kind[0], UnmappableCluster(kind[0]))
            u.count += 1
            u.residents.append(pid)
            if len(u.examples) < 3:
                u.examples.append(text.strip())
            continue

        hit = _match(text, MAPPING)
        if hit:
            action_type, label, _ = hit
            c = mapped.setdefault(action_type, RemedyCluster(action_type, label))
            c.count += 1
            c.residents.append(pid)
            if len(c.examples) < 3:
                c.examples.append(text.strip())
            continue

        label = "something else this model cannot represent"
        u = unmapped.setdefault(label, UnmappableCluster(label))
        u.count += 1
        u.residents.append(pid)
        if len(u.examples) < 3:
            u.examples.append(text.strip())

    report.mapped = sorted(mapped.values(), key=lambda c: -c.count)
    report.unmappable = sorted(unmapped.values(), key=lambda c: -c.count)
    return report


def collect_remedies(run) -> dict[str, str]:
    """Pull each harmed resident's own words out of a finished deliberation.

    Takes the last turn that carries one, so a resident who articulated what they needed
    in round 1 and stopped talking about it is still heard.
    """
    out: dict[str, str] = {}
    for pid, voice in run.voices.items():
        for turn in reversed(voice.turns):
            if turn.remedy and turn.remedy.strip():
                out[pid] = turn.remedy.strip()
                break
        else:
            if voice.turns and voice.turns[-1].severity != "none":
                out[pid] = ""          # harmed, asked, said nothing usable
    return out


#: Cost index per typed action, relative to baseline 1.00x (J3). Illustrative coefficients,
#: never currency: no real costing exists here and inventing one would be fabricated
#: provenance (`AGENTS.md` §16). Shown beside the comparison, labelled as illustrative.
RESIDENT_COST_INDEX = {
    "retain_stop_peak": 0.99,
    "add_shuttle_feeder": 1.12,
    "reroute_feeder": 0.96,
    "targeted_support": 1.03,
    "phase_rollout": 1.01,
}


def resident_candidates(report: RemedyReport, removed: set[str], geo=None):
    """Turn clustered resident requests into candidates for the ordinary validator.

    J4 is explicit that these get "the same validator and the same re-simulation as a
    planner candidate. No shortcut, no exemption." So this builds `Candidate` objects and
    hands them back unvalidated and unscored -- the caller runs `validate()` and, only if
    that passes, evaluates them.

    `add_shuttle_feeder` carries `vehicles: 1` deliberately. The validator rejects it when
    the policy declares no fleet increase, which is the correct outcome and a real finding:
    the thing most residents asked for is the thing the policy's own constraint forbids.
    Softening it to zero vehicles to make it pass would be inventing a shuttle that needs
    no bus.
    """
    from app.interventions import Candidate

    from app.interventions import _nearest_surviving

    # The stops a resident asking for "a bus nearer my home" is actually asking about.
    # Looked up, not guessed: the resident named a need, and which stops satisfy it is a
    # question about the network.
    nearby = _nearest_surviving(geo, removed, per_closure=2) if geo is not None else []

    out = []
    for i, cluster in enumerate(report.mapped, start=1):
        params: dict = {}
        if cluster.action_type == "retain_stop_peak":
            params = {"stops": sorted(removed), "hours": "07:00-09:30, 17:00-19:30"}
        elif cluster.action_type == "add_shuttle_feeder":
            # `serves` and the key names below are what `run_candidate` actually reads.
            # They used to be `stop_ids`, `via_stop`, and nothing at all for `serves`, so
            # a resident request that ever passed validation would have died on a KeyError
            # the moment somebody asked to evaluate it. It never did, because these are
            # listed and not evaluated -- a latent crash waiting on a feature.
            params = {"serves": nearby, "headway_min": 15, "vehicles": 1}
        elif cluster.action_type == "reroute_feeder":
            params = {"add": nearby, "drop": []}
        elif cluster.action_type == "targeted_support":
            params = {"eligible": "residents reporting harm", "subsidy_type": "fare"}
        elif cluster.action_type == "phase_rollout":
            params = {"close_now": sorted(removed)[:1], "defer": sorted(removed)[1:],
                      "delay_weeks": 12}

        out.append(Candidate(
            intervention_id=f"resident_{i:02d}",
            kind=cluster.action_type,
            name=cluster.label,
            params=params,
            rationale=(f"{cluster.count} resident"
                       f"{'s' if cluster.count != 1 else ''} asked for this during "
                       f"deliberation. Example: \"{cluster.examples[0]}\""
                       if cluster.examples else f"{cluster.count} residents asked for this."),
            estimated_cost_index=RESIDENT_COST_INDEX.get(cluster.action_type, 1.0),
        ))
    return out


# --------------------------------------------------------------------------- classifier
"""What a resident meant, decided by a model rather than by a regex.

Measured on the recorded Ang Mo Kio run: of 175 residents who offered a remedy, the
regex table placed 102, called 10 unmappable, and **matched nothing at all for 63 -- 36%**.
Those did not fail on exotic phrasing. They fail on the ordinary way people speak:

    "I would need a bus stop closer to my home"
    "Ensure the revised bus routes still provide convenient access to the hospital"
    "I would need to find an alternative bus route"

A human places all three immediately. Worse, a miss is silently counted as *asked for
nothing*, which inflates the exact number this feature exists to report honestly.

The regex is kept and still runs. Not as a fallback -- as a second opinion. Two
independent classifiers agreeing is evidence; where they disagree is what a person should
look at, and it costs nothing because the table is already there.

Two rules this classifier must obey, and they are why it is a schema rather than a prompt:

  - **It may refuse.** `action_type` is nullable. A model forced to choose from five
    options will always choose one, and the gap between what residents need and what the
    model can represent -- somewhere to sit, a later appointment -- would vanish. That gap
    is a finding, not a rounding error.
  - **It classifies, it does not invent.** The five actions are the whole space. A model
    proposing a sixth is proposing policy, which is not its job.
"""

from pydantic import BaseModel, Field

#: The whole action space. Mirrors `schemas/run.py`; a model may pick from these or none.
ACTION_TYPES = ("retain_stop_peak", "add_shuttle_feeder", "reroute_feeder",
                "targeted_support", "phase_rollout")


class RemedyClassification(BaseModel):
    persona_id: str
    #: One of ACTION_TYPES, or null when the action space cannot express the request.
    action_type: str | None = None
    #: Required when action_type is null: what they asked for, in a few words, so the
    #: unmappable clusters are readable rather than a count.
    unmappable_reason: str | None = None
    #: The model's own reading, for the audit trail and for comparing against the regex.
    quote: str = Field(default="", max_length=200)


class RemedyBatch(BaseModel):
    classifications: list[RemedyClassification] = Field(default_factory=list)


CLASSIFIER_SYSTEM = """You classify what a resident asked for onto a fixed set of transport
interventions. You are not proposing policy: the five actions below are the entire space.

    retain_stop_peak     keep the closing stop open, at least at certain times
    add_shuttle_feeder   a new small bus or shuttle linking them to where they need to go
    reroute_feeder       send an existing service past them instead
    targeted_support     help with the cost or with door-to-door transport
    phase_rollout        bring the change in gradually, or delay it

Rules:
- `action_type` is one of those five, or null.
- **Use null whenever none of the five genuinely fits.** A request for somewhere to sit
  while waiting, a shelter, a handrail, a different appointment time, or someone to
  accompany them is NOT one of these actions. Say null and fill `unmappable_reason` with
  a few words describing what they actually asked for. Forcing such a request into the
  nearest action hides the difference between what residents need and what this model can
  represent, and that difference is the point of asking them.
- A resident asking for a stop "closer to home", for a route that "still passes" their
  area, or for "an alternative route" is asking for `reroute_feeder` unless they name a
  new vehicle, in which case it is `add_shuttle_feeder`.
- `quote` is the few words from their own sentence that decided it.
- One classification per resident, in the order given, with persona_id copied exactly.

Respond with a single JSON object matching the RemedyBatch schema."""


def classify_remedies(remedies: dict[str, str], llm, batch_size: int = 20,
                      on_note=None) -> dict[str, RemedyClassification]:
    """Classify every remedy through the model. Batched, and every batch is validated."""
    from app.services.llm import call_with_retries, exact_items

    ids = sorted(remedies)
    out: dict[str, RemedyClassification] = {}
    for i in range(0, len(ids), batch_size):
        group = ids[i:i + batch_size]
        listing = "\n".join(f'{pid}: "{remedies[pid][:300]}"' for pid in group)
        prompt = (f"{len(group)} residents, each with what they said would make the "
                  f"policy workable for them:\n\n{listing}\n\n"
                  f"Return exactly {len(group)} classifications, in this order.")
        batch = call_with_retries(
            lambda: llm.structured(
                RemedyBatch, CLASSIFIER_SYSTEM, prompt, max_tokens=3000,
                schema_override=exact_items(RemedyBatch, "classifications", len(group))),
            on_note=on_note)
        for c in batch.classifications:
            if c.persona_id in remedies:
                if c.action_type not in ACTION_TYPES:
                    # A model naming a sixth action is proposing policy. Treated as a
                    # refusal, which is the honest reading of "none of these fit".
                    c.action_type = None
                out[c.persona_id] = c
        if on_note:
            on_note(f"classified {len(out)}/{len(ids)}")
    return out
