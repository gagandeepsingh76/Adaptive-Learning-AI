"""Gemini implementation of the provider-neutral LLM contract."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Mapping, Sequence
from importlib.metadata import PackageNotFoundError, version
from time import perf_counter
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import ClientError
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
_GEMINI_SCHEMA_OMITTED_KEYS = frozenset(
    {
        "additionalProperties",
        "default",
        "description",
        "examples",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "maxItems",
        "maxLength",
        "maximum",
        "minItems",
        "minLength",
        "minimum",
        "pattern",
        "title",
    }
)


class GeminiProvider(LLMProvider):
    """Configurable Gemini generation adapter with bounded retries and telemetry."""

    def __init__(
        self,
        api_key: str,
        settings: AISettings,
        observability: AIObservabilitySink | None = None,
        client: Any | None = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("A Gemini API key is required")
        self._settings = settings
        self._sink = observability or NullAIObservabilitySink()
        self._client = client or genai.Client(api_key=api_key)
        self._transport_diagnostics = _api_key_transport_diagnostics(self._client, api_key)

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
                        response = await self._client.aio.models.generate_content(
                            model=model,
                            contents=request.prompt,
                            config=self._generation_config(request),
                        )
            result = self._to_result(response, model, started, retry_count)
            await self._record(request, result, "success", None)
            return result
        except Exception as exc:
            latency_ms = (perf_counter() - started) * 1000
            await self._record_failure(request, model, latency_ms, retry_count, exc)
            if isinstance(exc, LLMProviderError):
                raise
            if isinstance(exc, ClientError):
                raise _provider_client_error(
                    exc, model=model, transport_diagnostics=self._transport_diagnostics
                ) from exc
            raise LLMProviderError(
                "Gemini generation failed.", details={"error_type": type(exc).__name__}
            ) from exc

    async def stream(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        """Stream normalized text chunks while retaining provider independence."""
        model = request.model or self._settings.llm_model
        started = perf_counter()
        usage = TokenUsage()
        try:
            async with asyncio.timeout(self._settings.generation_timeout_seconds):
                stream = await self._client.aio.models.generate_content_stream(
                    model=model,
                    contents=request.prompt,
                    config=self._generation_config(request),
                )
                async for response in stream:
                    text = self._extract_text(response, allow_empty=True)
                    usage = self._usage(response) or usage
                    finish_reason = self._finish_reason(response)
                    if text or finish_reason:
                        yield GenerationChunk(
                            text=text, finish_reason=finish_reason, usage=usage
                        )
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
            if isinstance(exc, ClientError):
                raise _provider_client_error(
                    exc, model=model, transport_diagnostics=self._transport_diagnostics
                ) from exc
            raise LLMProviderError(
                "Gemini streaming generation failed.",
                details={"error_type": type(exc).__name__},
            ) from exc

    def _generation_config(self, request: GenerationRequest) -> types.GenerateContentConfig:
        threshold = types.HarmBlockThreshold(self._settings.safety_threshold)
        response_schema = _gemini_response_json_schema(request.response_schema)
        categories = (
            types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        )
        return types.GenerateContentConfig(
            system_instruction=_system_instruction_with_schema(
                request.system_instruction, response_schema
            ),
            temperature=request.temperature
            if request.temperature is not None
            else self._settings.temperature,
            top_p=request.top_p if request.top_p is not None else self._settings.top_p,
            top_k=request.top_k if request.top_k is not None else self._settings.top_k,
            max_output_tokens=request.max_output_tokens
            if request.max_output_tokens is not None
            else self._settings.max_output_tokens,
            response_mime_type="application/json" if request.response_schema else "text/plain",
            response_json_schema=None,
            safety_settings=[
                types.SafetySetting(category=category, threshold=threshold)
                for category in categories
            ],
        )

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
        try:
            value = response.text
        except (AttributeError, ValueError) as exc:
            raise LLMProviderError("Gemini blocked or omitted response content.") from exc
        if not value and not allow_empty:
            raise LLMProviderError("Gemini returned an empty response.")
        return value or ""

    @staticmethod
    def _usage(response: Any) -> TokenUsage:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return TokenUsage()
        return TokenUsage(
            input_tokens=int(getattr(usage, "prompt_token_count", 0) or 0),
            output_tokens=int(getattr(usage, "candidates_token_count", 0) or 0),
            total_tokens=int(getattr(usage, "total_token_count", 0) or 0),
        )

    @staticmethod
    def _finish_reason(response: Any) -> str | None:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None
        reason = getattr(candidates[0], "finish_reason", None)
        return str(getattr(reason, "value", reason)) if reason is not None else None

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
                provider="gemini",
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
        if isinstance(exc, ClientError):
            diagnostic = _client_error_diagnostic(
                exc, model=model, transport_diagnostics=self._transport_diagnostics
            )
            log_fields.update(
                {
                    "http_status": diagnostic["http_status"],
                    "gemini_error_code": diagnostic["gemini_error_code"],
                    "gemini_error_message": diagnostic["gemini_error_message"],
                    "response_body": diagnostic["response_body"],
                    "api_key_sent": diagnostic["api_key_sent"],
                    "sdk_version": diagnostic["sdk_version"],
                    "gemini_client_error": diagnostic,
                }
            )
        logger.warning(
            "ai.generation.failed",
            **log_fields,
        )
        result = GenerationResult(
            text="", model=model, usage=TokenUsage(), latency_ms=latency_ms, retry_count=retry_count
        )
        await self._record(request, result, "failure", _metric_error_code(exc))


def _is_retryable_provider_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError, asyncio.TimeoutError)):
        return True
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return status_code == 429 or (isinstance(status_code, int) and status_code >= 500)


def _gemini_response_json_schema(schema: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if schema is None:
        return None
    simplified = _simplify_gemini_schema(schema)
    return simplified if isinstance(simplified, dict) else None


def _system_instruction_with_schema(
    system_instruction: str | None, schema: Mapping[str, Any] | None
) -> str | None:
    if schema is None:
        return system_instruction
    schema_text = json.dumps(schema, separators=(",", ":"), sort_keys=True)
    schema_instruction = (
        "Return only one valid JSON object matching this response schema shape. "
        "Do not include markdown fences, prose, or undeclared top-level fields. "
        "The backend will enforce the full strict schema after generation.\n"
        f"<response_schema>{schema_text}</response_schema>"
    )
    if system_instruction:
        return f"{system_instruction}\n\n{schema_instruction}"
    return schema_instruction


def _simplify_gemini_schema(value: Any) -> Any:
    if isinstance(value, Mapping):
        simplified: dict[str, Any] = {}
        for key, item in value.items():
            string_key = str(key)
            if string_key in _GEMINI_SCHEMA_OMITTED_KEYS:
                continue
            simplified[string_key] = _simplify_gemini_schema(item)
        return simplified
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_simplify_gemini_schema(item) for item in value]
    return value


def _google_genai_version() -> str:
    try:
        return version("google-genai")
    except PackageNotFoundError:
        return "unknown"


GOOGLE_GENAI_VERSION = _google_genai_version()


def _api_key_transport_diagnostics(client: Any, api_key: str) -> dict[str, Any]:
    api_client = getattr(client, "_api_client", None)
    api_client_key = getattr(api_client, "api_key", None)
    http_options = getattr(api_client, "_http_options", None)
    headers = getattr(http_options, "headers", None)
    api_key_header = headers.get("x-goog-api-key") if isinstance(headers, Mapping) else None
    return {
        "api_key_configured": bool(api_key),
        "api_key_client_present": bool(api_client_key),
        "api_key_header_present": bool(api_key_header),
        "api_key_sent": bool(api_key_header),
    }


def _provider_client_error(
    exc: ClientError, *, model: str, transport_diagnostics: Mapping[str, Any]
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
        app_code=_application_error_code(diagnostic["gemini_error_code"]),
        retryable=_is_retryable_provider_error(exc),
    )


def _client_error_message(diagnostic: Mapping[str, Any]) -> str:
    message = diagnostic.get("gemini_error_message")
    if isinstance(message, str) and message:
        return f"Gemini request rejected: {message}"
    return "Gemini request rejected by the provider."


def _client_error_diagnostic(
    exc: ClientError, *, model: str, transport_diagnostics: Mapping[str, Any]
) -> dict[str, Any]:
    http_status = _http_status(exc)
    gemini_error_code = _gemini_error_code(exc)
    gemini_error_message = _gemini_error_message(exc)
    return {
        "provider": "gemini",
        "model": model,
        "sdk": "google-genai",
        "sdk_version": GOOGLE_GENAI_VERSION,
        "error_type": type(exc).__name__,
        "exception": str(exc),
        "http_status": http_status,
        "gemini_error_code": gemini_error_code,
        "gemini_error_message": gemini_error_message,
        "response_body": _response_body(exc),
        "response_json": _json_safe(getattr(exc, "details", None)),
        "diagnostic_hint": _diagnostic_hint(http_status, gemini_error_code),
        **transport_diagnostics,
    }


def _http_status(exc: ClientError) -> int | None:
    code = getattr(exc, "code", None)
    if isinstance(code, int):
        return code
    payload = _error_payload(getattr(exc, "details", None))
    payload_code = payload.get("code")
    return payload_code if isinstance(payload_code, int) else None


def _gemini_error_code(exc: ClientError) -> str | None:
    status = getattr(exc, "status", None)
    if status:
        return str(status)
    payload = _error_payload(getattr(exc, "details", None))
    payload_status = payload.get("status")
    if payload_status:
        return str(payload_status)
    payload_code = payload.get("code")
    return str(payload_code) if payload_code is not None else None


def _gemini_error_message(exc: ClientError) -> str | None:
    message = getattr(exc, "message", None)
    if message:
        return str(message)
    payload = _error_payload(getattr(exc, "details", None))
    payload_message = payload.get("message")
    return str(payload_message) if payload_message is not None else None


def _error_payload(details: Any) -> Mapping[str, Any]:
    if not isinstance(details, Mapping):
        return {}
    error = details.get("error")
    if isinstance(error, Mapping):
        return error
    return details


def _response_body(exc: ClientError) -> Any:
    response = getattr(exc, "response", None)
    for attr in ("text", "body"):
        value = getattr(response, attr, None)
        if value is not None:
            return _json_safe(value)
    body_segments = getattr(response, "body_segments", None)
    if body_segments is not None:
        return _json_safe(body_segments)
    return _json_safe(getattr(exc, "details", None))


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


def _application_error_code(gemini_error_code: Any) -> str:
    raw = str(gemini_error_code or "CLIENT_ERROR").upper()
    normalized = "".join(character if character.isalnum() else "_" for character in raw)
    normalized = "_".join(part for part in normalized.split("_") if part)
    if not normalized:
        normalized = "CLIENT_ERROR"
    if normalized.isdigit():
        normalized = f"HTTP_{normalized}"
    return f"GEMINI_{normalized}"


def _metric_error_code(exc: Exception) -> str:
    if isinstance(exc, ClientError):
        return _application_error_code(_gemini_error_code(exc))
    return type(exc).__name__


def _diagnostic_hint(http_status: int | None, gemini_error_code: str | None) -> str:
    if http_status == 400 and gemini_error_code == "FAILED_PRECONDITION":
        return (
            "Check Gemini API billing and whether the request is running from a "
            "free-tier-supported region."
        )
    if http_status == 400:
        return "Check the Gemini request shape, API version, and model-specific parameters."
    if http_status in {401, 403}:
        return (
            "Check API key validity, key restrictions, Gemini API enablement, and model "
            "permissions."
        )
    if http_status == 404:
        return "Check the Gemini model name, API version, and requested resource access."
    if http_status == 429:
        return "Check Gemini quota, rate limits, spend limits, and billing tier."
    return "Check the Gemini provider response body for the authoritative reason."
