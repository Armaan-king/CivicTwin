"""Pull real Ang Mo Kio bus data from LTA DataMall into data/lta/. W2, M1.

Run once. The demo never runs it; it reads the trimmed files this writes.

    # get a free key by email: https://datamall.lta.gov.sg/content/datamall/en/request-for-api.html
    export LTA_ACCOUNT_KEY=...
    python scripts/fetch_lta.py            # defaults to ang-mo-kio
    python scripts/fetch_lta.py bedok      # any town in TOWNS

**This script does not trust field names, including the ones in our own docs.** It prints
what the API actually returned before filtering, because `AGENTS.md` W2 says to verify
against current docs rather than our specs, and a silently-renamed field would show up as
an empty study area rather than an error.

Nothing here is committed until it has a provenance file next to it: source URL, retrieval
date, licence, and exactly what was trimmed (`AGENTS.md` §16).
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = "https://datamall2.mytransport.sg/ltaodataservice"
DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "lta"

#: Towns, by bounding box. The LTA feed is national, so a town is a box over it and
#: nothing more; adding one is a line here and a re-fetch.
#:
#: Each box is drawn wide enough to keep the interchange and the stops just outside the
#: estate that people really transfer at, and tight enough to exclude the neighbouring
#: town. A generous Ang Mo Kio box put 45 synthetic residents on Sengkang West Road, four
#: kilometres away, and then reported them as an Ang Mo Kio cohort.
TOWNS: dict[str, dict[str, float]] = {
    "ang-mo-kio": {"lat_min": 1.358, "lat_max": 1.388, "lon_min": 103.832, "lon_max": 103.862},
    "bedok":      {"lat_min": 1.316, "lat_max": 1.342, "lon_min": 103.917, "lon_max": 103.955},
    "jurong-west": {"lat_min": 1.334, "lat_max": 1.365, "lon_min": 103.688, "lon_max": 103.730},
    "tampines":   {"lat_min": 1.340, "lat_max": 1.368, "lon_min": 103.928, "lon_max": 103.968},
    "woodlands":  {"lat_min": 1.424, "lat_max": 1.452, "lon_min": 103.775, "lon_max": 103.812},
}

#: Services are **discovered**, not listed. Picking them by name left 119 of 244 stops
#: with no service attached, so the router treated them as unusable and overstated harm.
#: Any service that calls at a stop inside the box is part of this network.


def fetch_all(endpoint: str, cap: int = 60000) -> list[dict]:
    """DataMall pages 500 records at a time via $skip. Stop at a short page."""
    key = os.environ.get("LTA_ACCOUNT_KEY")
    if not key:
        sys.exit(
            "LTA_ACCOUNT_KEY is not set.\n"
            "  Request a free key: "
            "https://datamall.lta.gov.sg/content/datamall/en/request-for-api.html\n"
            "  Then: export LTA_ACCOUNT_KEY=your-key   (or put it in .env)"
        )

    records: list[dict] = []
    skip = 0
    while len(records) < cap:
        req = urllib.request.Request(
            f"{BASE}/{endpoint}?$skip={skip}",
            headers={"AccountKey": key, "accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                page = json.loads(resp.read()).get("value", [])
        except urllib.error.HTTPError as exc:
            sys.exit(f"{endpoint} returned HTTP {exc.code}: {exc.read()[:200]!r}")
        except urllib.error.URLError as exc:
            sys.exit(f"could not reach DataMall: {exc.reason}")

        records.extend(page)
        print(f"  {endpoint}: {len(records)} records", end="\r")
        if len(page) < 500:
            break
        skip += 500
    print()
    return records


def report_fields(name: str, records: list[dict]) -> None:
    """Print what actually came back. Do not skip reading this."""
    if not records:
        print(f"  {name}: EMPTY -- the endpoint or the key is wrong")
        return
    print(f"  {name}: {len(records)} records, fields = {sorted(records[0])}")


def in_bbox(rec: dict, bbox: dict[str, float]) -> bool:
    try:
        lat, lon = float(rec.get("Latitude", 0)), float(rec.get("Longitude", 0))
    except (TypeError, ValueError):
        return False
    return (bbox["lat_min"] <= lat <= bbox["lat_max"]
            and bbox["lon_min"] <= lon <= bbox["lon_max"])


def main() -> None:
    town = sys.argv[1] if len(sys.argv) > 1 else "ang-mo-kio"
    if town not in TOWNS:
        known = ", ".join(sorted(TOWNS))
        sys.exit(f"unknown town {town!r}. Known: {known}\n"
                 f"  Add one by putting its bounding box in TOWNS.")
    bbox = TOWNS[town]
    out = DATA / town
    out.mkdir(parents=True, exist_ok=True)
    print(f"fetching {town} from LTA DataMall")

    stops = fetch_all("BusStops")
    routes = fetch_all("BusRoutes")
    services = fetch_all("BusServices")

    print("\nwhat the API actually returned:")
    for name, recs in (("BusStops", stops), ("BusRoutes", routes), ("BusServices", services)):
        report_fields(name, recs)

    local_stops = [s for s in stops if in_bbox(s, bbox)]
    local_codes = {s.get("BusStopCode") for s in local_stops}
    #: every service that calls anywhere inside the box
    local_service_nos = {r["ServiceNo"] for r in routes if r.get("BusStopCode") in local_codes}
    local_routes = [r for r in routes
                    if r.get("ServiceNo") in local_service_nos
                    and r.get("BusStopCode") in local_codes]
    local_services = [s for s in services if s.get("ServiceNo") in local_service_nos]

    print(f"\ntrimmed to the study area:")
    print(f"  stops    {len(local_stops):5d} of {len(stops)}")
    print(f"  routes   {len(local_routes):5d} of {len(routes)}")
    print(f"  services {len(local_service_nos):5d} discovered: "
          f"{' '.join(sorted(local_service_nos))}")
    unserved = local_codes - {r['BusStopCode'] for r in local_routes}
    print(f"  stops with no service calling: {len(unserved)} "
          f"(these are unusable to the router, so this number should be small)")
    print(f"  services {len(local_services):5d} of {len(services)}")

    if not local_stops:
        sys.exit("\nNo stops inside the bounding box. Check the field names printed above "
                 "before adjusting BBOX -- an empty result usually means Latitude and "
                 "Longitude are named something else now.")

    (out / "stops.json").write_text(json.dumps(local_stops, indent=1), encoding="utf-8")
    (out / "routes.json").write_text(json.dumps(local_routes, indent=1), encoding="utf-8")
    (out / "services.json").write_text(json.dumps(local_services, indent=1), encoding="utf-8")

    (out / "PROVENANCE.md").write_text(
        f"""# LTA DataMall extract: {town}

| | |
|---|---|
| Source | https://datamall2.mytransport.sg/ltaodataservice |
| Endpoints | `BusStops`, `BusRoutes`, `BusServices` |
| Retrieved | {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC |
| Licence | Singapore Open Data Licence v1.0 |
| Fetched by | `scripts/fetch_lta.py` |

## What was trimmed

Town `{town}`, bounding box {bbox["lat_min"]}-{bbox["lat_max"]} N,
{bbox["lon_min"]}-{bbox["lon_max"]} E. Every service calling at a stop inside the box is
kept: {len(local_service_nos)} of them, discovered rather than listed by hand.

- `stops.json` {len(local_stops)} of {len(stops)} stops nationwide
- `routes.json` {len(local_routes)} of {len(routes)} route rows
- `services.json` {len(local_services)} of {len(services)} services

## What this is not

Real stop positions and real headways. It carries **no population data**: residents remain
synthetic and are labelled as such everywhere they are shown.
""",
        encoding="utf-8",
    )
    print(f"\nwrote {OUT}/ with PROVENANCE.md")
    print("next: read PROVENANCE.md and the field lists above before wiring any of it in")


if __name__ == "__main__":
    main()
