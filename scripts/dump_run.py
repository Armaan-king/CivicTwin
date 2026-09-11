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

import tempfile  # noqa: E402

from app import consultation  # noqa: E402
from app.engine import build_run  # noqa: E402
from app.schemas.run import SimulationRun  # noqa: E402

# Two destinations, one generator.
#
# `data/fixtures/` is the canonical artefact and what `check_fixture_contract.py` reads.
# `frontend/public/fixtures/` is what Vite actually serves to a browser in fixture mode,
# and nothing kept them in step: they had drifted by 26KB, so every offline demo was
# running on a stale run while the checked file said otherwise. Writing both from here
# means there is one command and one source of truth.
OUTS = [ROOT / "data" / "fixtures" / "demo_run.json",
        ROOT / "frontend" / "public" / "fixtures" / "demo_run.json"]

if __name__ == "__main__":
    # Build against an empty feedback store.
    #
    # `build_consultation` folds real form submissions in, which is right at runtime and
    # wrong here: the fixture is committed, and a file that changes every time somebody
    # uses the consultation page is not reproducible from the seed and cannot show, by
    # diff, that a rule moved a number. It also carries strangers' submissions into the
    # repository. `check_fixture_contract.py` already asserted every response is seeded;
    # regenerating after nine real replies had landed is what surfaced this.
    consultation.FEEDBACK = pathlib.Path(tempfile.mkdtemp(prefix="fixture-feedback-"))
    raw = build_run()
    # validated before it is written, so a bad fixture can never reach the frontend
    run = SimulationRun.model_validate(raw)
    body = json.dumps(raw, indent=1)
    for out in OUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
    m = run.metrics.overall
    second = sum(1 for o in run.outcomes if o.second_order)
    print("wrote " + ", ".join(str(o.relative_to(ROOT)) for o in OUTS))
    print(f"  {len(run.personas)} personas, {len(run.events)} events, "
          f"{m.severe_harm_count} severely harmed ({second} through a dependency), "
          f"mean journey {m.avg_journey_time_delta:+.2f} min")
