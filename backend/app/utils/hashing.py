"""Deterministic hashing and canonical JSON serialization."""

import hashlib
import json
from typing import Any


def sha256_text(value: str) -> str:
    """Return a hexadecimal SHA-256 digest for UTF-8 text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    """Serialize JSON-compatible data deterministically for fingerprints."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    """Hash canonical JSON-compatible data."""
    return sha256_text(canonical_json(value))

