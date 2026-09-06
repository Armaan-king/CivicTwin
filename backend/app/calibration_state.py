"""Corrections a human has approved, and the record of every decision. L3 · LOCKED.

Calibration finds that the model over-predicted support somewhere, names the likely cause
from the consultation's own free text, and proposes a scoped correction. **It never applies
one itself.** A model that adjusts its own parameters because it was contradicted is a
model nobody can audit, so the proposal waits for a person and the decision is recorded
either way -- approved or rejected, with a timestamp and the error that prompted it.

What an approved correction changes is the *prediction*, not the world. `observed_support`
is what residents actually report and stays untouched; `predicted_support` is the model's
belief, and it is the thing that was wrong. Applying a correction narrows the gap between
them, which is exactly what calibration is measuring -- so the next run shows a smaller
error, and the history says why.

State is a single JSON file rather than a database. It holds a handful of decisions about
one scenario, and a file that a human can read and delete is the right size for that.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

STATE = pathlib.Path(__file__).resolve().parents[2] / "data" / "calibration_state.json"


@dataclass
class Decision:
    """One human ruling on one proposal."""
    parameter: str
    value: float
    approved: bool
    #: the signed error, in percentage points, that prompted the proposal
    prompted_by_error_pp: float
    cohort: str
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))


def _read() -> dict:
    if not STATE.exists():
        return {"applied": {}, "history": []}
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"applied": {}, "history": []}


def _write(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    tmp.replace(STATE)


def applied() -> dict[str, float]:
    """Corrections currently in force. Empty until a human approves one."""
    return dict(_read().get("applied", {}))


def history() -> list[dict]:
    """Every decision, approved or rejected. Retained either way (L3)."""
    return list(_read().get("history", []))


def record(decision: Decision) -> dict[str, float]:
    """Store a ruling and return the corrections now in force.

    A rejection is recorded as carefully as an approval. Knowing that a proposed change was
    put to someone and turned down is part of the audit trail, not an absence of one.
    """
    state = _read()
    state.setdefault("history", []).append(asdict(decision))
    live = state.setdefault("applied", {})
    if decision.approved:
        live[decision.parameter] = decision.value
    else:
        live.pop(decision.parameter, None)
    _write(state)
    return dict(live)


def clear() -> None:
    """Drop every correction. For tests, and for a demo that wants to start over."""
    _write({"applied": {}, "history": []})
