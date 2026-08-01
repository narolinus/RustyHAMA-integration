"""RustyHAMA configuration switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import (
    RustyEntity,
    async_setup_dynamic_entities,
    nested_patch,
    nested_value,
)
from .models import DeviceRecord

SPECS = {
    "keep_screen_on": ("Keep screen on", "app.keep_screen_on", True),
    "voice_enabled": ("Voice satellite", "voice_assistant.enabled", False),
    "wake_word": ("Wake word", "voice_assistant.wake_word", False),
    "screensaver_enabled": ("Screensaver", "screensaver.enabled", False),
    "camera_enabled": ("Camera", "device_cameras.enabled", False),
    "autostart": ("Autostart", "service.autostart", True),
    "media_player_enabled": ("Media player", "media_player.enabled", False),
}


class RustySwitch(RustyEntity, SwitchEntity):
    def __init__(self, manager: Any, device: DeviceRecord, key: str) -> None:
        super().__init__(manager, device, key)
        self._attr_name, self.path, self.default = SPECS[key]
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        config = self.manager.storage.effective_config(self.device)
        return bool(nested_value(config, self.path, self.default))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.manager.async_update_device_config(
            self.device.device_id, nested_patch(self.path, True)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.manager.async_update_device_config(
            self.device.device_id, nested_patch(self.path, False)
        )


def _entities(manager: Any, device: DeviceRecord) -> list[RustySwitch]:
    return [RustySwitch(manager, device, key) for key in SPECS]


async def async_setup_entry(
    hass: HomeAssistant, entry: Any, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    await async_setup_dynamic_entities(entry.runtime_data.manager, async_add_entities, _entities)
