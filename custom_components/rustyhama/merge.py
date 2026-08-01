"""RFC 7396 merge patch implementation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def merge_patch(target: Any, patch: Any) -> Any:
    """Apply an RFC 7396 JSON Merge Patch without mutating its inputs."""
    if not isinstance(patch, dict):
        return deepcopy(patch)
    result: dict[str, Any] = deepcopy(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, dict):
            result[key] = merge_patch(result.get(key), value)
        else:
            result[key] = deepcopy(value)
    return result


def redact_secrets(value: Any) -> Any:
    """Recursively remove values whose key denotes a secret."""
    from .const import SECRET_FIELDS

    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if not isinstance(value, dict):
        return deepcopy(value)
    output: dict[str, Any] = {}
    for key, child in value.items():
        lowered = key.lower()
        if lowered in SECRET_FIELDS or lowered.endswith(("_api_key", "_token", "_password")):
            output[key] = "**REDACTED**"
        else:
            output[key] = redact_secrets(child)
    return output
