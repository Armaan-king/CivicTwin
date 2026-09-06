"""Write a run to data/fixtures/demo_run.json.

The file is **engine output**, not a hand-authored stand-in. It exists so the frontend can
run with no backend process, which is what makes the demo survive a bad network, and so a
diff shows when a change to the rules moves a number.

    python scripts/dump_run.py

This replaces the old make_fixture.py, which asserted numbers the engine now computes.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.engine import build_run  # noqa: E402
from app.schemas.run import SimulationRun  # noqa: E402

OUT = ROOT / "data" / "fixtures" / "demo_run.json"

if __name__ == "__main__":
    raw = build_run()
    # validated before it is written, so a bad fixture can never reach the frontend
    run = SimulationRun.model_validate(raw)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(raw, indent=1), encoding="utf-8")
    m = run.metrics.overall
    second = sum(1 for o in run.outcomes if o.second_order)
    print(f"wrote {OUT.name}: {len(run.personas)} personas, {len(run.events)} events, "
          f"{m.severe_harm_count} severely harmed ({second} through a dependency), "
          f"mean journey {m.avg_journey_time_delta:+.2f} min")
