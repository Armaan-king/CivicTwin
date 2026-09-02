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
STUDY_AREA: Final = "Ang Mo Kio"
POPULATION_SIZE: Final = 2000
ROUNDS: Final = 4  # 0..3, scenario-v1.md B1

# ------------------------------------------------------------------ C3 mobility mapping
#: metres a person will walk to a stop. A spec, not a hint: test_contract asserts it.
MAX_WALK_M: Final[dict[str, int]] = {"none": 1200, "mild": 800, "moderate": 500, "severe": 250}

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
