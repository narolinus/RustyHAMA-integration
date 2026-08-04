"""RustyHAMA select configuration entities."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import wake_word
from homeassistant.components.assist_pipeline import async_get_pipeline
from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import RustyEntity, async_setup_dynamic_entities, nested_patch, nested_value
from .models import DeviceRecord

_LOGGER = logging.getLogger(__name__)

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


class WakeWordSelect(RustyEntity, SelectEntity):
    """Expose the server wake-word catalogue as an explicit device setting."""

    _attr_name = "Wake word model"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager: Any, device: DeviceRecord) -> None:
        super().__init__(manager, device, "wake_word_model")
        self._attr_options = []

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._async_refresh_options()

    @property
    def current_option(self) -> str | None:
        active = (
            self.manager.storage.effective_config(self.device)
            .get("voice_assistant", {})
            .get("active_wake_words", [])
        )
        selected = str(active[0]) if isinstance(active, list) and active else None
        return selected if selected in self.options else None

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ValueError(f"Unsupported wake word: {option}")
        await self.manager.async_update_device_config(
            self.device.device_id,
            {"voice_assistant": {"active_wake_words": [option]}},
        )

    async def _async_refresh_options(self) -> None:
        try:
            pipeline = async_get_pipeline(self.hass, pipeline_id=None)
            entity_id = pipeline.wake_word_entity or wake_word.async_default_entity(
                self.hass
            )
            engine = (
                wake_word.async_get_wake_word_detection_entity(self.hass, entity_id)
                if entity_id
                else None
            )
            if engine is None:
                return
            supported = await engine.get_supported_wake_words()
            self._attr_options = [str(item.id) for item in supported]
            self.async_write_ha_state()
        except (AttributeError, RuntimeError):
            _LOGGER.debug("No server wake-word catalogue available", exc_info=True)


def _entities(manager: Any, device: DeviceRecord) -> list[SelectEntity]:
    return [
        ProfileSelect(manager, device),
        WakeWordSelect(manager, device),
        *(RustySelect(manager, device, key) for key in SPECS),
    ]


async def async_setup_entry(
    hass: HomeAssistant, entry: Any, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    await async_setup_dynamic_entities(entry.runtime_data.manager, async_add_entities, _entities)
