"""Bounded JSON and prompt repair orchestration."""

from __future__ import annotations

from dataclasses import dataclass, replace

from pydantic import BaseModel

from app.core.interfaces.ai import GenerationRequest, GenerationResult, LLMProvider, PromptRenderer
from app.utils.hashing import fingerprint


@dataclass(frozen=True, slots=True)
class RepairedPrompt:
    """Derived prompt version used for one bounded regeneration attempt."""

    request: GenerationRequest
    repaired_version: str
    prompt_hash: str


class PromptRepairEngine:
    """Repair invalid JSON and reduce ambiguity without mutating reviewed assets."""

    def __init__(self, provider: LLMProvider, renderer: PromptRenderer) -> None:
        self._provider = provider
        self._renderer = renderer

    async def repair_json(
        self,
        invalid_payload: str,
        validation_errors: list[str],
        target_schema: type[BaseModel],
        original_request: GenerationRequest,
    ) -> GenerationResult:
        """Use the reviewed repair prompt to correct one malformed response."""
        rendered = await self._renderer.render(
            "repair",
            {
                "invalid_payload": invalid_payload,
                "original_instructions": original_request.prompt,
                "schema": target_schema.model_json_schema(),
                "validation_errors": validation_errors,
            },
        )
        return await self._provider.generate(
            GenerationRequest(
                prompt=rendered.text,
                system_instruction="Return only corrected JSON.",
                response_schema=target_schema.model_json_schema(),
                model=original_request.model,
                temperature=0.0,
                top_p=original_request.top_p,
                top_k=original_request.top_k,
                max_output_tokens=original_request.max_output_tokens,
                prompt_id=rendered.prompt_id,
                prompt_version=rendered.version,
                request_id=original_request.request_id,
                roadmap_id=original_request.roadmap_id,
            )
        )

    def improve_prompt(
        self,
        request: GenerationRequest,
        issues: list[str],
        attempt: int,
    ) -> RepairedPrompt:
        """Create a traceable, request-local clarification version for regeneration."""
        concise_issues = issues[:12]
        clarification = "\n".join(f"- {issue}" for issue in concise_issues)
        prompt = (
            f"{request.prompt}\n\n"
            "<generation_clarifications>\n"
            "Correct every issue below while preserving all original requirements:\n"
            f"{clarification}\n"
            "</generation_clarifications>"
        )
        base_version = request.prompt_version or "unversioned"
        repaired_version = f"{base_version}+repair.{attempt}"
        repaired_request = replace(
            request,
            prompt=prompt,
            prompt_version=repaired_version,
            temperature=0.0,
        )
        return RepairedPrompt(
            request=repaired_request,
            repaired_version=repaired_version,
            prompt_hash=fingerprint(
                {"prompt": prompt, "base_version": base_version, "attempt": attempt}
            ),
        )

