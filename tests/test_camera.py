"""Tests for RustyHAMA direct camera endpoint validation."""

from typing import Any

from custom_components.rustyhama.camera_url import (
    validated_direct_snapshot_url,
    validated_direct_stream_url,
)


def _telemetry(
    snapshot_url: str,
    *,
    stream_url: str = "http://172.20.19.2:8765/device_camera/0/stream.mjpeg",
    transport: str = "direct",
) -> dict[str, Any]:
    return {
        "ip_address": "172.20.19.2",
        "cameras": {
            "0": {
                "snapshot_url": snapshot_url,
                "stream_url": stream_url,
                "transport": transport,
            }
        },
    }


def test_direct_snapshot_url_accepts_advertised_device_endpoint() -> None:
    """The advertised camera endpoint on the device IP and port is accepted."""
    url = "http://172.20.19.2:8765/device_camera/0/snapshot.jpg"

    assert validated_direct_snapshot_url(_telemetry(url), "0") == url


def test_direct_snapshot_url_rejects_untrusted_targets() -> None:
    """Device telemetry cannot turn the HA camera entity into an SSRF proxy."""
    assert (
        validated_direct_snapshot_url(
            _telemetry("http://172.20.19.3:8765/device_camera/0/snapshot.jpg"), "0"
        )
        is None
    )
    assert (
        validated_direct_snapshot_url(
            _telemetry("http://172.20.19.2:8123/device_camera/0/snapshot.jpg"), "0"
        )
        is None
    )
    assert (
        validated_direct_snapshot_url(
            _telemetry("http://172.20.19.2:8765/device_camera/1/snapshot.jpg"), "0"
        )
        is None
    )
    assert (
        validated_direct_snapshot_url(
            _telemetry(
                "http://172.20.19.2:8765/device_camera/0/snapshot.jpg",
                transport="tunnel",
            ),
            "0",
        )
        is None
    )


def test_direct_camera_url_supports_configured_endpoint() -> None:
    """Configured ports and base paths are accepted without widening the target."""
    snapshot = "http://172.20.19.2:9876/rusty/cam/0/snapshot.jpg"

    assert (
        validated_direct_snapshot_url(
            _telemetry(snapshot),
            "0",
            expected_port=9876,
            expected_base_path="/rusty/cam",
        )
        == snapshot
    )


def test_direct_stream_url_accepts_only_advertised_device_endpoint() -> None:
    """The stream proxy cannot be redirected to another host, port, or path."""
    snapshot = "http://172.20.19.2:8765/device_camera/0/snapshot.jpg"
    stream = "http://172.20.19.2:8765/device_camera/0/stream.mjpeg"

    assert validated_direct_stream_url(_telemetry(snapshot), "0") == stream
    assert (
        validated_direct_stream_url(
            _telemetry(snapshot, stream_url=stream + "?redirect=1"), "0"
        )
        is None
    )
    assert (
        validated_direct_stream_url(
            _telemetry(
                snapshot,
                stream_url="http://172.20.19.3:8765/device_camera/0/stream.mjpeg",
            ),
            "0",
        )
        is None
    )
