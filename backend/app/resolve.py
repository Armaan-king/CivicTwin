"""Work out which town a policy is about, and which real stops it names.

This is the piece that was missing, and its absence was structural: the engine read a town
from an environment variable, guessed which stops to close, and then generated a policy
description to match. The interpreter parsed the planner's actual words and the result was
discarded. Everything downstream was therefore a description of a guess.

Now the text decides. A planner writes about Bedok and the run is about Bedok, because the
stop names in their sentence exist in Bedok's extract and nowhere else.

Nothing here guesses. If a policy names no stop that can be found, it raises and says which
towns were searched, because a run against a silently-chosen study area is worse than no
run: it answers a question nobody asked.
"""
from __future__ import annotations

import json
import pathlib
import re
from dataclasses import dataclass, field

from app.schemas.policy import PolicyChange

DATA = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "lta"

#: A five-digit code is a bus stop id in the LTA feed, and unambiguous.
STOP_CODE = re.compile(r"\b(\d{5})\b")

#: Words that appear in almost every stop name and so identify nothing on their own.
STOPWORDS = {"opp", "aft", "bef", "blk", "stn", "exit", "ave", "st", "rd", "the"}

#: The feed abbreviates and people do not. A planner writes "Ang Mo Kio Avenue 3"; LTA
#: publishes "Ang Mo Kio Ave 3", and without this the two never meet -- the policy resolves
#: to nowhere and the run is refused for naming a road it named correctly.
ABBREV = {
    "avenue": "ave", "street": "st", "road": "rd", "drive": "dr", "crescent": "cres",
    "block": "blk", "central": "ctrl", "north": "nth", "south": "sth", "east": "east",
    "west": "west", "interchange": "int", "station": "stn", "park": "pk",
    "secondary": "sec", "primary": "pr", "community": "cmty", "hospital": "hosp",
    "market": "mkt", "school": "sch", "terminal": "ter", "place": "pl",
    "boulevard": "blvd", "lane": "ln", "close": "cl", "walk": "walk", "link": "link",
}


@dataclass
class Resolution:
    town: str
    #: real stop codes the policy closes
    closures: set[str] = field(default_factory=set)
    #: what matched, so a planner can see how their words were read
    matched: list[str] = field(default_factory=list)
    #: phrases that matched nothing, surfaced rather than dropped
    unmatched: list[str] = field(default_factory=list)
    #: how strongly this town beat the others
    score: int = 0
    considered: list[str] = field(default_factory=list)


class StudyAreaNotFound(RuntimeError):
    """The policy names nowhere we hold data for."""


def available_towns() -> list[str]:
    if not DATA.exists():
        return []
    return sorted(d.name for d in DATA.iterdir()
                  if d.is_dir() and (d / "stops.json").exists())


def _stops(town: str) -> list[dict]:
    return json.loads((DATA / town / "stops.json").read_text(encoding="utf-8"))


def _normalise(s: str) -> str:
    """Lowercase, strip punctuation, and speak the operator's abbreviations."""
    words = re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()
    return " ".join(ABBREV.get(w, w) for w in words)


def _phrases(policy: PolicyChange, text: str) -> list[str]:
    """What the planner named: explicit stop entries first, then the prose."""
    out = [s for s in policy.modifications.remove_stops if s]
    for entity in policy.resolved_entities:
        if entity.kind == "stop":
            out.extend([entity.id, entity.label])
    if text:
        out.append(text)
    return [p for p in out if p]


def resolve_study_area(policy: PolicyChange, text: str = "") -> Resolution:
    """Which town, and which stops. Raises rather than falling back to a default."""
    towns = available_towns()
    if not towns:
        raise StudyAreaNotFound(
            "No study area data at all. Fetch one: python scripts/fetch_lta.py ang-mo-kio"
        )

    phrases = _phrases(policy, text)
    blob = _normalise(" ".join(phrases))
    codes = set(STOP_CODE.findall(" ".join(phrases)))

    best: Resolution | None = None
    for town in towns:
        stops = _stops(town)
        by_code = {s["BusStopCode"]: s for s in stops}
        hits: set[str] = set()
        matched: list[str] = []

        # a code that exists here is decisive and needs no fuzzy matching
        for code in codes:
            if code in by_code:
                hits.add(code)
                matched.append(f"{code} = {by_code[code]['Description']}")

        # otherwise match stop descriptions and road names appearing in the text
        roads: dict[str, int] = {}
        for s in stops:
            desc = _normalise(s["Description"])
            road = _normalise(s.get("RoadName") or "")
            meaningful = [w for w in desc.split() if w not in STOPWORDS and len(w) > 2]
            if meaningful and desc and desc in blob:
                hits.add(s["BusStopCode"])
                matched.append(f"{s['BusStopCode']} = {s['Description']}")
            if road and road in blob:
                roads[road] = roads.get(road, 0) + 1

        score = len(hits) * 10 + sum(roads.values())
        if best is None or score > best.score:
            best = Resolution(town=town, closures=hits, matched=sorted(set(matched)),
                              score=score, considered=towns)

    assert best is not None
    if best.score == 0:
        raise StudyAreaNotFound(
            f"Nothing in that policy names a stop or road we hold data for. "
            f"Searched: {', '.join(towns)}. Either name a stop (a five-digit code, or its "
            f"name as the operator publishes it) or fetch the town first: "
            f"python scripts/fetch_lta.py <town>"
        )

    for phrase in policy.modifications.remove_stops:
        if phrase not in best.closures and not any(phrase in m for m in best.matched):
            best.unmatched.append(phrase)
    return best
