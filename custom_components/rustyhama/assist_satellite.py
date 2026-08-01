"""Real Assist satellite backed by an Android RustyHAMA device."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.assist_pipeline import PipelineEvent, PipelineStage
from homeassistant.components.assist_satellite import (
    AssistSatelliteAnnouncement,
    AssistSatelliteConfiguration,
    AssistSatelliteEntity,
    AssistSatelliteEntityFeature,
    AssistSatelliteWakeWord,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SIGNAL_ASSIST_EVENT, SIGNAL_ASSIST_START
from .entity import RustyEntity, async_setup_dynamic_entities
from .models import DeviceRecord


class RustyAssistSatellite(RustyEntity, AssistSatelliteEntity):
    """Stream Android microphone audio through a Home Assistant pipeline."""

    _attr_name = "Assist satellite"
    _attr_supported_features = (
        AssistSatelliteEntityFeature.ANNOUNCE
        | AssistSatelliteEntityFeature.START_CONVERSATION
    )

    def __init__(self, manager: Any, device: DeviceRecord) -> None:
        super().__init__(manager, device, "assist_satellite")
        self._accept_task: asyncio.Task[Any] | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_ASSIST_START, self._async_assist_start
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_ASSIST_EVENT, self._async_assist_event
            )
        )

    @callback
    def _async_assist_start(self, device_id: str, payload: dict[str, Any]) -> None:
        if device_id != self.device.device_id:
            return
        if self._accept_task and not self._accept_task.done():
            self._accept_task.cancel()
        stream_id = str(payload["stream_id"])
        start_stage = PipelineStage(str(payload.get("start_stage", "stt")))
        end_stage = PipelineStage(str(payload.get("end_stage", "tts")))
        self._accept_task = self.hass.async_create_task(
            self.async_accept_pipeline_from_satellite(
                self.manager.async_stream(stream_id),
                start_stage=start_stage,
                end_stage=end_stage,
                wake_word_phrase=payload.get("wake_word_phrase"),
            ),
            f"RustyHAMA Assist {self.device.device_id}",
        )

    @callback
    def async_get_configuration(self) -> AssistSatelliteConfiguration:
        wake_words = [
            AssistSatelliteWakeWord(
                id=str(item["id"]),
                wake_word=str(item.get("wake_word", item["id"])),
                trained_languages=list(item.get("trained_languages", [])),
            )
            for item in self.device.capabilities.get("wake_words", [])
            if isinstance(item, dict) and item.get("id")
        ]
        active = self.device.telemetry.get("active_wake_words", [])
        return AssistSatelliteConfiguration(
            available_wake_words=wake_words,
            active_wake_words=list(active) if isinstance(active, list) else [],
            max_active_wake_words=1,
        )

    async def async_set_configuration(
        self, config: AssistSatelliteConfiguration
    ) -> None:
        await self.manager.async_send_command(
            self.device.device_id,
            "assist_configuration",
            {"active_wake_words": config.active_wake_words},
        )

    @callback
    def _async_assist_event(
        self, device_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        if device_id != self.device.device_id:
            return
        if event_type == "tts_finished":
            self.tts_response_finished()

    @callback
    def on_pipeline_event(self, event: PipelineEvent) -> None:
        """Forward state, transcript, and TTS media events to Android."""
        self.hass.async_create_task(
            self.manager.async_send_event(
                self.device.device_id,
                "assist_event",
                {"type": str(event.type), "data": event.data or {}},
            )
        )

    async def async_announce(
        self, announcement: AssistSatelliteAnnouncement
    ) -> None:
        await self.manager.async_send_command(
            self.device.device_id,
            "assist_announce",
            {
                "media_id": announcement.media_id,
                "message": announcement.message,
                "original_media_id": announcement.original_media_id,
                "media_id_source": announcement.media_id_source,
                "tts_token": announcement.tts_token,
                "preannounce_media_id": announcement.preannounce_media_id,
            },
            timeout=60,
        )

    async def async_start_conversation(
        self, start_announcement: AssistSatelliteAnnouncement
    ) -> None:
        await self.async_announce(start_announcement)
        await self.manager.async_send_command(
            self.device.device_id,
            "assist_start_listening",
        )


def _entities(manager: Any, device: DeviceRecord) -> list[RustyAssistSatellite]:
    return [RustyAssistSatellite(manager, device)]


async def async_setup_entry(
    hass: HomeAssistant, entry: Any, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    await async_setup_dynamic_entities(entry.runtime_data.manager, async_add_entities, _entities)
