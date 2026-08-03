"""Runtime models for RustyHAMA."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .const import DEFAULT_PROFILE_ID


def utc_iso() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class DeviceRecord:
    """Persistent and live data for one paired Android device."""

    device_id: str
    name: str
    token_hash: str
    subentry_id: str
    profile_id: str = DEFAULT_PROFILE_ID
    area_id: str | None = None
    override: dict[str, Any] = field(default_factory=dict)
    provider_bindings: dict[str, str] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    display: dict[str, Any] = field(default_factory=dict)
    telemetry: dict[str, Any] = field(default_factory=dict)
    config_revision: int = 0
    acknowledged_revision: int = 0
    last_seen: str | None = None
    paired_at: str = field(default_factory=utc_iso)
    online: bool = False
    session_generation: int = 0
    recent_message_ids: deque[str] = field(default_factory=lambda: deque(maxlen=256))

    def persistent_dict(self) -> dict[str, Any]:
        """Serialize persistent fields."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "token_hash": self.token_hash,
            "subentry_id": self.subentry_id,
            "profile_id": self.profile_id,
            "area_id": self.area_id,
            "override": self.override,
            "provider_bindings": self.provider_bindings,
            "capabilities": self.capabilities,
            "display": self.display,
            "telemetry": self.telemetry,
            "config_revision": self.config_revision,
            "acknowledged_revision": self.acknowledged_revision,
            "last_seen": self.last_seen,
            "paired_at": self.paired_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceRecord:
        """Deserialize a device."""
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass(slots=True)
class PairingRequest:
    """Short-lived pairing authorization."""

    code_hash: str
    qr_token_hash: str
    name: str
    profile_id: str
    area_id: str | None
    expires_at: float
    attempts: int = 0


@dataclass(slots=True)
class DeviceSession:
    """Live WebSocket session."""

    device_id: str
    websocket: Any
    generation: int
    connected_at: str = field(default_factory=utc_iso)
    last_activity_monotonic: float = field(default_factory=time.monotonic)
    pending: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeData:
    """Config-entry runtime container."""

    manager: Any
