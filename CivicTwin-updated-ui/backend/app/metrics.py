"""The six canonical metrics and the four subgroup axes. I1, I4.

Six, and no more. Every screen, every intervention ranking and every calibration row reads
from this one function, so a number shown in two places cannot disagree with itself.

`n` is never optional. A rate without a denominator is not a finding (`evaluation.md` §12),
and a 100% harm rate over three people has been the downfall of more dashboards than any
missing feature.

Four axes reported independently, no cross-tabs in V1 (**I4**). Cross-tabs on 2,000
personas produce cells of four people and invite exactly the over-reading the `n` rule
exists to prevent.
"""
from __future__ import annotations

from app.population import Population
from app.simulation import Outcome


def _p90(values: list[float]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.9))])


def metrics_for(outcomes: list[Outcome]) -> dict:
    """The six. Computed the same way for the whole run and for every cohort."""
    n = len(outcomes)
    if n == 0:
        return {"n": 0, "avg_journey_time_delta": 0.0, "severe_harm_count": 0,
                "severe_harm_rate": 0.0, "essential_trip_completion": None,
                "walk_distance_p90": 0}

    severe = sum(1 for o in outcomes if o.severity == "high")
    with_essential = [o for o in outcomes if o.essential_trips_total > 0]
    completion = None
    if with_essential:
        done = sum(o.essential_trips_completed for o in with_essential)
        total = sum(o.essential_trips_total for o in with_essential)
        completion = round(done / total, 4) if total else None

    return {
        "n": n,
        "avg_journey_time_delta": round(sum(o.journey_time_delta_min for o in outcomes) / n, 2),
        "severe_harm_count": severe,
        "severe_harm_rate": round(severe / n, 4),
        "essential_trip_completion": completion,
        "walk_distance_p90": _p90([float(o.walk_distance_m) for o in outcomes]),
    }


def subgroup_metrics(pop: Population, outcomes: dict[str, Outcome]) -> dict:
    """Four axes: age band, mobility level, home subzone, carer status.

    Carer status is the axis the product exists for. The other three are what a transport
    planner would already have looked at, which is what makes the fourth land.
    """
    by_id = pop.by_id()
    axes = {
        "age_band": lambda p: p.age_band,
        "mobility_level": lambda p: p.mobility_level,
        "home_subzone": lambda p: p.home_subzone,
        "is_caregiver": lambda p: str(p.is_caregiver),
    }
    out: dict[str, dict[str, dict]] = {}
    for name, key in axes.items():
        buckets: dict[str, list[Outcome]] = {}
        for pid, o in outcomes.items():
            buckets.setdefault(key(by_id[pid]), []).append(o)
        out[name] = {k: metrics_for(v) for k, v in sorted(buckets.items())}
    return out


def disparity_pp(subgroup: dict) -> float:
    """Widest severe-harm gap across any single axis, in percentage points.

    Cohorts under 30 are excluded: a gap driven by a cell of four is noise dressed as a
    finding, and the same n >= 30 floor governs calibration (**L2**).
    """
    widest = 0.0
    for axis in subgroup.values():
        rates = [m["severe_harm_rate"] for m in axis.values() if m["n"] >= 30]
        if len(rates) >= 2:
            widest = max(widest, max(rates) - min(rates))
    return round(widest * 100, 2)
