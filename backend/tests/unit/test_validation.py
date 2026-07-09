"""Structured response validation tests."""

import json

import pytest

from app.ai.validation import ResponseValidator
from app.exceptions import AIResponseValidationError
from app.schemas.ai_outputs import GeneratedRoadmap


def valid_roadmap() -> dict[str, object]:
    return {
        "goal_title": "Backend Engineer",
        "summary": "A progressive path from HTTP fundamentals to production services.",
        "estimated_hours": 10.0,
        "skills": [
            {
                "title": "Python APIs",
                "description": "Build robust typed web APIs with validation and tests.",
                "target_proficiency": "intermediate",
                "estimated_hours": 10.0,
                "order_index": 0,
                "tasks": [
                    {
                        "title": "FastAPI service",
                        "description": "Implement a layered HTTP service with strict contracts.",
                        "difficulty": "beginner",
                        "estimated_hours": 10.0,
                        "order_index": 0,
                        "learning_outcomes": ["Design typed API boundaries"],
                        "subtasks": [
                            {
                                "title": "Create routes",
                                "description": "Create and test typed route handlers.",
                                "completion_criteria": "Contract tests pass.",
                                "estimated_hours": 10.0,
                                "order_index": 0,
                            }
                        ],
                    }
                ],
            }
        ],
    }


def test_validator_returns_typed_roadmap() -> None:
    value = ResponseValidator(GeneratedRoadmap).validate_json(json.dumps(valid_roadmap()))
    assert value.skills[0].tasks[0].title == "FastAPI service"


def test_validator_rejects_non_contiguous_ordering() -> None:
    payload = valid_roadmap()
    payload["skills"][0]["order_index"] = 2  # type: ignore[index]

    with pytest.raises(AIResponseValidationError):
        ResponseValidator(GeneratedRoadmap).validate_json(json.dumps(payload))
