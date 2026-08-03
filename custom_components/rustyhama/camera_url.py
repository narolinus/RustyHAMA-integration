"""Validation helpers for direct RustyHAMA camera endpoints."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

DIRECT_CAMERA_PORT = 8765


def validated_direct_snapshot_url(
    telemetry: dict[str, Any], camera_id: str
) -> str | None:
    """Return a safe direct snapshot URL advertised by the paired device."""
    cameras = telemetry.get("cameras", {})
    data = cameras.get(camera_id, {}) if isinstance(cameras, dict) else {}
    url = data.get("snapshot_url") if isinstance(data, dict) else None
    device_ip = telemetry.get("ip_address")
    if (
        not isinstance(url, str)
        or not isinstance(device_ip, str)
        or data.get("transport") != "direct"
    ):
        return None
    parsed = urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname != device_ip
        or parsed.port != DIRECT_CAMERA_PORT
        or not parsed.path.startswith(f"/device_camera/{camera_id}/")
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    return url
