"""The one documented scale on which three different support signals are compared.

Three things in this system express "how much do you back this policy", and they were
born on different scales:

    predicted_support   1..5   the frozen logistic of L1, a Likert mean
    observed_support    1..5   what consultation respondents ticked, same Likert
    declared position   0..1   what a resident said during deliberation

Comparing them requires a stated conversion, not an implied one. `L2` reports signed error
in **percentage points**, which only means something if every input is on one scale first.
So everything is converted to a 0..1 *support fraction* here, in one place, with the
mapping written down:

    fraction = (likert - 1) / 4

    1 -> 0.00   strongly oppose
    2 -> 0.25
    3 -> 0.50   neutral
    4 -> 0.75
    5 -> 1.00   strongly support

The midpoint matters: a Likert 3 is 0.5, so "neutral" means the same thing in both
directions and a signed error keeps its sign. Dividing by 5 instead of mapping the
endpoints would put neutral at 0.6 and bias every comparison toward apparent opposition.

This is a presentation scale, not a claim that a Likert interval is metric. It is stated
so a reader can undo it.
"""
from __future__ import annotations

LIKERT_MIN = 1.0
LIKERT_MAX = 5.0


def likert_to_fraction(value: float) -> float:
    """1..5 Likert onto 0..1, endpoints anchored."""
    v = max(LIKERT_MIN, min(LIKERT_MAX, float(value)))
    return round((v - LIKERT_MIN) / (LIKERT_MAX - LIKERT_MIN), 4)


def fraction_to_likert(value: float) -> float:
    """0..1 back onto 1..5, for a screen that reports in the consultation's own units."""
    v = max(0.0, min(1.0, float(value)))
    return round(LIKERT_MIN + v * (LIKERT_MAX - LIKERT_MIN), 3)


def signed_error_pp(predicted_fraction: float, observed_fraction: float) -> float:
    """Percentage points, predicted minus observed. Positive means we overestimated.

    Signed rather than absolute, per L2: systematic overestimation among older residents
    is a different and more useful statement than "off by 19".
    """
    return round((predicted_fraction - observed_fraction) * 100, 2)


#: L2's flag threshold, in the same percentage points.
FLAG_PP = 10.0
