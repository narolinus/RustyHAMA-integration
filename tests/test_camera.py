"""Tests for the RustyHAMA camera entity."""

from types import SimpleNamespace

from custom_components.rustyhama.camera import RustyCamera
from custom_components.rustyhama.models import DeviceRecord


def _camera(snapshot_url: str, *, transport: str = "direct") -> RustyCamera:
    device = DeviceRecord(
        device_id="device-1",
        name="Test tablet",
        token_hash="hash",
        subentry_id="subentry-1",
        telemetry={
            "ip_address": "172.20.19.2",
            "cameras": {
                "0": {
                    "snapshot_url": snapshot_url,
                    "transport": transport,
                }
            },
        },
    )
    return RustyCamera(SimpleNamespace(), device, "0")


def test_direct_snapshot_url_accepts_advertised_device_endpoint() -> None:
    """The advertised camera endpoint on the device IP and port is accepted."""
    url = "http://172.20.19.2:8765/device_camera/0/snapshot.jpg"

    assert _camera(url)._direct_snapshot_url() == url


def test_direct_snapshot_url_rejects_untrusted_targets() -> None:
    """Device telemetry cannot turn the HA camera entity into an SSRF proxy."""
    assert (
        _camera(
            "http://172.20.19.3:8765/device_camera/0/snapshot.jpg"
        )._direct_snapshot_url()
        is None
    )
    assert (
        _camera(
            "http://172.20.19.2:8123/device_camera/0/snapshot.jpg"
        )._direct_snapshot_url()
        is None
    )
    assert (
        _camera(
            "http://172.20.19.2:8765/device_camera/1/snapshot.jpg"
        )._direct_snapshot_url()
        is None
    )
    assert (
        _camera(
            "http://172.20.19.2:8765/device_camera/0/snapshot.jpg",
            transport="tunnel",
        )._direct_snapshot_url()
        is None
    )
