# LTA DataMall extract

| | |
|---|---|
| Source | https://datamall2.mytransport.sg/ltaodataservice |
| Endpoints | `BusStops`, `BusRoutes`, `BusServices` |
| Retrieved | 2026-09-02 04:44 UTC |
| Licence | Singapore Open Data Licence v1.0 |
| Fetched by | `scripts/fetch_lta.py` |

## What was trimmed

Bounding box 1.358-1.388 N, 103.832-103.862 E,
which is Ang Mo Kio plus a margin. Every service calling at a stop inside the box is
kept: 73 of them, discovered rather than listed by hand.

- `stops.json` 161 of 5208 stops nationwide
- `routes.json` 924 of 26881 route rows
- `services.json` 108 of 806 services

## What this is not

Real stop positions and real headways. It carries **no population data**: residents remain
synthetic and are labelled as such everywhere they are shown.
