"""Validation helpers for direct RustyHAMA camera endpoints."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

DIRECT_CAMERA_PORT = 8765


def _validated_direct_camera_url(
    telemetry: dict[str, Any],
    camera_id: str,
    field: str,
    filename: str,
    *,
    expected_port: int,
    expected_base_path: str,
) -> str | None:
    """Return a safe direct camera URL advertised by the paired device."""
    cameras = telemetry.get("cameras", {})
    data = cameras.get(camera_id, {}) if isinstance(cameras, dict) else {}
    url = data.get(field) if isinstance(data, dict) else None
    device_ip = telemetry.get("ip_address")
    if (
        not isinstance(url, str)
        or not isinstance(device_ip, str)
        or data.get("transport") != "direct"
    ):
        return None
    parsed = urlsplit(url)
    base_path = "/" + expected_base_path.strip("/")
    if (
        parsed.scheme != "http"
        or parsed.hostname != device_ip
        or parsed.port != expected_port
        or parsed.path != f"{base_path}/{camera_id}/{filename}"
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    return url


def validated_direct_snapshot_url(
    telemetry: dict[str, Any],
    camera_id: str,
    *,
    expected_port: int = DIRECT_CAMERA_PORT,
    expected_base_path: str = "/device_camera",
) -> str | None:
    """Return a safe direct snapshot URL advertised by the paired device."""
    return _validated_direct_camera_url(
        telemetry,
        camera_id,
        "snapshot_url",
        "snapshot.jpg",
        expected_port=expected_port,
        expected_base_path=expected_base_path,
    )


def validated_direct_stream_url(
    telemetry: dict[str, Any],
    camera_id: str,
    *,
    expected_port: int = DIRECT_CAMERA_PORT,
    expected_base_path: str = "/device_camera",
) -> str | None:
    """Return a safe direct MJPEG URL advertised by the paired device."""
    return _validated_direct_camera_url(
        telemetry,
        camera_id,
        "stream_url",
        "stream.mjpeg",
        expected_port=expected_port,
        expected_base_path=expected_base_path,
    )
