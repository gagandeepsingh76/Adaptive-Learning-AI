"""OpenRouter implementation of the provider-neutral LLM contract."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator, Mapping, Sequence
from importlib.metadata import PackageNotFoundError, version
from time import perf_counter
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from app.config.ai_settings import AISettings
from app.config.logging import get_logger
from app.core.interfaces.ai import (
    GenerationChunk,
    GenerationRequest,
    GenerationResult,
    LLMProvider,
    TokenUsage,
)
from app.core.interfaces.observability import (
    AICallMetric,
    AIObservabilitySink,
    NullAIObservabilitySink,
)
from app.exceptions import LLMProviderClientError, LLMProviderError
from app.utils.time import utc_now

logger = get_logger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_OPENROUTER_SCHEMA_NAME = re.compile(r"[^a-zA-Z0-9_-]+")


class OpenRouterProvider(LLMProvider):
    """OpenRouter chat-completions adapter with bounded retries and telemetry."""

    def __init__(
        self,
        api_key: str,
        settings: AISettings,
        observability: AIObservabilitySink | None = None,
        client: Any | None = None,
        base_url: str = OPENROUTER_BASE_URL,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("An OpenRouter API key is required")
        self._settings = settings
        self._sink = observability or NullAIObservabilitySink()
        self._client = client or AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._transport_diagnostics = _api_key_transport_diagnostics(api_key, base_url)

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate a complete response and normalize provider accounting."""
        model = request.model or self._settings.llm_model
        started = perf_counter()
        retry_count = 0
        try:
            async for attempt in self._retrying():
                retry_count = attempt.retry_state.attempt_number - 1
                with attempt:
                    async with asyncio.timeout(self._settings.generation_timeout_seconds):
                        response = await self._client.chat.completions.create(
                            **self._chat_completion_params(request, model)
                        )
            result = self._to_result(response, model, started, retry_count)
            await self._record(request, result, "success", None)
            return result
        except Exception as exc:
            latency_ms = (perf_counter() - started) * 1000
            await self._record_failure(request, model, latency_ms, retry_count, exc)
            if isinstance(exc, LLMProviderError):
                raise
            if isinstance(exc, APIStatusError):
                raise _provider_client_error(
                    exc, model=model, transport_diagnostics=self._transport_diagnostics
                ) from exc
            raise LLMProviderError(
                "OpenRouter generation failed.", details={"error_type": type(exc).__name__}
            ) from exc

    async def stream(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        """Stream normalized text chunks while retaining provider independence."""
        model = request.model or self._settings.llm_model
        started = perf_counter()
        usage = TokenUsage()
        try:
            async with asyncio.timeout(self._settings.generation_timeout_seconds):
                stream = await self._client.chat.completions.create(
                    **self._chat_completion_params(request, model),
                    stream=True,
                )
                async for chunk in stream:
                    text = self._extract_stream_text(chunk)
                    usage = self._usage(chunk) or usage
                    finish_reason = self._finish_reason(chunk)
                    if text or finish_reason:
                        yield GenerationChunk(text=text, finish_reason=finish_reason, usage=usage)
            result = GenerationResult(
                text="",
                model=model,
                usage=usage,
                latency_ms=(perf_counter() - started) * 1000,
                retry_count=0,
            )
            await self._record(request, result, "success", None)
        except Exception as exc:
            await self._record_failure(
                request, model, (perf_counter() - started) * 1000, 0, exc
            )
            if isinstance(exc, LLMProviderError):
                raise
            if isinstance(exc, APIStatusError):
                raise _provider_client_error(
                    exc, model=model, transport_diagnostics=self._transport_diagnostics
                ) from exc
            raise LLMProviderError(
                "OpenRouter streaming generation failed.",
                details={"error_type": type(exc).__name__},
            ) from exc

    def _chat_completion_params(self, request: GenerationRequest, model: str) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": model,
            "messages": _messages(request),
            "temperature": request.temperature
            if request.temperature is not None
            else self._settings.temperature,
            "top_p": request.top_p if request.top_p is not None else self._settings.top_p,
            "max_tokens": request.max_output_tokens
            if request.max_output_tokens is not None
            else self._settings.max_output_tokens,
        }
        if request.response_schema:
            params["response_format"] = _response_format(request)
            params["extra_body"] = {"provider": {"require_parameters": True}}
        return params

    def _to_result(
        self, response: Any, model: str, started: float, retry_count: int
    ) -> GenerationResult:
        text = self._extract_text(response)
        return GenerationResult(
            text=text,
            model=model,
            usage=self._usage(response),
            latency_ms=(perf_counter() - started) * 1000,
            retry_count=retry_count,
            finish_reason=self._finish_reason(response),
        )

    @staticmethod
    def _extract_text(response: Any, *, allow_empty: bool = False) -> str:
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise LLMProviderError("OpenRouter returned no response choices.")
        message = getattr(choices[0], "message", None)
        text = _content_to_text(getattr(message, "content", None))
        if not text and not allow_empty:
            raise LLMProviderError("OpenRouter returned an empty response.")
        return text

    @staticmethod
    def _extract_stream_text(chunk: Any) -> str:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            return ""
        delta = getattr(choices[0], "delta", None)
        return _content_to_text(getattr(delta, "content", None))

    @staticmethod
    def _usage(response: Any) -> TokenUsage:
        usage = getattr(response, "usage", None)
        if usage is None:
            return TokenUsage()
        return TokenUsage(
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            total_tokens=int(getattr(usage, "total_tokens", 0) or 0),
        )

    @staticmethod
    def _finish_reason(response: Any) -> str | None:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return None
        reason = getattr(choices[0], "finish_reason", None)
        return str(reason) if reason is not None else None

    def _retrying(self) -> AsyncRetrying:
        return AsyncRetrying(
            stop=stop_after_attempt(self._settings.max_attempts),
            wait=wait_exponential_jitter(initial=0.5, max=8),
            retry=retry_if_exception(_is_retryable_provider_error),
            reraise=True,
        )

    async def _record(
        self,
        request: GenerationRequest,
        result: GenerationResult,
        outcome: str,
        error_code: str | None,
    ) -> None:
        cost = (
            result.usage.input_tokens * self._settings.input_cost_per_million
            + result.usage.output_tokens * self._settings.output_cost_per_million
        ) / 1_000_000
        await self._sink.record(
            AICallMetric(
                occurred_at=utc_now(),
                operation="generation",
                provider="openrouter",
                model=result.model,
                latency_ms=result.latency_ms,
                request_id=request.request_id,
                roadmap_id=request.roadmap_id,
                prompt_id=request.prompt_id,
                prompt_version=request.prompt_version,
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
                estimated_cost=cost,
                retry_count=result.retry_count,
                outcome=outcome,
                error_code=error_code,
            )
        )

    async def _record_failure(
        self,
        request: GenerationRequest,
        model: str,
        latency_ms: float,
        retry_count: int,
        exc: Exception,
    ) -> None:
        log_fields: dict[str, Any] = {
            "model": model,
            "retry_count": retry_count,
            "error_type": type(exc).__name__,
        }
        if isinstance(exc, APIStatusError):
            diagnostic = _client_error_diagnostic(
                exc, model=model, transport_diagnostics=self._transport_diagnostics
            )
            log_fields.update(
                {
                    "http_status": diagnostic["http_status"],
                    "openrouter_error_code": diagnostic["openrouter_error_code"],
                    "openrouter_error_message": diagnostic["openrouter_error_message"],
                    "response_body": diagnostic["response_body"],
                    "sdk_version": diagnostic["sdk_version"],
                    "openrouter_client_error": diagnostic,
                }
            )
        logger.warning("ai.generation.failed", **log_fields)
        result = GenerationResult(
            text="", model=model, usage=TokenUsage(), latency_ms=latency_ms, retry_count=retry_count
        )
        await self._record(request, result, "failure", _metric_error_code(exc))


def _messages(request: GenerationRequest) -> list[dict[str, str]]:
    system_instruction = _system_instruction_with_schema(
        request.system_instruction, request.response_schema
    )
    messages: list[dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": request.prompt})
    return messages


def _system_instruction_with_schema(
    system_instruction: str | None, schema: Mapping[str, Any] | None
) -> str | None:
    if schema is None:
        return system_instruction
    schema_text = json.dumps(schema, separators=(",", ":"), sort_keys=True)
    schema_instruction = (
        "Return only one valid JSON object matching this response schema. "
        "Do not include markdown fences, prose, or undeclared top-level fields. "
        "The backend will enforce the full strict schema after generation.\n"
        f"<response_schema>{schema_text}</response_schema>"
    )
    if system_instruction:
        return f"{system_instruction}\n\n{schema_instruction}"
    return schema_instruction


def _response_format(request: GenerationRequest) -> dict[str, Any]:
    schema = request.response_schema
    if schema is None:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": _schema_name(request),
            "strict": True,
            "schema": _json_safe(schema),
        },
    }


def _schema_name(request: GenerationRequest) -> str:
    title = None
    if isinstance(request.response_schema, Mapping):
        title = request.response_schema.get("title")
    candidate = str(request.prompt_id or title or "structured_response")
    normalized = _OPENROUTER_SCHEMA_NAME.sub("_", candidate).strip("_")
    return (normalized or "structured_response")[:64]


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, Mapping):
        text = content.get("text") or content.get("content")
        return str(text) if text is not None else ""
    if isinstance(content, Sequence) and not isinstance(content, str | bytes | bytearray):
        parts = [_content_to_text(item) for item in content]
        return "".join(part for part in parts if part)
    return ""


def _is_retryable_provider_error(exc: BaseException) -> bool:
    if isinstance(
        exc,
        (
            TimeoutError,
            ConnectionError,
            asyncio.TimeoutError,
            APIConnectionError,
            APITimeoutError,
        ),
    ):
        return True
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return status_code == 429 or (isinstance(status_code, int) and status_code >= 500)


def _openai_version() -> str:
    try:
        return version("openai")
    except PackageNotFoundError:
        return "unknown"


OPENAI_SDK_VERSION = _openai_version()


def _api_key_transport_diagnostics(api_key: str, base_url: str) -> dict[str, Any]:
    return {
        "api_key_configured": bool(api_key),
        "base_url": base_url,
    }


def _provider_client_error(
    exc: APIStatusError, *, model: str, transport_diagnostics: Mapping[str, Any]
) -> LLMProviderClientError:
    diagnostic = _client_error_diagnostic(
        exc, model=model, transport_diagnostics=transport_diagnostics
    )
    message = _client_error_message(diagnostic)
    http_status = diagnostic["http_status"]
    status_code = http_status if isinstance(http_status, int) else 502
    return LLMProviderClientError(
        message,
        details=diagnostic,
        status_code=status_code,
        app_code=_application_error_code(diagnostic["openrouter_error_code"]),
        retryable=_is_retryable_provider_error(exc),
    )


def _client_error_message(diagnostic: Mapping[str, Any]) -> str:
    message = diagnostic.get("openrouter_error_message")
    if isinstance(message, str) and message:
        return f"OpenRouter request rejected: {message}"
    return "OpenRouter request rejected by the provider."


def _client_error_diagnostic(
    exc: APIStatusError, *, model: str, transport_diagnostics: Mapping[str, Any]
) -> dict[str, Any]:
    http_status = _http_status(exc)
    response_body = _response_body(exc)
    response_json = _response_json(response_body)
    openrouter_error_code = _openrouter_error_code(exc, response_json)
    openrouter_error_message = _openrouter_error_message(exc, response_json)
    return {
        "provider": "openrouter",
        "model": model,
        "sdk": "openai",
        "sdk_version": OPENAI_SDK_VERSION,
        "error_type": type(exc).__name__,
        "exception": str(exc),
        "http_status": http_status,
        "openrouter_error_code": openrouter_error_code,
        "openrouter_error_message": openrouter_error_message,
        "response_body": response_body,
        "response_json": response_json,
        "diagnostic_hint": _diagnostic_hint(http_status, openrouter_error_code),
        **transport_diagnostics,
    }


def _http_status(exc: APIStatusError) -> int | None:
    status_code = getattr(exc, "status_code", None)
    return status_code if isinstance(status_code, int) else None


def _openrouter_error_code(exc: APIStatusError, response_json: Any) -> str | None:
    payload = _error_payload(response_json)
    for key in ("code", "status", "type"):
        value = payload.get(key)
        if value is not None:
            return str(value)
    status_code = _http_status(exc)
    return str(status_code) if status_code is not None else None


def _openrouter_error_message(exc: APIStatusError, response_json: Any) -> str | None:
    payload = _error_payload(response_json)
    message = payload.get("message")
    if message is not None:
        return str(message)
    exception_message = getattr(exc, "message", None)
    return str(exception_message) if exception_message else None


def _error_payload(details: Any) -> Mapping[str, Any]:
    if not isinstance(details, Mapping):
        return {}
    error = details.get("error")
    if isinstance(error, Mapping):
        return error
    return details


def _response_body(exc: APIStatusError) -> Any:
    body = getattr(exc, "body", None)
    if body is not None:
        return _json_safe(body)
    response = getattr(exc, "response", None)
    text = getattr(response, "text", None)
    if text is not None:
        return _json_safe(text)
    return None


def _response_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return _json_safe(json.loads(value))
        except json.JSONDecodeError:
            return None
    return _json_safe(value)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence):
        return [_json_safe(item) for item in value]
    return str(value)


def _application_error_code(openrouter_error_code: Any) -> str:
    raw = str(openrouter_error_code or "CLIENT_ERROR").upper()
    normalized = "".join(character if character.isalnum() else "_" for character in raw)
    normalized = "_".join(part for part in normalized.split("_") if part)
    if not normalized:
        normalized = "CLIENT_ERROR"
    if normalized.isdigit():
        normalized = f"HTTP_{normalized}"
    return f"OPENROUTER_{normalized}"


def _metric_error_code(exc: Exception) -> str:
    if isinstance(exc, APIStatusError):
        response_json = _response_json(_response_body(exc))
        return _application_error_code(_openrouter_error_code(exc, response_json))
    return type(exc).__name__


def _diagnostic_hint(http_status: int | None, openrouter_error_code: str | None) -> str:
    if http_status == 400:
        return "Check the OpenRouter request shape, API version, and model parameters."
    if http_status in {401, 403}:
        return "Check the OpenRouter API key, account credits, and model permissions."
    if http_status == 404:
        return "Check the OpenRouter model name and requested resource access."
    if http_status == 429:
        return "Check OpenRouter quota, rate limits, spend limits, and billing settings."
    if openrouter_error_code:
        return "Check the OpenRouter provider response body for the authoritative reason."
    return "Check OpenRouter status and provider logs for the authoritative reason."
