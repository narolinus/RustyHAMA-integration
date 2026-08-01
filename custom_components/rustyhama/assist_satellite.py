"""Real Assist satellite backed by an Android RustyHAMA device."""

from __future__ import annotations

import asyncio
import logging
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

_LOGGER = logging.getLogger(__name__)


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
            self._async_run_pipeline(stream_id, start_stage, end_stage, payload),
            f"RustyHAMA Assist {self.device.device_id}",
        )

    async def _async_run_pipeline(
        self,
        stream_id: str,
        start_stage: PipelineStage,
        end_stage: PipelineStage,
        payload: dict[str, Any],
    ) -> None:
        """Run a pipeline and always release Android from processing state."""
        try:
            await self.async_accept_pipeline_from_satellite(
                self.manager.async_stream(stream_id),
                start_stage=start_stage,
                end_stage=end_stage,
                wake_word_phrase=payload.get("wake_word_phrase"),
            )
        except asyncio.CancelledError:
            raise
        except Exception as err:  # The device must not hang when a HA pipeline fails.
            _LOGGER.exception(
                "Assist pipeline failed for RustyHAMA device %s",
                self.device.device_id,
            )
            await self._async_forward_event(
                "error", {"code": "pipeline_failed", "message": str(err)}
            )
            await self._async_forward_event("run-end", {})

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
        event_type = getattr(event.type, "value", str(event.type))
        self.hass.async_create_task(
            self._async_forward_event(event_type, event.data or {})
        )

    async def _async_forward_event(
        self, event_type: str, data: dict[str, Any]
    ) -> None:
        """Forward one event without leaking background task exceptions."""
        try:
            await self.manager.async_send_event(
                self.device.device_id,
                "assist_event",
                {"type": event_type, "data": data},
            )
        except ConnectionError:
            _LOGGER.debug(
                "Dropping Assist event %s for offline device %s",
                event_type,
                self.device.device_id,
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
