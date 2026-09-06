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


def resident_candidates(report: RemedyReport, removed: set[str]):
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

    out = []
    for i, cluster in enumerate(report.mapped, start=1):
        params: dict = {}
        if cluster.action_type == "retain_stop_peak":
            params = {"stop_ids": sorted(removed), "hours": ["07:00-09:30", "17:00-19:30"]}
        elif cluster.action_type == "add_shuttle_feeder":
            params = {"headway_min": 15, "vehicles": 1}
        elif cluster.action_type == "reroute_feeder":
            params = {"via_stop": sorted(removed)[0] if removed else None}
        elif cluster.action_type == "targeted_support":
            params = {"cohort": "residents reporting harm", "subsidy_type": "fare"}
        elif cluster.action_type == "phase_rollout":
            params = {"delay_weeks": 12, "stages": 2}

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
