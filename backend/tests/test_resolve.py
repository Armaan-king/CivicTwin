"""The study-area guard, watched failing.

`resolve.py` exists because the engine used to read a town from an environment variable,
guess which stops to close, and generate a description to match -- so everything
downstream described a guess. Its refusal is the thing that stops that returning, and
until now nothing tested the refusal.
"""
from __future__ import annotations

import pytest

from app.resolve import StudyAreaNotFound, available_towns, resolve_study_area
from app.schemas.policy import PolicyChange


def policy(**mods) -> PolicyChange:
    return PolicyChange.model_validate({
        "objective": "test", "modifications": mods or {},
        "constraints": {}, "reading": [],
    })


def test_a_policy_naming_nowhere_is_refused_rather_than_defaulted():
    """The failure the module exists to prevent: a run against a silently-chosen town."""
    with pytest.raises(StudyAreaNotFound) as err:
        resolve_study_area(policy(), "Please improve the buses somewhere nice.")
    message = str(err.value)
    assert "names a stop or road we hold data for" in message
    # and it says where it looked, so the refusal is actionable
    for town in available_towns():
        assert town in message


def test_a_five_digit_stop_code_resolves_decisively():
    r = resolve_study_area(policy(remove_stops=["54231"]), "Close stop 54231.")
    assert r.town == "ang-mo-kio"
    assert "54231" in r.closures
    assert any("54231" in m for m in r.matched)


def test_a_road_name_resolves_the_town_without_inventing_closures():
    """Matching a road is enough to know where; it is not enough to know which stops.

    The distinction matters: a policy that names a road but no stop should resolve to a
    study area and close nothing, rather than have stops chosen for it.
    """
    r = resolve_study_area(policy(), "Something about Ang Mo Kio Avenue 3.")
    assert r.town == "ang-mo-kio"
    assert r.closures == set(), "a road name must not conjure closures"
    assert r.score > 0


def test_the_operators_abbreviations_are_spoken():
    """A planner writes 'Avenue'; LTA publishes 'Ave'. Without this the policy resolves to
    nowhere and is refused for naming a road it named correctly."""
    spelled = resolve_study_area(policy(), "Ang Mo Kio Avenue 3")
    abbreviated = resolve_study_area(policy(), "Ang Mo Kio Ave 3")
    assert spelled.town == abbreviated.town


def test_a_stop_that_matched_nothing_is_surfaced_not_dropped():
    r = resolve_study_area(policy(remove_stops=["54231", "99999"]),
                           "Close stops 54231 and 99999.")
    assert "54231" in r.closures
    assert "99999" in r.unmatched, "an unmatched request must be reported"


def test_the_towns_searched_are_recorded():
    r = resolve_study_area(policy(remove_stops=["54231"]), "Close stop 54231.")
    assert r.considered == available_towns()
