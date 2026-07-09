"""Compact JSON-output instructions for locally validated AI responses."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from enum import Enum
from types import UnionType
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel

from app.core.interfaces.ai import GenerationRequest

_JSON_OBJECT_RESPONSE_SCHEMA = {"type": "object"}


def json_object_response_schema() -> Mapping[str, str]:
    """Return the provider-neutral signal for plain JSON-object output."""
    return dict(_JSON_OBJECT_RESPONSE_SCHEMA)


def with_json_output_contract(
    request: GenerationRequest, schema: type[BaseModel]
) -> GenerationRequest:
    """Attach compact output-format instructions without provider-side schemas."""
    return replace(
        request,
        prompt=append_json_output_contract(request.prompt, schema),
        response_schema=json_object_response_schema(),
    )


def append_json_output_contract(prompt: str, schema: type[BaseModel]) -> str:
    """Append a concise JSON shape that is safe to send to non-schema providers."""
    return (
        f"{prompt.rstrip()}\n\n"
        "<json_output_contract>\n"
        f"{json_output_contract(schema)}\n"
        "</json_output_contract>"
    )


def json_output_contract(schema: type[BaseModel]) -> str:
    """Describe the required JSON shape without serializing Pydantic JSON Schema."""
    return (
        "Return exactly one valid JSON object with no markdown, prose, comments, trailing "
        "commas, wrapper keys, or undeclared fields.\n"
        "Use this JSON shape and field order:\n"
        f"{_format_model(schema)}\n"
        "Local backend validation will reject missing fields, extra fields, wrong value "
        "types, invalid enum values, empty required arrays, and inconsistent ordering."
    )


def _format_model(model: type[BaseModel], indent: int = 0) -> str:
    pad = " " * indent
    field_pad = " " * (indent + 2)
    lines = [f"{pad}{{"]
    for name, field in model.model_fields.items():
        value = _format_annotation(field.annotation, indent + 2)
        if "\n" in value:
            value_lines = value.splitlines()
            lines.append(f"{field_pad}{json.dumps(name)}: {value_lines[0].lstrip()}")
            lines.extend(value_lines[1:])
        else:
            lines.append(f"{field_pad}{json.dumps(name)}: {value}")
    lines.append(f"{pad}}}")
    return "\n".join(lines)


def _format_annotation(annotation: Any, indent: int) -> str:
    annotation = _strip_annotated(annotation)
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Literal:
        return " | ".join(json.dumps(value) for value in args)
    if origin in {Union, UnionType}:
        return " | ".join(_format_annotation(arg, indent) for arg in args)
    if origin is list:
        item = _format_annotation(args[0] if args else Any, indent + 2)
        if "\n" in item:
            return f"[\n{item}\n{' ' * indent}]"
        return f"[{item}]"
    if origin is dict:
        value = _format_annotation(args[1], indent + 2) if len(args) > 1 else "value"
        return f'{{"key": {value}}}'

    if _is_model(annotation):
        return _format_model(annotation, indent)
    if _is_enum(annotation):
        return " | ".join(json.dumps(member.value) for member in annotation)
    if annotation is str:
        return "string"
    if annotation is int:
        return "integer"
    if annotation is float:
        return "number"
    if annotation is bool:
        return "boolean"
    if annotation is type(None):
        return "null"

    name = getattr(annotation, "__name__", "")
    if name == "HttpUrl":
        return "URL string"
    return "value"


def _strip_annotated(annotation: Any) -> Any:
    while get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    return annotation


def _is_model(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def _is_enum(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, Enum)
