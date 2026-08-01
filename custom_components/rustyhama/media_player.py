"""Optional RustyHAMA Android media player."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.components.media_player.const import MediaPlayerState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import RustyEntity, async_setup_dynamic_entities
from .models import DeviceRecord

FEATURES = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PLAY_MEDIA
    | MediaPlayerEntityFeature.SEEK
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_SET
)


class RustyMediaPlayer(RustyEntity, MediaPlayerEntity):
    _attr_name = "Media player"
    _attr_supported_features = FEATURES
    _attr_entity_registry_enabled_default = False

    def __init__(self, manager: Any, device: DeviceRecord) -> None:
        super().__init__(manager, device, "media_player")

    @property
    def state(self) -> MediaPlayerState:
        value = str(self.device.telemetry.get("media_state", "idle"))
        try:
            return MediaPlayerState(value)
        except ValueError:
            return MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float | None:
        value = self.device.telemetry.get("media_volume")
        return float(value) if value is not None else None

    @property
    def is_volume_muted(self) -> bool | None:
        return self.device.telemetry.get("media_muted")

    @property
    def media_position(self) -> int | None:
        value = self.device.telemetry.get("media_position")
        return int(value) if value is not None else None

    @property
    def media_duration(self) -> int | None:
        value = self.device.telemetry.get("media_duration")
        return int(value) if value is not None else None

    @property
    def media_title(self) -> str | None:
        return self.device.telemetry.get("media_title")

    @property
    def media_image_url(self) -> str | None:
        return self.device.telemetry.get("media_image_url")

    async def _command(self, command: str, **payload: Any) -> None:
        await self.manager.async_send_command(self.device.device_id, command, payload)

    async def async_media_play(self) -> None:
        await self._command("media_play")

    async def async_media_pause(self) -> None:
        await self._command("media_pause")

    async def async_media_stop(self) -> None:
        await self._command("media_stop")

    async def async_media_seek(self, position: float) -> None:
        await self._command("media_seek", position=position)

    async def async_set_volume_level(self, volume: float) -> None:
        await self._command("media_volume", volume=volume)

    async def async_mute_volume(self, mute: bool) -> None:
        await self._command("media_mute", mute=mute)

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        await self._command(
            "media_play_url", media_type=media_type, url=media_id, metadata=kwargs
        )


def _entities(manager: Any, device: DeviceRecord) -> list[RustyMediaPlayer]:
    return [RustyMediaPlayer(manager, device)]


async def async_setup_entry(
    hass: HomeAssistant, entry: Any, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    await async_setup_dynamic_entities(entry.runtime_data.manager, async_add_entities, _entities)
