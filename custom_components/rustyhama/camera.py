"""RustyHAMA camera entities."""

from __future__ import annotations

import base64
from typing import Any

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import RustyEntity, async_setup_dynamic_entities
from .models import DeviceRecord


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
        result = await self.manager.async_send_command(
            self.device.device_id,
            "camera_snapshot",
            {"camera_id": self.camera_id, "width": width, "height": height},
            timeout=20,
        )
        encoded = result.get("jpeg")
        return base64.b64decode(encoded) if isinstance(encoded, str) else None

    async def stream_source(self) -> str | None:
        """Return a direct pinned LAN URL when the device advertises one."""
        cameras = self.device.telemetry.get("cameras", {})
        data = cameras.get(self.camera_id, {}) if isinstance(cameras, dict) else {}
        if isinstance(cameras, dict) and not data:
            data = next(
                (
                    item
                    for item in cameras.values()
                    if isinstance(item, dict)
                    and str(item.get("id", "")) == self.camera_id
                ),
                {},
            )
        return data.get("stream_url") if data.get("transport") == "direct" else None


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
