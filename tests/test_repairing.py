"""Re-pairing regression tests."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.rustyhama.manager import RustyManager, token_hash
from custom_components.rustyhama.models import DeviceRecord, DeviceSession, PairingRequest


def manager_with_device(device: DeviceRecord) -> RustyManager:
    """Build the manager surface needed by the isolated pairing tests."""
    manager = object.__new__(RustyManager)
    manager.hass = object()
    manager.storage = SimpleNamespace(
        devices={device.device_id: device},
        async_save=AsyncMock(),
    )
    manager.pairings = {}
    manager.sessions = {}
    manager._watchdog_tasks = {}
    manager._refresh_tasks = {}
    manager._compiled = {}
    manager._compile = lambda current: SimpleNamespace(
        config={"device": {"id": current.device_id}}
    )
    manager._signal_device = MagicMock()
    return manager


@pytest.mark.asyncio
async def test_create_repairing_targets_existing_device_settings() -> None:
    """The authorization binds to an existing record instead of copying settings."""
    device = DeviceRecord(
        "device-1",
        "Kitchen tablet",
        "old-hash",
        "subentry-1",
        profile_id="kitchen",
        area_id="kitchen-area",
        override={"theme": {"accent_color": "#123456"}},
        provider_bindings={"photos": "immich-main"},
    )
    manager = manager_with_device(device)

    result = await manager.async_create_repairing(
        device.device_id, public_key_pin="sha256/example"
    )

    request = next(iter(manager.pairings.values()))
    assert request.device_id == device.device_id
    assert request.name == device.name
    assert request.profile_id == device.profile_id
    assert request.area_id == device.area_id
    assert result["public_key_pin"] == "sha256/example"
    assert device.override == {"theme": {"accent_color": "#123456"}}
    assert device.provider_bindings == {"photos": "immich-main"}


@pytest.mark.asyncio
async def test_complete_repairing_reuses_identity_and_revokes_old_installation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful re-pair keeps HA configuration but rotates runtime identity."""
    device = DeviceRecord(
        "device-1",
        "Kitchen tablet",
        token_hash("old-credential"),
        "subentry-1",
        profile_id="kitchen",
        area_id="kitchen-area",
        override={"theme": {"accent_color": "#123456"}},
        provider_bindings={"photos": "immich-main"},
        capabilities={"model": "Old tablet"},
        display={"width_px": 800},
        telemetry={"privacy_locks": {"camera": True}},
        config_revision=42,
        acknowledged_revision=42,
        online=True,
    )
    device.recent_message_ids.append("old-message")
    manager = manager_with_device(device)
    websocket = SimpleNamespace(closed=False, close=AsyncMock())
    manager.sessions[device.device_id] = DeviceSession(device.device_id, websocket, 1)
    watchdog = MagicMock()
    refresh = MagicMock()
    manager._watchdog_tasks[device.device_id] = watchdog
    manager._refresh_tasks[device.device_id] = refresh
    pairing = PairingRequest(
        token_hash("12345678"),
        token_hash("qr-token"),
        device.name,
        device.profile_id,
        device.area_id,
        time.time() + 600,
        device_id=device.device_id,
    )
    stale_pairing = PairingRequest(
        token_hash("87654321"),
        token_hash("stale-qr"),
        device.name,
        device.profile_id,
        device.area_id,
        time.time() + 600,
        device_id=device.device_id,
    )
    other_pairing = PairingRequest(
        token_hash("11223344"),
        token_hash("other-qr"),
        "Other tablet",
        "default",
        None,
        time.time() + 600,
    )
    manager.pairings = {
        pairing.code_hash: pairing,
        stale_pairing.code_hash: stale_pairing,
        other_pairing.code_hash: other_pairing,
    }
    monkeypatch.setattr(
        "custom_components.rustyhama.manager.async_dispatcher_send",
        MagicMock(),
    )

    result = await manager.async_complete_pairing(
        {
            "code": "12345678",
            "capabilities": {"model": "Reinstalled tablet"},
            "display": {"width_px": 1280},
        }
    )

    assert result["device_id"] == device.device_id
    assert result["config_revision"] == 42
    assert manager.authenticate(device.device_id, "old-credential") is None
    assert manager.authenticate(device.device_id, result["credential"]) is device
    assert device.profile_id == "kitchen"
    assert device.area_id == "kitchen-area"
    assert device.override == {"theme": {"accent_color": "#123456"}}
    assert device.provider_bindings == {"photos": "immich-main"}
    assert device.capabilities == {"model": "Reinstalled tablet"}
    assert device.display == {"width_px": 1280}
    assert device.telemetry == {}
    assert device.acknowledged_revision == 0
    assert device.online is False
    assert list(device.recent_message_ids) == []
    assert list(manager.pairings.values()) == [other_pairing]
    watchdog.cancel.assert_called_once_with()
    refresh.cancel.assert_called_once_with()
    websocket.close.assert_awaited_once_with(code=4003, message=b"re-paired")
    manager.storage.async_save.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_repairing_storage_failure_keeps_old_credential() -> None:
    """A failed private-storage write must not strand the existing device record."""
    device = DeviceRecord(
        "device-1",
        "Kitchen tablet",
        token_hash("old-credential"),
        "subentry-1",
        telemetry={"battery": 80},
        acknowledged_revision=7,
        online=True,
    )
    manager = manager_with_device(device)
    manager.storage.async_save.side_effect = OSError("storage unavailable")
    pairing = PairingRequest(
        token_hash("12345678"),
        token_hash("qr-token"),
        device.name,
        device.profile_id,
        device.area_id,
        time.time() + 600,
        device_id=device.device_id,
    )
    manager.pairings = {pairing.code_hash: pairing}

    with pytest.raises(OSError, match="storage unavailable"):
        await manager.async_complete_pairing({"code": "12345678"})

    assert manager.authenticate(device.device_id, "old-credential") is device
    assert device.telemetry == {"battery": 80}
    assert device.acknowledged_revision == 7
    assert device.online is True
    assert manager.pairings == {pairing.code_hash: pairing}
