"""Real Assist satellite backed by an Android RustyHAMA device."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from homeassistant.components import wake_word
from homeassistant.components.assist_pipeline import (
    PipelineEvent,
    PipelineStage,
    async_get_pipeline,
)
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
        self._available_wake_words: list[AssistSatelliteWakeWord] = []

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_ASSIST_START, self._async_assist_start
            )
        )
        await self._async_refresh_wake_words()
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
            selected = self._selected_wake_word()
            if start_stage is PipelineStage.WAKE_WORD and selected:
                await self._async_accept_selected_server_wake_word(
                    stream_id, selected, end_stage
                )
            else:
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
        active = (
            self.manager.storage.effective_config(self.device)
            .get("voice_assistant", {})
            .get("active_wake_words", [])
        )
        return AssistSatelliteConfiguration(
            available_wake_words=list(self._available_wake_words),
            active_wake_words=list(active) if isinstance(active, list) else [],
            max_active_wake_words=1,
        )

    async def async_set_configuration(
        self, config: AssistSatelliteConfiguration
    ) -> None:
        await self.manager.async_update_device_config(
            self.device.device_id,
            {"voice_assistant": {"active_wake_words": config.active_wake_words}},
        )

    async def _async_refresh_wake_words(self) -> None:
        """Cache wake words offered by the selected server-side engine."""
        try:
            pipeline = async_get_pipeline(self.hass, pipeline_id=self._resolve_pipeline())
            entity_id = pipeline.wake_word_entity or wake_word.async_default_entity(self.hass)
            if not entity_id:
                return
            engine = wake_word.async_get_wake_word_detection_entity(self.hass, entity_id)
            if engine is None:
                return
            supported = await engine.get_supported_wake_words()
            self._available_wake_words = [
                AssistSatelliteWakeWord(
                    id=str(item.id),
                    wake_word=str(item.phrase or item.name or item.id),
                    trained_languages=[],
                )
                for item in supported
            ]
            self.async_write_ha_state()
        except (AttributeError, RuntimeError):
            _LOGGER.debug("No server wake-word catalogue available", exc_info=True)

    def _selected_wake_word(self) -> str | None:
        active = self.async_get_configuration().active_wake_words
        return active[0] if active else None

    async def _async_accept_selected_server_wake_word(
        self, stream_id: str, wake_word_id: str, end_stage: PipelineStage
    ) -> None:
        """Run the chosen server wake word, then continue the same stream at STT."""
        pipeline = async_get_pipeline(self.hass, pipeline_id=self._resolve_pipeline())
        entity_id = pipeline.wake_word_entity or wake_word.async_default_entity(self.hass)
        if not entity_id:
            raise RuntimeError("No wake word engine")
        engine = wake_word.async_get_wake_word_detection_entity(self.hass, entity_id)
        if engine is None:
            raise RuntimeError(f"Wake word engine not found: {entity_id}")

        raw_stream = self.manager.async_stream(stream_id)
        elapsed_ms = 0

        async def timed_audio() -> AsyncIterator[tuple[bytes, int]]:
            nonlocal elapsed_ms
            async for chunk in raw_stream:
                timestamp = elapsed_ms
                elapsed_ms += max(1, len(chunk) // 32)
                yield chunk, timestamp

        timed_iterator = timed_audio().__aiter__()
        result = await engine.async_process_audio_stream(timed_iterator, wake_word_id)
        if result is None:
            return

        async def speech_audio() -> AsyncIterator[bytes]:
            for chunk, _timestamp in result.queued_audio or []:
                yield chunk
            async for chunk, _timestamp in timed_iterator:
                yield chunk

        await self.async_accept_pipeline_from_satellite(
            speech_audio(),
            start_stage=PipelineStage.STT,
            end_stage=end_stage,
            wake_word_phrase=result.wake_word_phrase,
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
