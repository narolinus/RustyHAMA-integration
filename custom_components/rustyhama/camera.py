"""RustyHAMA camera entities."""

from __future__ import annotations

import base64
import logging
from typing import Any

from aiohttp import ClientError, ClientTimeout, web
from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import (
    async_aiohttp_proxy_web,
    async_get_clientsession,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .camera_url import validated_direct_snapshot_url, validated_direct_stream_url
from .entity import RustyEntity, async_setup_dynamic_entities
from .models import DeviceRecord

_LOGGER = logging.getLogger(__name__)
_MAX_SNAPSHOT_BYTES = 10 * 1024 * 1024


class RustyCamera(RustyEntity, Camera):
    """HA-proxied Android camera."""

    _attr_name = "Camera"
    _attr_supported_features = CameraEntityFeature.STREAM
    # Keep camera entities visible. The RustyHAMA camera switch controls runtime
    # availability; hiding both the entity and the switch made initial setup opaque.
    _attr_entity_registry_enabled_default = True

    def __init__(self, manager: Any, device: DeviceRecord, camera_id: str) -> None:
        RustyEntity.__init__(self, manager, device, f"camera_{camera_id}")
        Camera.__init__(self)
        self.camera_id = camera_id
        self._attr_name = f"Camera {camera_id}"

    @property
    def available(self) -> bool:
        """Return availability only while camera service and device are online."""
        config = self.manager.storage.effective_config(self.device).get(
            "device_cameras", {}
        )
        return bool(
            self.device.online
            and isinstance(config, dict)
            and config.get("enabled", False)
        )

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a snapshot without burdening the persistent control channel."""
        direct_url = self._direct_snapshot_url()
        if direct_url is not None:
            try:
                session = async_get_clientsession(self.hass)
                async with session.get(
                    direct_url, timeout=ClientTimeout(total=5)
                ) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "")
                    if not content_type.lower().startswith("image/"):
                        raise ValueError("camera_response_is_not_an_image")
                    snapshot = await response.read()
                    if not snapshot or len(snapshot) > _MAX_SNAPSHOT_BYTES:
                        raise ValueError("camera_response_has_invalid_size")
                    return snapshot
            except (ClientError, TimeoutError, ValueError):
                _LOGGER.debug(
                    "Direct RustyHAMA camera snapshot failed for %s camera %s; "
                    "falling back to the device channel",
                    self.device.device_id,
                    self.camera_id,
                    exc_info=True,
                )

        result = await self.manager.async_send_command(
            self.device.device_id,
            "camera_snapshot",
            {"camera_id": self.camera_id, "width": width, "height": height},
            timeout=4,
        )
        encoded = result.get("jpeg")
        return base64.b64decode(encoded) if isinstance(encoded, str) else None

    def _direct_snapshot_url(self) -> str | None:
        """Return a validated direct snapshot URL advertised by this device."""
        config = self.manager.storage.effective_config(self.device).get(
            "device_cameras", {}
        )
        if not isinstance(config, dict):
            return None
        return validated_direct_snapshot_url(
            self.device.telemetry,
            self.camera_id,
            expected_port=int(config.get("port", 8765)),
            expected_base_path=str(config.get("base_path", "/device_camera")),
        )

    def _direct_stream_url(self) -> str | None:
        """Return a validated direct MJPEG URL advertised by this device."""
        config = self.manager.storage.effective_config(self.device).get(
            "device_cameras", {}
        )
        if not isinstance(config, dict):
            return None
        return validated_direct_stream_url(
            self.device.telemetry,
            self.camera_id,
            expected_port=int(config.get("port", 8765)),
            expected_base_path=str(config.get("base_path", "/device_camera")),
        )

    async def handle_async_mjpeg_stream(
        self, request: web.Request
    ) -> web.StreamResponse | None:
        """Proxy the native device MJPEG stream without reducing its frame rate."""
        direct_url = self._direct_stream_url()
        if direct_url is None:
            return await super().handle_async_mjpeg_stream(request)

        session = async_get_clientsession(self.hass)
        try:
            return await async_aiohttp_proxy_web(
                self.hass,
                request,
                session.get(
                    direct_url,
                    timeout=ClientTimeout(
                        total=None, connect=5, sock_connect=5, sock_read=None
                    ),
                ),
                timeout=20,
            )
        except web.HTTPException:
            _LOGGER.debug(
                "Direct RustyHAMA MJPEG stream failed for %s camera %s",
                self.device.device_id,
                self.camera_id,
                exc_info=True,
            )
            return await super().handle_async_mjpeg_stream(request)

    async def stream_source(self) -> str | None:
        """Return a direct pinned LAN URL when the device advertises one."""
        return self._direct_stream_url()


def _entities(manager: Any, device: DeviceRecord) -> list[RustyCamera]:
    cameras = device.capabilities.get("cameras", [])
    if not isinstance(cameras, list):
        return []
    return [
        RustyCamera(manager, device, str(camera.get("id", index)))
        for index, camera in enumerate(cameras)
        if isinstance(camera, dict) and camera.get("enabled", True)
    ]


async def async_setup_entry(
    hass: HomeAssistant, entry: Any, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    await async_setup_dynamic_entities(entry.runtime_data.manager, async_add_entities, _entities)
