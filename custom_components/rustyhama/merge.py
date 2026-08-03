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


def apply_tab_order(config: dict[str, Any]) -> dict[str, Any]:
    """Apply an optional partial tab order without replacing the tabs array.

    RFC 7396 intentionally replaces arrays. ``tab_order`` is therefore a
    RustyHAMA post-merge directive: listed tab ids are moved to the front in
    the requested order and all unlisted tabs retain their profile order.
    """
    result = deepcopy(config)
    tabs = result.get("tabs")
    order = result.get("tab_order")
    if not isinstance(tabs, list) or not isinstance(order, list):
        return result
    by_id = {
        str(tab.get("id")): tab
        for tab in tabs
        if isinstance(tab, dict) and tab.get("id") is not None
    }
    requested = [str(tab_id) for tab_id in order]
    selected = [by_id[tab_id] for tab_id in requested if tab_id in by_id]
    selected_ids = set(requested)
    result["tabs"] = selected + [
        tab
        for tab in tabs
        if not isinstance(tab, dict) or str(tab.get("id")) not in selected_ids
    ]
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
