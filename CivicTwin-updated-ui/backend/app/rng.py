"""Seeding, per decision G2.

    persona_seed = hash(scenario_seed, key)

Never one sequential stream. With a single RNG an intervention that changes how many
personas reach the abandonment check shifts every subsequent draw, so a measured
difference partly reflects reshuffled randomness rather than policy. Derived per-key seeds
mean persona 1847 draws the same numbers under every scenario, and the delta is causal.

Small implementation detail, large evaluation consequence, which is why it is one module
that everything else imports rather than a helper copied into three files.
"""
from __future__ import annotations

import hashlib
import random

from app.scenario import SCENARIO_SEED


def derived_rng(key: str, seed: int = SCENARIO_SEED) -> random.Random:
    """A stream that depends only on (seed, key), never on call order."""
    digest = hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))
