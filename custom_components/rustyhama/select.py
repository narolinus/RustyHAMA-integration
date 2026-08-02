"""RustyHAMA select configuration entities."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import RustyEntity, async_setup_dynamic_entities, nested_patch, nested_value
from .models import DeviceRecord

SPECS = {
    "active_tab": ("Active tab", "runtime.active_tab", ["0"], "0"),
    "audio_route": (
        "Audio route",
        "voice_assistant.audio_route",
        ["system", "speakerphone", "earpiece"],
        "system",
    ),
    "vad": ("Voice activity detection", "voice_assistant.vad", ["server", "device"], "server"),
    "camera_transport": ("Camera transport", "device_cameras.transport", ["direct", "tunnel"], "direct"),
}


class RustySelect(RustyEntity, SelectEntity):
    def __init__(self, manager: Any, device: DeviceRecord, key: str) -> None:
        super().__init__(manager, device, key)
        self._attr_name, self.path, options, self.default = SPECS[key]
        self._attr_options = options
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def options(self) -> list[str]:
        if self.entity_key == "active_tab":
            tabs = self.manager.storage.effective_config(self.device).get("tabs", [])
            return [str(tab.get("id", index)) for index, tab in enumerate(tabs)] or ["0"]
        return list(self._attr_options)

    @property
    def current_option(self) -> str:
        config = self.manager.storage.effective_config(self.device)
        return str(nested_value(config, self.path, self.default))

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ValueError(f"Unsupported option: {option}")
        await self.manager.async_update_device_config(
            self.device.device_id, nested_patch(self.path, option)
        )


class ProfileSelect(RustyEntity, SelectEntity):
    _attr_name = "Profile"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager: Any, device: DeviceRecord) -> None:
        super().__init__(manager, device, "profile")

    @property
    def options(self) -> list[str]:
        return sorted(self.manager.storage.profiles)

    @property
    def current_option(self) -> str:
        return self.device.profile_id

    async def async_select_option(self, option: str) -> None:
        if option not in self.manager.storage.profiles:
            raise ValueError(f"Unknown profile: {option}")
        self.device.profile_id = option
        await self.manager.storage.async_publish_device(self.device)
        await self.manager.async_push_configuration(self.device.device_id)


def _entities(manager: Any, device: DeviceRecord) -> list[SelectEntity]:
    return [ProfileSelect(manager, device), *(RustySelect(manager, device, key) for key in SPECS)]


async def async_setup_entry(
    hass: HomeAssistant, entry: Any, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    await async_setup_dynamic_entities(entry.runtime_data.manager, async_add_entities, _entities)
