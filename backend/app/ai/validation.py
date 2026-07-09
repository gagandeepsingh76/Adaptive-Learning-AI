"""Strict schema and logical consistency validation for AI responses."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from pydantic import BaseModel, ValidationError

from app.exceptions import AIResponseValidationError
from app.schemas.ai_outputs import GeneratedProject, GeneratedRoadmap


class ResponseValidator[OutputT: BaseModel]:
    """Decode JSON and enforce schema plus generation-specific invariants."""

    def __init__(self, schema: type[OutputT], hour_tolerance: float = 0.10) -> None:
        self.schema = schema
        self.hour_tolerance = hour_tolerance

    def validate_json(self, payload: str) -> OutputT:
        """Return a typed object or raise a client-safe validation exception."""
        try:
            decoded = json.loads(payload)
            if not isinstance(decoded, dict):
                raise ValueError("top-level JSON must be an object")
            candidate = self.schema.model_validate(decoded, strict=False)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise AIResponseValidationError(
                "AI response failed JSON schema validation.",
                details={"errors": _validation_errors(exc)},
            ) from exc
        issues = self.logical_issues(candidate)
        if issues:
            raise AIResponseValidationError(
                "AI response failed logical consistency validation.",
                details={"errors": issues},
            )
        return candidate

    def logical_issues(self, candidate: OutputT) -> list[str]:
        """Return deterministic domain issues for the supported output type."""
        if isinstance(candidate, GeneratedRoadmap):
            return self._roadmap_issues(candidate)
        if isinstance(candidate, GeneratedProject):
            return self._project_issues(candidate)
        return []

    def _roadmap_issues(self, roadmap: GeneratedRoadmap) -> list[str]:
        issues: list[str] = []
        issues.extend(_order_issues("skill", [skill.order_index for skill in roadmap.skills]))
        issues.extend(_duplicate_issues("skill", [skill.title for skill in roadmap.skills]))
        for skill in roadmap.skills:
            issues.extend(
                _order_issues(f"task in {skill.title}", [task.order_index for task in skill.tasks])
            )
            issues.extend(
                _duplicate_issues(f"task in {skill.title}", [task.title for task in skill.tasks])
            )
            task_hours = sum(task.estimated_hours for task in skill.tasks)
            if not _hours_match(skill.estimated_hours, task_hours, self.hour_tolerance):
                issues.append(f"Task hours do not match skill hours for {skill.title}.")
            for task in skill.tasks:
                issues.extend(
                    _order_issues(
                        f"subtask in {task.title}",
                        [subtask.order_index for subtask in task.subtasks],
                    )
                )
                issues.extend(
                    _duplicate_issues(
                        f"subtask in {task.title}",
                        [subtask.title for subtask in task.subtasks],
                    )
                )
                subtask_hours = sum(item.estimated_hours for item in task.subtasks)
                if not _hours_match(task.estimated_hours, subtask_hours, self.hour_tolerance):
                    issues.append(f"Subtask hours do not match task hours for {task.title}.")
        skill_hours = sum(skill.estimated_hours for skill in roadmap.skills)
        if not _hours_match(roadmap.estimated_hours, skill_hours, self.hour_tolerance):
            issues.append("Skill hours do not match roadmap estimated hours.")
        return issues

    @staticmethod
    def _project_issues(project: GeneratedProject) -> list[str]:
        issues = _duplicate_issues("project skill", project.skills)
        issues.extend(_duplicate_issues("requirement", project.requirements))
        issues.extend(_duplicate_issues("deliverable", project.deliverables))
        issues.extend(_duplicate_issues("acceptance criterion", project.acceptance_criteria))
        return issues


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _duplicate_issues(label: str, values: Iterable[str]) -> list[str]:
    normalized = [_normalize(value) for value in values]
    if len(set(normalized)) != len(normalized):
        return [f"Duplicate {label} titles are not allowed."]
    return []


def _order_issues(label: str, values: list[int]) -> list[str]:
    if values != list(range(len(values))):
        return [f"{label.capitalize()} ordering must be contiguous and zero-based."]
    return []


def _hours_match(parent: float, children: float, tolerance: float) -> bool:
    return abs(parent - children) <= max(0.5, parent * tolerance)


def _validation_errors(exc: Exception) -> list[str]:
    if isinstance(exc, ValidationError):
        return [f"{'.'.join(map(str, error['loc']))}: {error['msg']}" for error in exc.errors()]
    return [str(exc)]
