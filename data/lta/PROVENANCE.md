# LTA DataMall extract

| | |
|---|---|
| Source | https://datamall2.mytransport.sg/ltaodataservice |
| Endpoints | `BusStops`, `BusRoutes`, `BusServices` |
| Retrieved | 2026-09-02 04:33 UTC |
| Licence | Singapore Open Data Licence v1.0 |
| Fetched by | `scripts/fetch_lta.py` |

## What was trimmed

Bounding box 1.355-1.395 N, 103.83-103.87 E,
which is Ang Mo Kio plus a margin. Every service calling at a stop inside the box is
kept: 89 of them, discovered rather than listed by hand.

- `stops.json` 244 of 5208 stops nationwide
- `routes.json` 1390 of 26881 route rows
- `services.json` 131 of 806 services

## What this is not

Real stop positions and real headways. It carries **no population data**: residents remain
synthetic and are labelled as such everywhere they are shown.
