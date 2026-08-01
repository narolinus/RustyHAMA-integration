"""Redacted diagnostics for RustyHAMA."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .merge import redact_secrets


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: Any
) -> dict[str, Any]:
    """Return operational state without provider keys or device credentials."""
    manager = entry.runtime_data.manager
    return redact_secrets(manager.public_snapshot())
