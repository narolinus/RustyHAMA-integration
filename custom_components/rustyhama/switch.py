"""RustyHAMA configuration switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import (
    RustyEntity,
    async_setup_dynamic_entities,
    local_privacy_locked,
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
        feature = self._privacy_feature()
        if feature is not None and local_privacy_locked(self.device, feature):
            return False
        config = self.manager.storage.effective_config(self.device)
        return bool(nested_value(config, self.path, self.default))

    @property
    def extra_state_attributes(self) -> dict[str, bool] | None:
        feature = self._privacy_feature()
        if feature is None:
            return None
        return {"local_privacy_lock": local_privacy_locked(self.device, feature)}

    def _privacy_feature(self) -> str | None:
        if self.entity_key == "camera_enabled":
            return "camera"
        if self.entity_key in {"voice_enabled", "wake_word"}:
            return "voice_assist"
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        feature = self._privacy_feature()
        if feature is not None and local_privacy_locked(self.device, feature):
            raise HomeAssistantError(
                "This feature is blocked by the local device privacy lock"
            )
        await self.manager.async_update_device_config(
            self.device.device_id, nested_patch(self.path, True)
        )
        if self.entity_key == "camera_enabled":
            registry = er.async_get(self.hass)
            for index, camera in enumerate(
                self.device.capabilities.get("cameras", []) or []
            ):
                camera_id = str(camera.get("id", index)) if isinstance(camera, dict) else str(index)
                entity_id = registry.async_get_entity_id(
                    "camera", DOMAIN, f"{self.device.device_id}_camera_{camera_id}"
                )
                if entity_id is not None:
                    registry.async_update_entity(entity_id, disabled_by=None)

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
