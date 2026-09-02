"""The study area: blocks, roads, stops, two bus services, and the polyclinic.

Synthetic and declared as such (`AGENTS.md` §16). Coordinates are metres in a local plan
frame with the origin at the estate's north-west corner, which is also the frame the
frontend map draws in, so the engine and the picture can never disagree about where
anything is. **M1** would replace this module with LTA coordinates; nothing downstream
reads anything but `Stop.x/y` and `Service.stops`.

Two services, not one. A single line makes stop assignment trivial (walk to the next stop
along) and leaves `add_shuttle_feeder` and `reroute_feeder` with nothing to act on. The
feeder is what makes a transfer, and therefore `FRICTION_ADDED` and the transfer tolerance
in **C3**, mean anything.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.rng import derived_rng
from app.scenario import STUDY_AREA

BLOCK, ROAD = 64, 22
GRID_COLS, GRID_ROWS = 14, 9
SUBZONES = ("AMK Ave 3", "Cheng San", "Chong Boon", "Kebun Baru")
BUS_SPEED_M_PER_MIN = 340.0   # ~20 km/h in mixed traffic, dwell time counted separately

#: The plan frame is drawn in display units; the world is in metres. One unit is 2.6 m,
#: which puts the estate at roughly 3.1 x 2.0 km and bus stops 350 m apart, both about
#: right for Ang Mo Kio. Without this the whole estate fits inside one person's walking
#: range, every journey is a walk, and a bus policy cannot harm anybody.
METRES_PER_UNIT = 2.6


@dataclass
class Stop:
    stop_id: str
    x: float
    y: float
    name: str
    removed: bool = False

    @property
    def xy(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Service:
    service_id: str
    name: str
    headway_min: float
    #: stop ids in running order. Both directions are assumed symmetric in V1.
    stops: list[str] = field(default_factory=list)


@dataclass
class Geography:
    span: tuple[float, float]
    blocks: list[dict]
    roads: list[dict]
    stops: dict[str, Stop]
    services: dict[str, Service]
    polyclinic: tuple[float, float]
    #: stop ids from which the polyclinic is a short walk
    clinic_stops: list[str] = field(default_factory=list)

    def serving(self, stop_id: str) -> list[Service]:
        return [s for s in self.services.values() if stop_id in s.stops]


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Straight-line metres between two points given in display units.

    Local plan frame, so no haversine is needed at this scale. Every consumer wants
    metres, so the unit conversion lives here and nowhere else.
    """
    return math.hypot(a[0] - b[0], a[1] - b[1]) * METRES_PER_UNIT


def build_geography() -> Geography:
    rng = derived_rng("geography")

    # subzones occupy contiguous bands of the grid, the way estates actually do
    per = GRID_COLS // len(SUBZONES) + 1
    bands = {z: range(i * per, min((i + 1) * per, GRID_COLS)) for i, z in enumerate(SUBZONES)}

    blocks = []
    for zone, cols in bands.items():
        for cx in cols:
            for ry in range(GRID_ROWS):
                if rng.random() < 0.12:          # a park, a carpark, a school field
                    continue
                blocks.append({
                    "block_id": f"b_{cx:02d}_{ry:02d}",
                    "subzone": zone,
                    "x": cx * (BLOCK + ROAD),
                    "y": ry * (BLOCK + ROAD),
                    "w": BLOCK - rng.choice([0, 0, 8, 14]),
                    "h": BLOCK - rng.choice([0, 0, 8, 14]),
                    "storeys": rng.choice([8, 10, 10, 12, 12, 14, 16, 18]),
                    "population": 0,
                })

    span_x = GRID_COLS * (BLOCK + ROAD)
    span_y = GRID_ROWS * (BLOCK + ROAD)

    roads = [{"x1": c * (BLOCK + ROAD) - ROAD / 2, "y1": 0,
              "x2": c * (BLOCK + ROAD) - ROAD / 2, "y2": span_y, "kind": "minor"}
             for c in range(GRID_COLS + 1)]
    roads += [{"x1": 0, "y1": r * (BLOCK + ROAD) - ROAD / 2,
               "x2": span_x, "y2": r * (BLOCK + ROAD) - ROAD / 2, "kind": "minor"}
              for r in range(GRID_ROWS + 1)]

    corridor_y = 3 * (BLOCK + ROAD) - ROAD / 2
    roads.append({"x1": 0, "y1": corridor_y, "x2": span_x, "y2": corridor_y, "kind": "arterial"})

    # ---------------------------------------------------------------- the trunk, service 265
    trunk_ids = ["55007", "55021", "55039", "55079", "55081", "55101", "55119", "55139", "55161"]
    trunk_names = ["Interchange", "Ave 1", "Ave 2", "Ang Mo Kio Ave 3", "Blk 226",
                   "Ave 5", "Ave 6", "Ave 8", "Ave 10"]
    stops: dict[str, Stop] = {}
    for i, (sid, name) in enumerate(zip(trunk_ids, trunk_names)):
        stops[sid] = Stop(sid, round(70 + i * (span_x - 140) / 8, 1), corridor_y, name)

    # ---------------------------------------------------------------- the feeder, service 162
    # an interior loop running deeper into the estate, returning to the interchange.
    feeder_y = 6 * (BLOCK + ROAD) - ROAD / 2
    feeder_ids = ["55203", "55211", "55229", "55237", "55251", "55263"]
    feeder_names = ["Cheng San Mkt", "Blk 411", "Chong Boon Sec", "Polyclinic",
                    "Blk 560", "Kebun Baru CC"]
    for i, (sid, name) in enumerate(zip(feeder_ids, feeder_names)):
        stops[sid] = Stop(sid, round(120 + i * (span_x - 260) / 5, 1), feeder_y, name)

    services = {
        "265": Service("265", "265 Trunk", headway_min=8.0, stops=trunk_ids),
        # begins and ends at the interchange, so a transfer is always available there
        "162": Service("162", "162 Feeder", headway_min=12.0,
                       stops=["55007", *feeder_ids, "55007"]),
    }

    clinic_stop = stops["55237"]
    polyclinic = (clinic_stop.x + 15.0, clinic_stop.y + 34.0)
    #: the feeder stop outside it, and the trunk stop up the road
    clinic_stops = ["55237", "55101"]

    return Geography(
        span=(span_x, span_y), blocks=blocks, roads=roads, stops=stops,
        services=services, polyclinic=polyclinic, clinic_stops=clinic_stops,
    )


def display_dict(geo: Geography) -> dict:
    """The shape the frontend map reads. Display only; no rule consults it."""
    return {
        "study_area": STUDY_AREA,
        "span": list(geo.span),
        "blocks": geo.blocks,
        "roads": geo.roads,
        "stops": [{"stop_id": s.stop_id, "x": s.x, "y": s.y,
                   "removed": s.removed, "name": s.name} for s in geo.stops.values()],
        "route": [[geo.stops[i].x, geo.stops[i].y] for i in geo.services["265"].stops],
        "feeder": [[geo.stops[i].x, geo.stops[i].y] for i in geo.services["162"].stops],
        "polyclinic": {"x": geo.polyclinic[0], "y": geo.polyclinic[1]},
    }
