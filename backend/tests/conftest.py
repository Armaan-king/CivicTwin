"""Test-wide fixtures.

The deliberation cache is keyed on prompt version, model name and prompt text -- but not
on the *behaviour* of whatever produced the answer. Two different stubs called "stub"
therefore share entries, so changing a stub silently replays the old one's output and the
failure appears in an unrelated assertion. That cost a confusing debugging detour, so the
suite gets its own cache directory per session and the project's real one is never
touched by a test.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True, scope="session")
def isolated_deliberation_cache(tmp_path_factory):
    from app import deliberate

    original = deliberate.CACHE
    deliberate.CACHE = tmp_path_factory.mktemp("deliberation_cache")

    # Session scope, because a module-scoped fixture elsewhere in the suite runs before
    # any function-scoped one and would otherwise execute under the demo's settings.
    # `DELIBERATION_REPLAY_ONLY=1` lives in `.env` so a demo cannot accidentally call the
    # model, and `app.config` loads `.env` on import -- so the suite silently inherited it
    # and every test expecting a stub to be called broke at once.
    replay = deliberate.REPLAY_ONLY
    deliberate.REPLAY_ONLY = False

    yield deliberate.CACHE

    deliberate.CACHE = original
    deliberate.REPLAY_ONLY = replay


@pytest.fixture(autouse=True)
def isolated_llm_cache(tmp_path, monkeypatch):
    """Per test, not per session.

    Every structured call is now cached on (model, system, prompt), and test doubles all
    call themselves "canned" or "stub" while returning different answers -- so a shared
    cache has one test replaying another's result. That surfaced as `assert 7 == 3` in a
    test that had nothing to do with caching.
    """
    from app.services import llm

    monkeypatch.setattr(llm, "LLM_CACHE", tmp_path / "llm_cache")

