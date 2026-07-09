"""Versioned, validated external prompt management."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import StrictUndefined, meta
from jinja2.sandbox import SandboxedEnvironment

from app.core.interfaces.ai import PromptRenderer, RenderedPrompt
from app.core.interfaces.cache import AICache
from app.exceptions import PromptConfigurationError
from app.utils.hashing import fingerprint, sha256_text


@dataclass(frozen=True, slots=True)
class PromptAsset:
    """Validated prompt template metadata."""

    prompt_id: str
    version: str
    response_schema: str
    required_variables: frozenset[str]
    template: str
    prompt_hash: str


class PromptManager(PromptRenderer):
    """Load, validate, render, and cache versioned prompt assets."""

    def __init__(self, root: Path, cache: AICache, cache_ttl_seconds: int = 86_400) -> None:
        self._root = root
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds
        self._environment = SandboxedEnvironment(
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._assets: dict[tuple[str, str], PromptAsset] = {}
        self._active_versions: dict[str, str] = {}
        self._load_lock = asyncio.Lock()

    async def render(
        self, prompt_id: str, variables: Mapping[str, Any], version: str | None = None
    ) -> RenderedPrompt:
        asset = await self._get_asset(prompt_id, version)
        received = frozenset(variables)
        if received != asset.required_variables:
            raise PromptConfigurationError(
                "Prompt variables do not match the reviewed manifest.",
                details={
                    "prompt_id": prompt_id,
                    "missing": sorted(asset.required_variables - received),
                    "unexpected": sorted(received - asset.required_variables),
                },
            )
        variables_hash = fingerprint(dict(variables))
        cache_key = fingerprint(
            {
                "prompt_id": prompt_id,
                "version": asset.version,
                "prompt_hash": asset.prompt_hash,
                "variables_hash": variables_hash,
            }
        )
        cached = await self._cache.get("prompt_render", cache_key)
        if isinstance(cached, dict) and isinstance(cached.get("text"), str):
            text = cached["text"]
        else:
            try:
                text = self._environment.from_string(asset.template).render(**variables)
            except Exception as exc:
                raise PromptConfigurationError(
                    "Prompt rendering failed.",
                    details={"prompt_id": prompt_id, "version": asset.version},
                ) from exc
            await self._cache.set(
                "prompt_render", cache_key, {"text": text}, self._cache_ttl_seconds
            )
        return RenderedPrompt(
            prompt_id=prompt_id,
            version=asset.version,
            text=text,
            prompt_hash=asset.prompt_hash,
            variables_hash=variables_hash,
        )

    async def _get_asset(self, prompt_id: str, version: str | None) -> PromptAsset:
        if prompt_id not in self._active_versions:
            async with self._load_lock:
                if prompt_id not in self._active_versions:
                    self._load_manifest(prompt_id)
        resolved_version = version or self._active_versions[prompt_id]
        asset = self._assets.get((prompt_id, resolved_version))
        if asset is None:
            raise PromptConfigurationError(
                "Requested prompt version does not exist.",
                details={"prompt_id": prompt_id, "version": resolved_version},
            )
        return asset

    def _load_manifest(self, prompt_id: str) -> None:
        directory = self._root / prompt_id
        manifest_path = directory / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest["prompt_id"] != prompt_id:
                raise ValueError("prompt ID does not match directory")
            active_version = str(manifest["active_version"])
            for version, definition in manifest["versions"].items():
                template_path = directory / str(definition["template"])
                template = template_path.read_text(encoding="utf-8")
                required = frozenset(str(value) for value in definition["required_variables"])
                parsed = self._environment.parse(template)
                declared = frozenset(meta.find_undeclared_variables(parsed))
                if declared != required:
                    raise ValueError(
                        f"template variables {sorted(declared)} do not match {sorted(required)}"
                    )
                asset = PromptAsset(
                    prompt_id=prompt_id,
                    version=str(version),
                    response_schema=str(definition["response_schema"]),
                    required_variables=required,
                    template=template,
                    prompt_hash=sha256_text(template),
                )
                self._assets[(prompt_id, str(version))] = asset
            if (prompt_id, active_version) not in self._assets:
                raise ValueError("active version is not declared")
            self._active_versions[prompt_id] = active_version
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PromptConfigurationError(
                "Prompt manifest is missing or invalid.", details={"prompt_id": prompt_id}
            ) from exc
