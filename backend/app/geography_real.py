"""Build the study area from the real LTA extract. W2, M1.

Produces the same `Geography` the synthetic builder does, so `graph.py`, `simulation.py`
and everything downstream cannot tell the difference. The only thing that changes is that
the numbers stop being ones I chose.

Three things come from the data rather than from a constant:

```text
stop positions   real lat/lon, projected to metres
ride times       the real cumulative Distance along each service, not a straight line
headways         the real AM-peak frequency band, e.g. "5-7" -> 6.0 min
```

What is still synthetic, and is labelled as such everywhere it is shown: **the residents**.
LTA publishes where the buses go, not who lives there. Households are placed against real
stop positions on the assumption that people in Ang Mo Kio live near a bus stop, which is
roughly how the estate was planned but is still an assumption.
"""
from __future__ import annotations

import json
import math
import pathlib
from collections import defaultdict

from app.geography import Geography, Service, Stop

DATA = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "lta"

#: Ang Mo Kio Community Hospital, Ave 9. Real, named in the source data, and the essential
#: destination for the V1 scenario. The polyclinic is not identifiable in the bus feed by
#: name, so it is not used rather than guessed at.
CLINIC_STOPS = ["55151", "55159"]

#: the two stops the V1 policy closes. Real codes on Ang Mo Kio Ave 3.
CLOSED_STOPS = {"54231", "54239"}

BUS_SPEED_M_PER_MIN = 340.0
#: fallback when a service publishes no frequency for the band
DEFAULT_HEADWAY_MIN = 12.0


def _project(lat: float, lon: float, lat0: float, lon0: float) -> tuple[float, float]:
    """Equirectangular metres from a local origin. Exact enough over 4 km."""
    x = (lon - lon0) * 111320.0 * math.cos(math.radians(lat0))
    y = (lat0 - lat) * 110540.0          # y grows southward, matching screen coordinates
    return (round(x, 1), round(y, 1))


def parse_headway(raw: str | None) -> float:
    """LTA publishes a band as a string: "5-7", "09-11", "-" when not running.

    The midpoint is the honest reading of a band. A missing or malformed value falls back
    to a declared default rather than to zero, because a zero headway silently makes a
    service infinitely attractive to the router.
    """
    if not raw or not raw.strip() or raw.strip() == "-":
        return DEFAULT_HEADWAY_MIN
    parts = [p for p in raw.replace(" ", "").split("-") if p.isdigit()]
    if not parts:
        return DEFAULT_HEADWAY_MIN
    values = [float(p) for p in parts]
    return round(sum(values) / len(values), 1)


def build_real_geography(closed: set[str] | None = None) -> Geography:
    """The real network. `closed` stops are dropped from every service that calls there."""
    closed = closed or set()
    raw_stops = json.loads((DATA / "stops.json").read_text(encoding="utf-8"))
    raw_routes = json.loads((DATA / "routes.json").read_text(encoding="utf-8"))
    raw_services = json.loads((DATA / "services.json").read_text(encoding="utf-8"))

    lat0 = max(float(s["Latitude"]) for s in raw_stops)
    lon0 = min(float(s["Longitude"]) for s in raw_stops)

    stops: dict[str, Stop] = {}
    for s in raw_stops:
        x, y = _project(float(s["Latitude"]), float(s["Longitude"]), lat0, lon0)
        stops[s["BusStopCode"]] = Stop(
            stop_id=s["BusStopCode"], x=x, y=y,
            name=s["Description"], removed=s["BusStopCode"] in closed,
        )

    # AM peak is the band the scenario is argued over, so it is the one modelled.
    headways = {}
    for s in raw_services:
        h = parse_headway(s.get("AM_Peak_Freq"))
        key = s["ServiceNo"]
        headways[key] = min(headways.get(key, h), h)

    #: real cumulative distance along each service, used for ride time between stops
    ordered: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for r in raw_routes:
        ordered[(r["ServiceNo"], r["Direction"])].append(r)

    services: dict[str, Service] = {}
    for (svc_no, direction), rows in ordered.items():
        rows.sort(key=lambda r: r["StopSequence"])
        seq = [r["BusStopCode"] for r in rows if r["BusStopCode"] in stops]
        if len(seq) < 2:
            continue
        sid = svc_no if direction == 1 else f"{svc_no}:{direction}"
        services[sid] = Service(sid, f"Service {svc_no}",
                                headways.get(svc_no, DEFAULT_HEADWAY_MIN), seq)

    #: real distance between consecutive stops on a service, in metres. A service that
    #: leaves the study area and comes back shows up here as a long hop, which is correct.
    distances: dict[tuple[str, str, str], float] = {}
    for (svc_no, direction), rows in ordered.items():
        sid = svc_no if direction == 1 else f"{svc_no}:{direction}"
        rows = [r for r in rows if r["BusStopCode"] in stops]
        for a, b in zip(rows, rows[1:]):
            gap = (float(b["Distance"]) - float(a["Distance"])) * 1000.0
            if gap > 0:
                distances[(sid, a["BusStopCode"], b["BusStopCode"])] = gap

    clinic = stops[CLINIC_STOPS[0]]
    geo = Geography(
        span=(max(s.x for s in stops.values()) + 100,
              max(s.y for s in stops.values()) + 100),
        blocks=[], roads=[], stops=stops, services=services,
        polyclinic=(clinic.x + 30.0, clinic.y + 40.0),
        clinic_stops=list(CLINIC_STOPS),
    )
    geo.ride_distances = distances       # type: ignore[attr-defined]
    return geo


def summarise(geo: Geography) -> str:
    hw = sorted(s.headway_min for s in geo.services.values())
    return (f"{len(geo.stops)} stops, {len(geo.services)} service directions, "
            f"headway median {hw[len(hw) // 2]:.1f} min, "
            f"span {geo.span[0] / 1000:.1f} x {geo.span[1] / 1000:.1f} km")
