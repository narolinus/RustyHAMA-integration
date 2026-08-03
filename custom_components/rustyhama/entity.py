"""Shared entity helpers for RustyHAMA."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_DEVICE_UPDATED, SIGNAL_DEVICES_CHANGED
from .models import DeviceRecord


def local_privacy_locked(device: DeviceRecord, feature: str) -> bool:
    """Return a device-local privacy lock that HA is not allowed to override."""
    telemetry_locks = device.telemetry.get("privacy_locks")
    if isinstance(telemetry_locks, dict) and feature in telemetry_locks:
        return bool(telemetry_locks[feature])
    capability_locks = device.capabilities.get("privacy_locks")
    return bool(
        isinstance(capability_locks, dict) and capability_locks.get(feature, False)
    )


class RustyEntity(Entity):
    """Base entity backed by a paired Android device."""

    _attr_has_entity_name = True

    def __init__(self, manager: Any, device: DeviceRecord, key: str) -> None:
        self.manager = manager
        self.device = device
        self.entity_key = key
        self._attr_unique_id = f"{device.device_id}_{key}"
        self._attr_config_subentry_id = device.subentry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
            manufacturer="RustyHAMA",
            model=str(device.capabilities.get("model", "Android device")),
            name=device.name,
            sw_version=str(device.telemetry.get("app_version", "unknown")),
            configuration_url=(
                f"homeassistant://navigate/rustyhama/device/{device.device_id}"
            ),
        )

    @property
    def available(self) -> bool:
        """Return whether the live device can accept commands."""
        return self.device.online

    async def async_added_to_hass(self) -> None:
        """Subscribe to the specific device update signal."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_DEVICE_UPDATED, self._async_device_updated
            )
        )

    @callback
    def _async_device_updated(self, device_id: str) -> None:
        if device_id == self.device.device_id:
            self.async_write_ha_state()


async def async_setup_dynamic_entities(
    manager: Any,
    async_add_entities: Callable[[Iterable[Entity]], None],
    factory: Callable[[Any, DeviceRecord], Iterable[Entity]],
) -> None:
    """Add entities now and whenever another device is paired."""
    seen: set[str] = set()

    @callback
    def add_missing() -> None:
        entities: list[Entity] = []
        for device_id, device in manager.storage.devices.items():
            if device_id not in seen:
                seen.add(device_id)
                entities.extend(factory(manager, device))
        if entities:
            async_add_entities(entities)

    add_missing()
    manager.entry.async_on_unload(
        async_dispatcher_connect(manager.hass, SIGNAL_DEVICES_CHANGED, add_missing)
    )


def nested_value(source: dict[str, Any], path: str, default: Any = None) -> Any:
    """Read a dotted value from a nested mapping."""
    value: Any = source
    for segment in path.split("."):
        if not isinstance(value, dict) or segment not in value:
            return default
        value = value[segment]
    return value


def nested_patch(path: str, value: Any) -> dict[str, Any]:
    """Build a merge-patch for one dotted setting path."""
    result: Any = value
    for segment in reversed(path.split(".")):
        result = {segment: result}
    return result
