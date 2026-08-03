"""RustyHAMA numeric configuration entities."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import RustyEntity, async_setup_dynamic_entities, nested_patch, nested_value
from .models import DeviceRecord

SPECS = {
    "brightness": ("Brightness", "display.brightness", 0, 100, 1, PERCENTAGE, 100),
    "camera_fps": ("Camera FPS", "device_cameras.stream_fps", 1, 30, 1, "fps", 5),
    "camera_quality": ("Camera JPEG quality", "device_cameras.jpeg_quality", 30, 95, 1, PERCENTAGE, 75),
    "camera_max_width": ("Camera maximum width", "device_cameras.max_width", 320, 1920, 16, "px", 1280),
    "sensor_interval": ("Sensor interval", "sensors.interval", 1, 3600, 1, UnitOfTime.SECONDS, 30),
    "media_volume": ("Media volume", "media_player.volume", 0, 100, 1, PERCENTAGE, 50),
}


class RustyNumber(RustyEntity, NumberEntity):
    _attr_mode = NumberMode.SLIDER

    def __init__(self, manager: Any, device: DeviceRecord, key: str) -> None:
        super().__init__(manager, device, key)
        name, self.path, minimum, maximum, step, unit, self.default = SPECS[key]
        self._attr_name = name
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self) -> float:
        config = self.manager.storage.effective_config(self.device)
        return float(nested_value(config, self.path, self.default))

    async def async_set_native_value(self, value: float) -> None:
        await self.manager.async_update_device_config(
            self.device.device_id, nested_patch(self.path, value)
        )


def _entities(manager: Any, device: DeviceRecord) -> list[RustyNumber]:
    return [RustyNumber(manager, device, key) for key in SPECS]


async def async_setup_entry(
    hass: HomeAssistant, entry: Any, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    await async_setup_dynamic_entities(entry.runtime_data.manager, async_add_entities, _entities)
