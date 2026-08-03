"""RustyHAMA binary sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import RustyEntity, async_setup_dynamic_entities, local_privacy_locked
from .models import DeviceRecord

SPECS = {
    "online": ("Online", BinarySensorDeviceClass.CONNECTIVITY),
    "charging": ("Charging", BinarySensorDeviceClass.BATTERY_CHARGING),
    "screensaver": ("Screensaver", BinarySensorDeviceClass.RUNNING),
    "voice": ("Voice service", BinarySensorDeviceClass.RUNNING),
    "camera": ("Camera service", BinarySensorDeviceClass.RUNNING),
    "service": ("Foreground service", BinarySensorDeviceClass.RUNNING),
    "camera_privacy_lock": ("Camera privacy lock", None),
    "voice_privacy_lock": ("Voice privacy lock", None),
}


class RustyBinarySensor(RustyEntity, BinarySensorEntity):
    def __init__(self, manager: Any, device: DeviceRecord, key: str) -> None:
        super().__init__(manager, device, key)
        self._attr_name, self._attr_device_class = SPECS[key]
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        if self.entity_key == "online":
            return self.device.online
        if self.entity_key == "camera_privacy_lock":
            return local_privacy_locked(self.device, "camera")
        if self.entity_key == "voice_privacy_lock":
            return local_privacy_locked(self.device, "voice_assist")
        return bool(self.device.telemetry.get(self.entity_key))

    @property
    def available(self) -> bool:
        return True if self.entity_key == "online" else self.device.online


def _entities(manager: Any, device: DeviceRecord) -> list[RustyBinarySensor]:
    return [RustyBinarySensor(manager, device, key) for key in SPECS]


async def async_setup_entry(
    hass: HomeAssistant, entry: Any, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    await async_setup_dynamic_entities(entry.runtime_data.manager, async_add_entities, _entities)
