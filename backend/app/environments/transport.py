"""Public transport: the one environment implemented in V1.

Everything here is the domain's clothing over the neutral core. The mechanism, the
severity rules, the dependency propagation and the audit all live in the core; this
supplies what a bus rider's constraints are and what the domain calls each event.
"""
from __future__ import annotations

from app.environments.base import register

WALK_SPEED_M_PER_MIN = 78          # ~4.7 km/h, an older resident on a covered walkway
BASE_WALK_M = 380
DETOUR_FACTOR = 1.35               # straight line to walkable distance. F1.2, declared.


class Transport:
    name = "transport"

    #: the neutral vocabulary, in the words a transport planner uses
    event_labels = {
        "PATH_UNAVAILABLE": "route no longer serves them",
        "EFFORT_INCREASED": "walk to the stop lengthened",
        "FRICTION_ADDED": "an extra transfer appeared",
        "DURATION_INCREASED": "journey time rose",
        "THRESHOLD_EXCEEDED": "walk passed what they can manage",
        "ESSENTIAL_ACCESS_LOST": "the polyclinic became unreachable",
        "DEPENDENCY_ABSORBED": "a household member took over the journey",
        "OBLIGATION_MISSED": "they arrived after their shift started",
        "SERVICE_ABANDONED": "they stopped making the trip",
    }

    #: capacity displacement is reachable here only via the reroute alternative;
    #: F2 defers crowding, so the baseline cannot produce it.
    patterns = ("threshold_cliff", "dependency_cascade",
                "capacity_displacement", "participation_gap")

    def persona_fields(self):
        return {
            "mobility_level": str,
            "max_walk_m": int,
            "transfer_tolerance": int,
            "has_car_access": bool,
            "needs_clinic": bool,
            "work_start_time": str,
        }

    def metric_names(self):
        return ("avg_journey_time_delta", "walk_distance_p90")

    def apply_policy(self, state: dict, policy: dict) -> dict:
        removed = set(policy.get("modifications", {}).get("remove_stops", []))
        return {**state, "removed_stops": removed}

    def evaluate(self, persona: dict, state: dict) -> dict:
        """Deterministic. Threshold rules only; no model call anywhere near this."""
        walk = state["walk_m"]
        limit = persona["max_walk_m"]
        severity, status = "none", "ok"
        if walk > limit * 1.5:
            severity, status = "high", "unreachable"
        elif walk > limit:
            severity, status = "moderate", "degraded"
        if persona.get("needs_clinic") and status == "unreachable":
            severity = "high"
        return {
            "severity": severity,
            "access_status": status,
            "walk_minutes": max(0.0, (walk - BASE_WALK_M) / WALK_SPEED_M_PER_MIN),
        }


TRANSPORT = register(Transport())
