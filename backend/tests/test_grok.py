"""Exercise the OpenAI-shaped HTTP boundary without credentials or live calls."""
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.services.llm import ChatCompletion, LLMClient, LLMError, TELEMETRY, build_client


class Shape(BaseModel):
    value: int


def reply(content='{"value": 7}', finish_reason="stop"):
    return {"choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 5}}


def test_grok_request_validation_and_usage(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-only-key")
    monkeypatch.setenv("LLM_PROVIDER", "grok")
    monkeypatch.setenv("GROK_MODEL_ID", "test-model")
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs)
        assert url == "https://api.x.ai/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer test-only-key"
        assert kwargs["json"]["model"] == "test-model"
        assert kwargs["json"]["response_format"] == {"type": "json_object"}
        assert kwargs["json"]["max_tokens"] == 100
        assert kwargs["json"]["temperature"] == 0.8
        system = kwargs["json"]["messages"][0]["content"]
        assert system.startswith("Return JSON")
        assert '"value":' in system and '"type": "integer"' in system
        assert kwargs["timeout"] == 120.0
        # A bad schema must be retried; all consumed tokens must be counted.
        body = reply('{"value": "wrong"}' if len(calls) == 1 else '{"value": 7}')
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    llm = build_client(temperature=0.8)
    assert isinstance(llm.completion, ChatCompletion)
    assert llm.structured(Shape, "Return JSON", "go", max_tokens=100).value == 7
    assert len(calls) == 2
    usage = TELEMETRY.calls[-1]
    assert (usage.input_tokens, usage.output_tokens, usage.attempts) == (40, 10, 2)


def test_missing_key_never_calls_network(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("Unexpected network call"))
    with pytest.raises(LLMError, match="XAI_API_KEY"):
        LLMClient(ChatCompletion("test-model")).structured(Shape, "", "go")


@pytest.mark.parametrize("status", [401, 429, 500])
def test_api_errors_are_visible_and_do_not_echo_secrets(monkeypatch, status):
    monkeypatch.setenv("XAI_API_KEY", "test-only-secret")
    monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Response(
        status, text="test-only-secret", request=httpx.Request("POST", url)))
    with pytest.raises(LLMError, match=f"HTTP {status}") as error:
        ChatCompletion("test-model").complete("", "go", 10)
    assert "test-only-secret" not in str(error.value)


@pytest.mark.parametrize("body", [reply(finish_reason="length"), reply(content=None), {}])
def test_incomplete_responses_are_rejected(monkeypatch, body):
    monkeypatch.setenv("XAI_API_KEY", "test-only-key")
    monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Response(
        200, json=body, request=httpx.Request("POST", url)))
    with pytest.raises(LLMError, match="incomplete or invalid"):
        ChatCompletion("test-model").complete("", "go", 10)


def test_groq_is_a_different_provider_from_grok(monkeypatch):
    """Groq is not Grok. A key for one 401s on the other, so the branch must send the
    Groq key to the Groq host -- the mistake this test exists to catch."""
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-only-groq-key")
    monkeypatch.setenv("XAI_API_KEY", "test-only-xai-key")
    seen = {}

    def post(url, **kwargs):
        seen["url"] = url
        seen["auth"] = kwargs["headers"]["Authorization"]
        seen["model"] = kwargs["json"]["model"]
        return httpx.Response(200, json=reply(), request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    assert build_client().structured(Shape, "", "go").value == 7
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["auth"] == "Bearer test-only-groq-key"
    assert seen["model"] == "openai/gpt-oss-120b"


def test_unknown_provider_does_not_silently_become_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "grokk")
    with pytest.raises(LLMError, match="Unknown LLM_PROVIDER"):
        build_client()


@pytest.mark.parametrize("method,path", [("get", "/api/runs/demo/voices"),
                                         ("post", "/api/runs/demo/voices/stream")])
def test_voice_routes_explain_provider_failures(monkeypatch, method, path):
    from app import main

    def fail(_):
        raise LLMError("Grok needs XAI_API_KEY")

    monkeypatch.setattr(main, "get_deliberation", fail)
    response = getattr(TestClient(main.app), method)(path)
    assert response.status_code == 502
    assert "XAI_API_KEY" in response.json()["detail"]
