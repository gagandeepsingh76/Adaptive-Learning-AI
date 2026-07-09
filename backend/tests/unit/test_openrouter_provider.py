"""OpenRouter generation adapter tests without network access."""

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
    def __init__(
        self,
        *,
        expected_model: str = "openai/gpt-4.1-mini",
        expected_prompt: str = "prompt",
    ) -> None:
        self.params: dict[str, Any] | None = None
        self.expected_model = expected_model
        self.expected_prompt = expected_prompt

    async def create(self, **params: Any) -> Any:
        self.params = params
        assert params["model"] == self.expected_model
        assert params["messages"][-1] == {"role": "user", "content": self.expected_prompt}
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
    assert params["extra_body"] == {"provider": {"require_parameters": True}}
    assert params["response_format"] == {"type": "json_object"}
    assert "json_schema" not in params["response_format"]
    system_instruction = params["messages"][0]["content"]
    assert "<response_schema>" not in system_instruction
    assert "validate the JSON locally" in system_instruction


async def test_openrouter_provider_does_not_send_json_schema_for_gemini_roadmap(
    ai_settings: Any,
) -> None:
    completions = FakeChatCompletions(expected_model="google/gemini-2.5-flash")
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = OpenRouterProvider("", ai_settings, client=client)

    await provider.generate(
        GenerationRequest(
            prompt="prompt",
            model="google/gemini-2.5-flash",
            prompt_id="roadmap/v1",
            response_schema=GeneratedRoadmap.model_json_schema(),
        )
    )

    params = completions.params
    assert params is not None
    assert params["response_format"] == {"type": "json_object"}
    assert "json_schema" not in params["response_format"]
    assert "schema" not in params["response_format"]
    system_instruction = params["messages"][0]["content"]
    assert isinstance(system_instruction, str)
    assert "<response_schema>" not in system_instruction
    assert "$defs" not in system_instruction
    assert "GeneratedSubtask" not in system_instruction


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
