"""World facts: what is true around a resident, looked up and handed to them.

This is the line V2 draws. **Facts are retrieved, consequences are reasoned.** A model
asked how far it is to the next stop will invent a plausible number; a model asked what a
380 m walk means to someone with a bad hip is the entire point of the product.

So everything here is lookup and geometry, and none of it judges. Nothing in this module
decides whether a resident is harmed, how badly, or what they do about it. It says the
stop outside their block is closed and the next one that still reaches the hospital is
380 m away, and then it stops talking.

Every fact carries an id. An agent may cite only the ids it was given, which is what makes
its conclusion checkable (`AGENTS.md` §8).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.geography import Geography, distance_m
from app.graph import TransitNetwork, walk_m
from app.population import Persona, Population


@dataclass
class Fact:
    id: str
    text: str
    #: which round this becomes true. 0 is the world as it stands before the policy.
    round: int = 0


@dataclass
class ResidentWorld:
    """Everything one resident can legitimately reason from."""
    persona_id: str
    facts: list[Fact] = field(default_factory=list)
    #: household members and social ties, by persona_id
    household: list[str] = field(default_factory=list)
    depends_on_me: list[str] = field(default_factory=list)
    i_depend_on: list[str] = field(default_factory=list)

    def ids(self) -> set[str]:
        return {f.id for f in self.facts}

    def upto(self, rnd: int) -> list[Fact]:
        return [f for f in self.facts if f.round <= rnd]


def _service_names(geo: Geography, stop_id: str) -> list[str]:
    """Route numbers as a resident says them: "138", not "138:2".

    The colon suffix is our own bookkeeping for the second direction of a service. Handing
    it to an agent invites it to repeat an identifier back to a reader as if it were the
    name of a bus.
    """
    return sorted({s.service_id.split(":")[0] for s in geo.serving(stop_id)})[:6]


def _nearest(net: TransitNetwork, xy, dest_stops: list[str], exclude: set[str]):
    """Nearest usable stop, and whether anything there reaches the destination."""
    best = None
    for sid in net.live_stops():
        if sid in exclude:
            continue
        d = walk_m(xy, net.geo.stops[sid].xy)
        if best is None or d < best[1]:
            best = (sid, d)
    return best


def build_resident_world(
    p: Persona,
    pop: Population,
    geo: Geography,
    before: TransitNetwork,
    after: TransitNetwork,
    closed: set[str],
) -> ResidentWorld:
    """The numbered facts this resident is given, and nothing else."""
    w = ResidentWorld(persona_id=p.persona_id)
    n = [0]

    def fact(text: str, rnd: int = 0) -> None:
        n[0] += 1
        w.facts.append(Fact(id=f"{p.persona_id}:f{n[0]}", text=text, round=rnd))

    dest = geo.clinic_stops
    dest_name = geo.stops[dest[0]].name if dest else "the hospital"

    # ---------------------------------------------------------------- round 0: the world
    near_before = _nearest(before, p.xy, dest, set())
    if near_before:
        sid, d = near_before
        fact(f"Your nearest bus stop is {geo.stops[sid].name} ({sid}), "
             f"about {round(d)} m walk from home.")
        services = _service_names(geo, sid)
        if services:
            fact(f"Services calling at {geo.stops[sid].name}: {', '.join(services)}.")

    if p.needs_clinic:
        fact(f"You make a regular trip to {dest_name}, which you cannot skip.")
        d_hosp = distance_m(p.xy, geo.polyclinic)
        fact(f"{dest_name} is about {round(d_hosp)} m from home in a straight line, "
             f"too far to walk.")

    fact(f"You are {p.age_band}, {p.employment_status}."
         + (f" You start work at {p.work_start_time}." if p.work_start_time else ""))
    if p.mobility_level != "none":
        fact(f"You have {p.mobility_level} difficulty walking. You would not normally walk "
             f"more than about {p.max_walk_m} m to a stop.")
    else:
        fact(f"You walk without difficulty, up to about {p.max_walk_m} m to a stop.")
    fact("There is a car in your household." if p.has_car_access
         else "Your household does not have a car.")

    # ---------------------------------------------------------------- round 1: the policy
    closed_names = ", ".join(f"{geo.stops[c].name} ({c})" for c in sorted(closed)
                             if c in geo.stops)
    fact(f"The policy closes these stops: {closed_names}.", rnd=1)

    if near_before and near_before[0] in closed:
        fact(f"{geo.stops[near_before[0]].name} is the stop you use. It is closing.", rnd=1)
        near_after = _nearest(after, p.xy, dest, closed)
        if near_after:
            sid2, d2 = near_after
            extra = round(d2 - near_before[1])
            fact(f"The nearest stop that stays open is {geo.stops[sid2].name} ({sid2}), "
                 f"about {round(d2)} m from home. That is {extra:+d} m compared with now.",
                 rnd=1)
            svc2 = _service_names(geo, sid2)
            if svc2:
                fact(f"Services calling at {geo.stops[sid2].name}: {', '.join(svc2)}.", rnd=1)
    else:
        fact("None of the closing stops is the one you normally use.", rnd=1)

    # ---------------------------------------------------------------- ties
    by_id = pop.by_id()
    w.household = [q.persona_id for q in pop.personas
                   if q.household_id == p.household_id and q.persona_id != p.persona_id]
    for e in pop.care_edges:
        if e.carer == p.persona_id:
            w.depends_on_me.append(e.dependent)
        if e.dependent == p.persona_id:
            w.i_depend_on.append(e.carer)

    for dep in w.depends_on_me:
        d = by_id[dep]
        fact(f"{dep} lives with you: {d.age_band}, "
             f"{d.mobility_level if d.mobility_level != 'none' else 'no'} difficulty walking"
             + (f", and makes the same trip to {dest_name}." if d.needs_clinic else "."))
    for car in w.i_depend_on:
        fact(f"{car} lives with you and helps you get about.")

    return w


def build_world(
    pop: Population, geo: Geography, closed: set[str]
) -> dict[str, ResidentWorld]:
    before = TransitNetwork(geo)
    after = TransitNetwork(geo, removed=closed)
    return {
        p.persona_id: build_resident_world(p, pop, geo, before, after, closed)
        for p in pop.personas
    }
