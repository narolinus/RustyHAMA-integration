"""Protocol validation and message helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import voluptuous as vol

from .const import PROTOCOL_VERSION

MESSAGE_SCHEMA = vol.Schema(
    {
        vol.Required("version"): vol.All(int, vol.Range(min=1)),
        vol.Required("id"): vol.All(str, vol.Length(min=1, max=128)),
        vol.Required("type"): vol.All(str, vol.Length(min=1, max=128)),
        vol.Optional("timestamp"): str,
        vol.Optional("revision", default=0): vol.All(int, vol.Range(min=0)),
        vol.Optional("payload", default={}): dict,
    },
    extra=vol.PREVENT_EXTRA,
)


def envelope(
    message_type: str,
    payload: dict[str, Any] | None = None,
    *,
    revision: int = 0,
    message_id: str | None = None,
) -> dict[str, Any]:
    """Build a protocol envelope."""
    return {
        "version": PROTOCOL_VERSION,
        "id": message_id or uuid4().hex,
        "type": message_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "revision": revision,
        "payload": payload or {},
    }


def validate_message(raw: Any) -> dict[str, Any]:
    """Validate and normalize a received message."""
    message = MESSAGE_SCHEMA(raw)
    if message["version"] != PROTOCOL_VERSION:
        raise vol.Invalid(f"unsupported protocol version {message['version']}")
    return message
