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
def isolated_feedback_store(tmp_path_factory):
    """Real consultation submissions go to a temp directory during the suite.

    `test_api` posts a feedback body to prove the endpoint accepts one. Once that
    endpoint actually persisted, the post started landing in the project's own
    `data/feedback/`, where the next run folded it into the consultation -- and two
    contract tests failed because a response had appeared with no persona behind it.

    The tests were right and the isolation was missing. A suite that writes into the
    data the product ships is not testing the product, it is editing it.
    """
    from app import consultation

    original = consultation.FEEDBACK
    consultation.FEEDBACK = tmp_path_factory.mktemp("feedback")
    yield
    consultation.FEEDBACK = original


@pytest.fixture(autouse=True, scope="session")
def no_throttle_pacing():
    """Remove the inter-batch pacing for the duration of the suite.

    `deliberate.PACE_SECONDS` exists because Bedrock throttles a real account, and a run
    that is refused pays the wait twice. A stub is not rate limited, so every second of
    that pacing in a test is a second spent proving nothing: adding it took the suite from
    40 seconds to over two minutes and it would have grown with every new deliberation
    test.

    Neutralised here rather than guarded inside `_pace`, for the same reason the cache is
    redirected here: production code should not carry branches whose only purpose is to
    behave differently when observed.
    """
    from app import deliberate

    original = deliberate.PACE_SECONDS
    deliberate.PACE_SECONDS = 0.0
    yield
    deliberate.PACE_SECONDS = original


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

