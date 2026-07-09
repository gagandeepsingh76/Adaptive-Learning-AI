"""OpenRouter generation adapter tests without network access."""

import json
from collections.abc import Mapping, Sequence
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from openai import APIStatusError

from app.ai.openrouter import OPENROUTER_BASE_URL, OpenRouterProvider
from app.core.interfaces.ai import GenerationRequest
from app.exceptions import LLMProviderClientError
from app.schemas.ai_outputs import GeneratedRoadmap


class FakeChatCompletions:
    def __init__(self) -> None:
        self.params: dict[str, Any] | None = None

    async def create(self, **params: Any) -> Any:
        self.params = params
        assert params["model"] == "openai/gpt-4.1-mini"
        assert params["messages"][-1] == {"role": "user", "content": "prompt"}
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"ok":true}'),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=7, completion_tokens=3, total_tokens=10),
        )


async def test_openrouter_provider_normalizes_usage_and_json_config(
    ai_settings: Any,
) -> None:
    completions = FakeChatCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = OpenRouterProvider("", ai_settings, client=client)

    result = await provider.generate(
        GenerationRequest(prompt="prompt", response_schema={"type": "object"})
    )

    assert result.text == '{"ok":true}'
    assert result.usage.total_tokens == 10
    params = completions.params
    assert params is not None
    assert params["response_format"] == {"type": "json_object"}
    assert "<response_schema>" in params["messages"][0]["content"]


async def test_openrouter_provider_sends_full_response_schema(ai_settings: Any) -> None:
    completions = FakeChatCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = OpenRouterProvider("", ai_settings, client=client)

    await provider.generate(
        GenerationRequest(prompt="prompt", response_schema=GeneratedRoadmap.model_json_schema())
    )

    params = completions.params
    assert params is not None
    system_instruction = params["messages"][0]["content"]
    assert isinstance(system_instruction, str)
    encoded = system_instruction
    assert '"skills":{"items":{"$ref":"#/$defs/GeneratedSkill"},"maxItems":30' in encoded
    assert "GeneratedSubtask" in encoded
    assert _schema_contains_any(
        json.loads(encoded.split("<response_schema>", 1)[1].split("</response_schema>", 1)[0]),
        {
            "additionalProperties",
            "exclusiveMaximum",
            "exclusiveMinimum",
            "maxItems",
            "maxLength",
            "maximum",
            "minItems",
            "minLength",
            "minimum",
            "title",
        },
    )


class FailingChatCompletions:
    async def create(self, **params: Any) -> Any:
        assert params["model"] == "openai/gpt-4.1-mini"
        assert params["messages"][-1] == {"role": "user", "content": "prompt"}
        body = {
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "API key not valid for this OpenRouter model.",
            }
        }
        response = httpx.Response(
            403,
            json=body,
            request=httpx.Request("POST", f"{OPENROUTER_BASE_URL}/chat/completions"),
        )
        raise APIStatusError("OpenRouter request failed", response=response, body=body)


async def test_openrouter_provider_exposes_complete_client_error(
    ai_settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[tuple[str, dict[str, Any]]] = []

    def capture_warning(event: str, **kwargs: Any) -> None:
        events.append((event, kwargs))

    monkeypatch.setattr("app.ai.openrouter.logger.warning", capture_warning)
    client = SimpleNamespace(chat=SimpleNamespace(completions=FailingChatCompletions()))
    provider = OpenRouterProvider("", ai_settings, client=client)

    with pytest.raises(LLMProviderClientError) as raised:
        await provider.generate(GenerationRequest(prompt="prompt"))

    error = raised.value
    assert error.status_code == 403
    assert error.code == "OPENROUTER_PERMISSION_DENIED"
    assert error.retryable is False
    assert error.message == (
        "OpenRouter request rejected: API key not valid for this OpenRouter model."
    )
    details = error.details
    assert details is not None
    assert details["http_status"] == 403
    assert details["openrouter_error_code"] == "PERMISSION_DENIED"
    assert details["openrouter_error_message"] == (
        "API key not valid for this OpenRouter model."
    )
    assert details["response_body"]["error"]["code"] == "PERMISSION_DENIED"
    assert details["response_json"]["error"]["code"] == "PERMISSION_DENIED"
    assert details["api_key_configured"] is False

    assert events
    event, fields = events[0]
    assert event == "ai.generation.failed"
    assert fields["http_status"] == 403
    assert fields["openrouter_error_code"] == "PERMISSION_DENIED"
    assert fields["openrouter_error_message"] == (
        "API key not valid for this OpenRouter model."
    )
    assert fields["response_body"] == details["response_body"]
    assert fields["openrouter_client_error"]["response_json"] == details["response_json"]


def test_openrouter_provider_configures_openai_compatible_client(ai_settings: Any) -> None:
    provider = OpenRouterProvider("test-openrouter-key", ai_settings)

    assert provider._transport_diagnostics["api_key_configured"] is True
    assert provider._transport_diagnostics["base_url"] == OPENROUTER_BASE_URL
    assert str(provider._client.base_url).rstrip("/") == OPENROUTER_BASE_URL


def _schema_contains_any(value: Any, keys: set[str]) -> bool:
    if isinstance(value, Mapping):
        return any(key in keys or _schema_contains_any(item, keys) for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return any(_schema_contains_any(item, keys) for item in value)
    return False
