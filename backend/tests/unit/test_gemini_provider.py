"""Gemini generation adapter tests without network access."""

import json
from collections.abc import Mapping, Sequence
from types import SimpleNamespace
from typing import Any

import pytest
from google.genai.errors import ClientError

from app.ai.gemini import GeminiProvider
from app.core.interfaces.ai import GenerationRequest
from app.exceptions import LLMProviderClientError
from app.schemas.ai_outputs import GeneratedRoadmap


class FakeModels:
    def __init__(self) -> None:
        self.config: Any = None

    async def generate_content(self, *, model: str, contents: str, config: Any) -> Any:
        self.config = config
        assert model == "gemini-2.5-flash"
        assert contents == "prompt"
        return SimpleNamespace(
            text='{"ok":true}',
            usage_metadata=SimpleNamespace(
                prompt_token_count=7, candidates_token_count=3, total_token_count=10
            ),
            candidates=[SimpleNamespace(finish_reason=SimpleNamespace(value="STOP"))],
        )


async def test_gemini_provider_normalizes_usage_and_json_config(ai_settings: Any) -> None:
    models = FakeModels()
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    provider = GeminiProvider("", ai_settings, client=client)

    result = await provider.generate(
        GenerationRequest(prompt="prompt", response_schema={"type": "object"})
    )

    assert result.text == '{"ok":true}'
    assert result.usage.total_tokens == 10
    config = models.config
    assert config is not None
    assert config.response_mime_type == "application/json"


async def test_gemini_provider_simplifies_large_response_schema(ai_settings: Any) -> None:
    models = FakeModels()
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    provider = GeminiProvider("", ai_settings, client=client)

    await provider.generate(
        GenerationRequest(prompt="prompt", response_schema=GeneratedRoadmap.model_json_schema())
    )

    config = models.config
    assert config is not None
    schema = config.response_json_schema
    assert isinstance(schema, dict)
    assert schema["properties"]["skills"]["items"]["$ref"] == "#/$defs/GeneratedSkill"
    encoded = json.dumps(schema)
    assert "GeneratedSubtask" in encoded
    assert not _schema_contains_any(
        schema,
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


class FailingModels:
    async def generate_content(self, *, model: str, contents: str, config: Any) -> Any:
        assert model == "gemini-2.5-flash"
        assert contents == "prompt"
        body = {
            "error": {
                "code": 403,
                "message": "API key not valid for this Gemini model.",
                "status": "PERMISSION_DENIED",
            }
        }
        raise ClientError(
            403,
            body,
            response=SimpleNamespace(
                text=(
                    '{"error":{"code":403,"message":"API key not valid for this '
                    'Gemini model.","status":"PERMISSION_DENIED"}}'
                )
            ),
        )


async def test_gemini_provider_exposes_complete_client_error(
    ai_settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[tuple[str, dict[str, Any]]] = []

    def capture_warning(event: str, **kwargs: Any) -> None:
        events.append((event, kwargs))

    monkeypatch.setattr("app.ai.gemini.logger.warning", capture_warning)
    client = SimpleNamespace(aio=SimpleNamespace(models=FailingModels()))
    provider = GeminiProvider("", ai_settings, client=client)

    with pytest.raises(LLMProviderClientError) as raised:
        await provider.generate(GenerationRequest(prompt="prompt"))

    error = raised.value
    assert error.status_code == 403
    assert error.code == "GEMINI_PERMISSION_DENIED"
    assert error.retryable is False
    assert error.message == "Gemini request rejected: API key not valid for this Gemini model."
    details = error.details
    assert details is not None
    assert details["http_status"] == 403
    assert details["gemini_error_code"] == "PERMISSION_DENIED"
    assert details["gemini_error_message"] == "API key not valid for this Gemini model."
    assert details["response_body"] == (
        '{"error":{"code":403,"message":"API key not valid for this Gemini '
        'model.","status":"PERMISSION_DENIED"}}'
    )
    assert details["response_json"]["error"]["status"] == "PERMISSION_DENIED"
    assert details["api_key_sent"] is False

    assert events
    event, fields = events[0]
    assert event == "ai.generation.failed"
    assert fields["http_status"] == 403
    assert fields["gemini_error_code"] == "PERMISSION_DENIED"
    assert fields["gemini_error_message"] == "API key not valid for this Gemini model."
    assert fields["response_body"] == details["response_body"]
    assert fields["gemini_client_error"]["response_json"] == details["response_json"]


def test_gemini_provider_configures_sdk_api_key_header(ai_settings: Any) -> None:
    provider = GeminiProvider("test-gemini-key", ai_settings)

    assert provider._transport_diagnostics["api_key_configured"] is True
    assert provider._transport_diagnostics["api_key_client_present"] is True
    assert provider._transport_diagnostics["api_key_header_present"] is True
    assert provider._transport_diagnostics["api_key_sent"] is True


def _schema_contains_any(value: Any, keys: set[str]) -> bool:
    if isinstance(value, Mapping):
        return any(key in keys or _schema_contains_any(item, keys) for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return any(_schema_contains_any(item, keys) for item in value)
    return False
