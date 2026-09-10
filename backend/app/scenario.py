"""Every declared constant and coefficient in the V1 scenario, in one place.

`AGENTS.md` §6 bans unexplained magic constants. The stronger reason for one file is
`G3`: the behavioural coefficients are **assumptions, not evidence**, and the honest story
at demo time is "here is what we assumed, and here is how wrong it turned out to be".
That story needs somewhere to point.

Nothing here is fitted to data. Anything that later is must say so on its own line.
"""
from __future__ import annotations

from typing import Final

SCENARIO_ID: Final = "scenario_sg_bus_v1"
SCENARIO_SEED: Final = 20260118
#: Fallback display name only. The real study area comes from the policy that was
#: submitted -- `engine.build_run` derives it from the town the words resolved to -- so
#: this is what a run built with no policy at all is labelled, and nothing else.
#:
#: It was previously shipped as the run's `study_area` unconditionally, which meant a
#: Bedok policy produced Bedok geography, Bedok stops and Bedok residents under a heading
#: that said Ang Mo Kio. A label that contradicts the data beneath it is worse than no
#: label, because it reads as a result.
STUDY_AREA: Final = "Ang Mo Kio"


def town_display(town: str) -> str:
    """`ang-mo-kio` -> `Ang Mo Kio`. The slug is a directory name, not a place name."""
    return " ".join(w.capitalize() for w in town.replace("_", "-").split("-") if w)
#: Residents who exist in the study area. Every town gets this many, and it costs
#: nothing: the population is pure Python from a seed, built in about 0.3 seconds.
#:
#: **Three different numbers get confused for each other, so they are written down here
#: once.** They are nested, not alternatives:
#:
#:     POPULATION_SIZE  2000    everyone in the town. Free. Never the thing being paid for.
#:       cohort          818    who is asked to reason. `cohort.select_cohort`. THIS is
#:                              the number that drives model cost, and it is built from
#:                              three strata:
#:         affected        43      the policy reaches their own stop
#:         tied           175      household and care ties to someone affected
#:         comparison     600      a stratified control group, so every rate has a
#:                                 denominator and subgroup cells clear MIN_CELL
#:
#: The figures above are Ang Mo Kio under the default closures; Bedok comes out at 770
#: because a different network reaches a different number of people. Quoting "600" as if
#: it were the population, or the cohort as if it were the town, is how this gets
#: misread -- the comparison budget is a stratum inside the cohort, and the cohort is a
#: subset of the population.
#:
#: Residents outside the cohort are **unevaluated, never unaffected**, and every rate the
#: product reports travels with the denominator it was computed over.
POPULATION_SIZE: Final = 2000
ROUNDS: Final = 4  # 0..3, scenario-v1.md B1

# ------------------------------------------------------------------ C3 mobility mapping
#: metres a person will walk to a stop. A spec, not a hint: test_contract asserts it.
MAX_WALK_M: Final[dict[str, int]] = {"none": 1200, "mild": 800, "moderate": 500, "severe": 250}

#: `max_walk_m` is what someone says they will walk. It is a comfort threshold, not a
#: physical ceiling: when their stop goes away people stretch past it before giving up.
#: This multiplier is where they stop stretching, and the band between the two is what
#: F1.6 and F3 are describing.
#:
#:     <= 1.0x    fine
#:     1.0-1.5x   THRESHOLD_EXCEEDED, moderate harm
#:     1.5-2.0x   severe: they still make the trip, at a cost they should not be paying
#:     > 2.0x     the destination is transit-unreachable for them
WALK_CEILING_MULTIPLIER: Final = 2.0

#: severe mobility tolerates no transfers at all. Everyone else, one or two.
TRANSFER_TOLERANCE: Final[dict[str, int]] = {"none": 2, "mild": 2, "moderate": 1, "severe": 0}

# ------------------------------------------------------------------ F1 journey constants
#: straight-line to walkable distance. Declared, and exactly the kind of assumption a
#: resident comment can legitimately attack, which makes it useful demo material (F1.2).
DETOUR_FACTOR: Final = 1.35
WALK_SPEED_M_PER_MIN: Final = 78.0     # ~4.7 km/h, unhurried adult
MOBILITY_WALK_SPEED: Final[dict[str, float]] = {
    "none": 1.0, "mild": 0.85, "moderate": 0.7, "severe": 0.55,
}
BOARD_PENALTY_MIN: Final = 1.0          # dwell plus boarding, per boarding
TRANSFER_PENALTY_MIN: Final = 4.0       # walk between berths plus the second wait

# ------------------------------------------------------------------ F3 severity
SEVERE_WALK_MULTIPLIER: Final = 1.5     # walk_m > max_walk_m x this -> HIGH
MODERATE_JOURNEY_DELTA: Final = 0.50    # journey time up by more than this -> MODERATE

# ------------------------------------------------------------------ G1 adaptation logistic
#: The one stochastic component in the deterministic layer. G3: assumptions, exposed here
#: so calibration can test them, and so the write-up can say how wrong they were.
BETA: Final[dict[str, float]] = {
    "intercept": -2.30,
    "journey_delta": 2.60,      # per unit of normalised journey-time increase
    "transfers": 0.85,          # per added transfer
    "walk_ratio": 1.40,         # per unit of walk_m / max_walk_m
    "tolerance": 2.10,          # subtracted; a tolerant person adapts less
    "car_access": 0.95,         # subtracted; a car makes switching easy, not abandoning
}
#: given the person adapts, how they split. A car makes switching the likely branch.
P_SWITCH_GIVEN_CAR: Final = 0.80
P_SWITCH_GIVEN_NO_CAR: Final = 0.15

# ------------------------------------------------------------------ C4 behavioural draws
#: (mean, sd) for the three 0-1 scalars. The least defensible numbers in the system, and
#: the first ones calibration adjusts (C4).
BEHAVIOUR_DIST: Final[dict[str, tuple[float, float]]] = {
    "inconvenience_tolerance": (0.50, 0.20),
    "switching_propensity": (0.45, 0.22),
    "baseline_trust": (0.58, 0.18),
}

# ------------------------------------------------------------------ D4 conditional edges
#: P(NEEDS -> Polyclinic) by age band. The gradient is what makes the 65+ cohort
#: structurally exposed to a stop removal, which is what produces the headline finding.
CLINIC_NEED_BY_AGE: Final[dict[str, float]] = {
    "<18": 0.04, "18-34": 0.06, "35-54": 0.14, "55-64": 0.34, "65-74": 0.62, "75+": 0.86,
}

#: P(mobility limitation) by age band, as (mild, moderate, severe). Remainder is "none".
MOBILITY_BY_AGE: Final[dict[str, tuple[float, float, float]]] = {
    "<18":   (0.02, 0.01, 0.00),
    "18-34": (0.03, 0.01, 0.00),
    "35-54": (0.07, 0.02, 0.01),
    "55-64": (0.16, 0.06, 0.02),
    "65-74": (0.28, 0.13, 0.05),
    "75+":   (0.34, 0.24, 0.13),
}

AGE_BANDS: Final = ("<18", "18-34", "35-54", "55-64", "65-74", "75+")
#: Singapore-shaped, declared synthetic. M1 would replace this with SingStat figures.
AGE_DISTRIBUTION: Final[dict[str, float]] = {
    "<18": 0.16, "18-34": 0.22, "35-54": 0.27, "55-64": 0.14, "65-74": 0.13, "75+": 0.08,
}
