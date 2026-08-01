"""RustyHAMA device buttons."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import RustyEntity, async_setup_dynamic_entities
from .models import DeviceRecord

COMMANDS = {
    "reload_configuration": ("Reload configuration", "reload_configuration"),
    "wake_screen": ("Wake screen", "wake_screen"),
    "restart_service": ("Restart foreground service", "restart_service"),
}


class RustyButton(RustyEntity, ButtonEntity):
    def __init__(self, manager: Any, device: DeviceRecord, key: str) -> None:
        super().__init__(manager, device, key)
        self._attr_name, self.command = COMMANDS[key]
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_press(self) -> None:
        if self.command == "reload_configuration":
            await self.manager.async_push_configuration(self.device.device_id)
            return
        await self.manager.async_send_command(self.device.device_id, self.command)


def _entities(manager: Any, device: DeviceRecord) -> list[RustyButton]:
    return [RustyButton(manager, device, key) for key in COMMANDS]


async def async_setup_entry(
    hass: HomeAssistant, entry: Any, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    await async_setup_dynamic_entities(entry.runtime_data.manager, async_add_entities, _entities)
