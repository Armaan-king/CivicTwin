# LTA DataMall extract: bedok

| | |
|---|---|
| Source | https://datamall2.mytransport.sg/ltaodataservice |
| Endpoints | `BusStops`, `BusRoutes`, `BusServices` |
| Retrieved | 2026-09-02 04:55 UTC |
| Licence | Singapore Open Data Licence v1.0 |
| Fetched by | `scripts/fetch_lta.py` |

## What was trimmed

Town `bedok`, bounding box 1.316-1.342 N,
103.917-103.955 E. Every service calling at a stop inside the box is
kept: 81 of them, discovered rather than listed by hand.

- `stops.json` 181 of 5208 stops nationwide
- `routes.json` 1045 of 26881 route rows
- `services.json` 124 of 806 services

## What this is not

Real stop positions and real headways. It carries **no population data**: residents remain
synthetic and are labelled as such everywhere they are shown.
