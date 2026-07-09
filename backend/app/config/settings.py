"""Validated environment-backed application settings."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Self
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PRODUCTION_TRUSTED_HOST_DEFAULTS = ("*.onrender.com", "localhost", "127.0.0.1")
PRODUCTION_CORS_ALLOWED_ORIGIN_DEFAULTS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
PRODUCTION_CORS_ALLOWED_ORIGIN_REGEX = (
    r"^https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.vercel\.app$"
)


def _hostname_from_origin(origin: str) -> str | None:
    value = origin.strip()
    if not value or value == "*":
        return None

    parsed = urlsplit(value)
    if parsed.hostname is None and "://" not in value:
        parsed = urlsplit(f"//{value}")
    if parsed.hostname is None:
        return None
    return parsed.hostname.lower()


def _normalize_cors_origin(origin: str) -> str | None:
    value = origin.strip().rstrip("/")
    if not value:
        return None
    if value == "*":
        return value

    parsed = urlsplit(value)
    if parsed.scheme and parsed.netloc and not parsed.path and not parsed.query:
        host = parsed.hostname.lower() if parsed.hostname is not None else parsed.netloc.lower()
        port = f":{parsed.port}" if parsed.port is not None else ""
        return f"{parsed.scheme.lower()}://{host}{port}"
    return value


def _normalize_trusted_host(host: str) -> str | None:
    value = host.strip().lower()
    if not value:
        return None
    if value == "*" or value.startswith("*."):
        return value

    parsed = urlsplit(value)
    if parsed.hostname is not None and "://" in value:
        return parsed.hostname.lower()
    if ":" in value or "/" in value:
        parsed = urlsplit(f"//{value}")
        if parsed.hostname is not None:
            return parsed.hostname.lower()
    return value


def _unique_hosts(hosts: Iterable[str | None]) -> list[str]:
    normalized_hosts: list[str] = []
    seen: set[str] = set()
    for host in hosts:
        if host is None or host in seen:
            continue
        normalized_hosts.append(host)
        seen.add(host)
    return normalized_hosts


def _unique_origins(origins: Iterable[str | None]) -> list[str]:
    normalized_origins: list[str] = []
    seen: set[str] = set()
    for origin in origins:
        if origin is None or origin in seen:
            continue
        normalized_origins.append(origin)
        seen.add(origin)
    return normalized_origins


class Environment(StrEnum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Single source of truth for runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ALA_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Learning Assistant API"
    app_version: str = "0.1.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    host: str = "0.0.0.0"  # noqa: S104 - container bind address is intentional
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"

    database_url: str = "sqlite+aiosqlite:///./data/learning_assistant.db"
    database_echo: bool = False

    gemini_api_key: SecretStr | None = None
    llm_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = Field(default=768, ge=128, le=3072)
    llm_timeout_seconds: float = Field(default=45.0, gt=0, le=180)
    embedding_timeout_seconds: float = Field(default=30.0, gt=0, le=180)
    provider_max_attempts: int = Field(default=3, ge=1, le=5)
    ai_temperature: float = Field(default=0.25, ge=0, le=2)
    ai_top_p: float = Field(default=0.90, gt=0, le=1)
    ai_top_k: int = Field(default=40, ge=1, le=100)
    ai_max_output_tokens: int = Field(default=8192, ge=256, le=65536)
    ai_safety_threshold: str = "BLOCK_MEDIUM_AND_ABOVE"
    ai_input_cost_per_million: float = Field(default=0.0, ge=0)
    ai_output_cost_per_million: float = Field(default=0.0, ge=0)
    ai_metrics_path: Path = Path("./data/ai-metrics.jsonl")
    ai_cache_path: Path = Path("./data/ai-cache.sqlite3")
    embedding_concurrency: int = Field(default=4, ge=1, le=20)
    embedding_document_instruction: str = "Represent this learning content for retrieval:"
    embedding_query_instruction: str = "Represent this learner question for retrieval:"

    chroma_path: Path = Path("./data/chroma")
    chroma_collection_prefix: str = Field(
        default="learning_content", pattern=r"^[a-z][a-z0-9_-]{2,50}$"
    )
    prompt_root: Path = Path("app/prompts/templates")

    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    max_request_bytes: int = Field(default=1_048_576, ge=1024, le=10_485_760)
    allow_anonymous_learner: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "allow_anonymous_learner",
            "ALA_ALLOW_ANONYMOUS_LEARNER",
            "ALA_ALLOW_ANONYMOUS_LEARNERS",
        ),
    )
    anonymous_learner_id: UUID = UUID("00000000-0000-4000-8000-000000000001")

    chunk_target_tokens: int = Field(default=400, ge=100, le=1000)
    chunk_max_tokens: int = Field(default=600, ge=150, le=1500)
    chunk_overlap_tokens: int = Field(default=60, ge=0, le=200)
    retrieval_candidates: int = Field(default=20, ge=1, le=100)
    retrieval_context_chunks: int = Field(default=8, ge=1, le=20)
    retrieval_min_relevance: float = Field(default=0.25, ge=0, le=1)
    quality_threshold: float = Field(default=0.80, ge=0, le=1)
    response_cache_ttl_seconds: int = Field(default=86_400, ge=60)
    metrics_enabled: bool = True

    @model_validator(mode="after")
    def validate_runtime_policy(self) -> Self:
        """Reject configurations that would be unsafe or internally inconsistent."""
        self.cors_allowed_origins = _unique_origins(
            _normalize_cors_origin(origin) for origin in self.cors_allowed_origins
        )
        self.trusted_hosts = _unique_hosts(
            _normalize_trusted_host(host) for host in self.trusted_hosts
        )
        if self.chunk_target_tokens > self.chunk_max_tokens:
            raise ValueError("chunk_target_tokens cannot exceed chunk_max_tokens")
        if self.chunk_overlap_tokens >= self.chunk_target_tokens:
            raise ValueError("chunk_overlap_tokens must be smaller than chunk_target_tokens")
        if self.environment is Environment.PRODUCTION:
            self.cors_allowed_origins = _unique_origins(
                [*self.cors_allowed_origins, *PRODUCTION_CORS_ALLOWED_ORIGIN_DEFAULTS]
            )
            self.trusted_hosts = _unique_hosts(
                [
                    *self.trusted_hosts,
                    *PRODUCTION_TRUSTED_HOST_DEFAULTS,
                    *(_hostname_from_origin(origin) for origin in self.cors_allowed_origins),
                ]
            )
            if self.gemini_api_key is None:
                raise ValueError("ALA_GEMINI_API_KEY is required in production")
            if self.allow_anonymous_learner:
                raise ValueError("anonymous learners must be disabled in production")
            if "*" in self.cors_allowed_origins or "*" in self.trusted_hosts:
                raise ValueError(
                    "wildcard CORS origins and trusted hosts are forbidden in production"
                )
        return self

    @property
    def is_production(self) -> bool:
        """Return whether strict production behavior is required."""
        return self.environment is Environment.PRODUCTION

    @property
    def cors_allowed_origin_regex(self) -> str | None:
        """Return the production-only dynamic frontend origin matcher."""
        if self.environment is Environment.PRODUCTION:
            return PRODUCTION_CORS_ALLOWED_ORIGIN_REGEX
        return None

    @property
    def chroma_collection_name(self) -> str:
        """Return a model- and dimension-isolated Chroma collection name."""
        model_slug = self.embedding_model.lower().replace("_", "-")
        return f"{self.chroma_collection_prefix}--{model_slug}--d{self.embedding_dimensions}--v1"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build and cache immutable process configuration."""
    return Settings()
