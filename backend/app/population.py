"""Personas and households, per C1-C5 and D4.

Two things here carry real weight and are easy to get quietly wrong.

**Households are built before people, and a household lives in one block.** Sample a
subzone per person and a carer ends up living across the estate from the mother they drive
to the clinic, which makes the dependency meaningless and the second-order finding a lie.
`test_care_edges_are_within_a_household` exists because this went wrong once.

**Attributes are conditional, per D4.** Uniform ones would flatten the population and
destroy the subgroup variance the product exists to surface. The clinic-need gradient by
age is what makes the 65+ cohort structurally exposed to a stop removal, which is what
produces the headline finding at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.geography import Geography
from app.rng import derived_rng
from app.scenario import (
    BEHAVIOUR_DIST,
    CLINIC_NEED_BY_AGE,
    MAX_WALK_M,
    MOBILITY_BY_AGE,
    POPULATION_SIZE,
    TRANSFER_TOLERANCE,
)

WORK_START = ("07:00", "07:30", "08:00", "08:30", "09:00")

#: household shapes and their share. `multigen` is the one that matters: it is the only
#: composition that reliably contains both a clinic-dependent elder and a working adult,
#: which is where every CARES_FOR edge comes from.
HOUSEHOLD_TYPES: dict[str, float] = {
    "family_with_children": 0.30,
    "working_adults": 0.20,
    "multigen": 0.18,
    "elder_couple": 0.12,
    "single_adult": 0.12,
    "single_elder": 0.08,
}

#: (role, age band) members of each household type, in order
COMPOSITION: dict[str, list[tuple[str, str]]] = {
    "family_with_children": [("parent", "35-54"), ("parent", "35-54"), ("child", "<18")],
    "working_adults": [("adult", "18-34"), ("adult", "18-34")],
    "multigen": [("elder", "75+"), ("adult", "35-54"), ("child", "<18")],
    "elder_couple": [("elder", "65-74"), ("elder", "65-74")],
    "single_adult": [("adult", "18-34")],
    "single_elder": [("elder", "75+")],
}

AGE_ORDER = ["<18", "18-34", "35-54", "55-64", "65-74", "75+"]


@dataclass
class Persona:
    persona_id: str
    age_band: str
    home_subzone: str
    household_id: str
    household_role: str
    income_band: str
    employment_status: str
    mobility_level: str
    max_walk_m: int
    transfer_tolerance: int
    work_start_time: str | None
    has_car_access: bool
    is_caregiver: bool
    inconvenience_tolerance: float
    switching_propensity: float
    baseline_trust: float
    needs_clinic: bool
    xy: tuple[float, float]
    block_id: str


@dataclass
class CareEdge:
    """Directed and asymmetric. Harm propagates to the carer, never back (D2)."""

    carer: str
    dependent: str
    criticality: str = "high"


@dataclass
class Population:
    personas: list[Persona]
    care_edges: list[CareEdge] = field(default_factory=list)

    def by_id(self) -> dict[str, Persona]:
        return {p.persona_id: p for p in self.personas}


def _unit(rng, key: str) -> float:
    mean, sd = BEHAVIOUR_DIST[key]
    return round(min(1.0, max(0.0, rng.gauss(mean, sd))), 3)


def _mobility(rng, age_band: str) -> str:
    mild, moderate, severe = MOBILITY_BY_AGE[age_band]
    r = rng.random()
    if r < severe:
        return "severe"
    if r < severe + moderate:
        return "moderate"
    if r < severe + moderate + mild:
        return "mild"
    return "none"


def _shift_age(rng, band: str) -> str:
    """Households are not uniform. Nudge a member to a neighbouring band sometimes."""
    i = AGE_ORDER.index(band)
    if rng.random() < 0.30:
        i = max(0, min(len(AGE_ORDER) - 1, i + rng.choice([-1, 1])))
    return AGE_ORDER[i]


def build_population(geo: Geography, size: int = POPULATION_SIZE) -> Population:
    blocks = geo.blocks
    types = list(HOUSEHOLD_TYPES)
    weights = list(HOUSEHOLD_TYPES.values())

    personas: list[Persona] = []
    hh_index = 0
    while len(personas) < size:
        hid = f"hh_{hh_index:04d}"
        hh_index += 1
        hrng = derived_rng(hid)

        # one household, one block, therefore one subzone. this is the invariant.
        home = blocks[hrng.randrange(len(blocks))]
        htype = hrng.choices(types, weights=weights, k=1)[0]
        members = list(COMPOSITION[htype])
        if htype == "family_with_children" and hrng.random() < 0.45:
            members.append(("child", "<18"))
        if htype == "multigen" and hrng.random() < 0.55:
            members.append(("adult", "35-54"))

        car = hrng.random() < 0.34  # a car belongs to a household, not a person
        income = hrng.choices(["low", "mid", "high"], weights=[0.28, 0.52, 0.20], k=1)[0]

        for role, base_band in members:
            if len(personas) >= size:
                break
            pid = f"p_{len(personas):04d}"
            rng = derived_rng(pid)
            band = _shift_age(rng, base_band)
            mobility = _mobility(rng, band)

            if band == "<18":
                employment = "student"
            elif band in ("65-74", "75+"):
                employment = "retired" if rng.random() < 0.88 else "employed"
            else:
                employment = "employed" if rng.random() < 0.86 else "unemployed"

            personas.append(
                Persona(
                    persona_id=pid,
                    age_band=band,
                    home_subzone=home["subzone"],
                    household_id=hid,
                    household_role=role,
                    income_band=income,
                    employment_status=employment,
                    mobility_level=mobility,
                    max_walk_m=MAX_WALK_M[mobility],
                    transfer_tolerance=TRANSFER_TOLERANCE[mobility],
                    work_start_time=rng.choice(WORK_START) if employment == "employed" else None,
                    has_car_access=car and rng.random() < 0.75,
                    is_caregiver=False,  # set by assign_care_edges
                    inconvenience_tolerance=_unit(rng, "inconvenience_tolerance"),
                    switching_propensity=_unit(rng, "switching_propensity"),
                    baseline_trust=_unit(rng, "baseline_trust"),
                    needs_clinic=rng.random() < CLINIC_NEED_BY_AGE[band],
                    xy=(
                        round(home["x"] + home["w"] * (0.2 + 0.6 * rng.random()), 1),
                        round(home["y"] + home["h"] * (0.2 + 0.6 * rng.random()), 1),
                    ),
                    block_id=home["block_id"],
                )
            )

    pop = Population(personas=personas)
    pop.care_edges = assign_care_edges(pop)

    counts: dict[str, int] = {}
    for p in personas:
        counts[p.block_id] = counts.get(p.block_id, 0) + 1
    for b in blocks:
        b["population"] = counts.get(b["block_id"], 0)
    return pop


def assign_care_edges(pop: Population) -> list[CareEdge]:
    """One carer per dependent, inside one household. D2, D4.

    A dependent is someone whose own mobility limits them *and* who has an essential trip
    to lose. A carer is a household member who could absorb that trip: no mobility
    limitation, and in work, which is what makes the absorption cost something.
    """
    households: dict[str, list[Persona]] = {}
    for p in pop.personas:
        households.setdefault(p.household_id, []).append(p)

    edges: list[CareEdge] = []
    for members in households.values():
        dependents = [
            m for m in members
            if m.mobility_level in ("moderate", "severe") and m.needs_clinic
        ]
        carers = [
            m for m in members
            if m.mobility_level == "none" and m.employment_status == "employed"
        ]
        if not dependents or not carers:
            continue
        for i, d in enumerate(dependents):
            carer = carers[i % len(carers)]
            carer.is_caregiver = True
            edges.append(CareEdge(carer=carer.persona_id, dependent=d.persona_id))
    return edges
