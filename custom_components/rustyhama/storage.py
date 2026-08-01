"""Persistent profiles, providers, devices, and revisions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DEFAULT_PROFILE,
    DEFAULT_PROFILE_ID,
    MAX_REVISIONS,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .merge import merge_patch
from .models import DeviceRecord, utc_iso
from .schema import validate_dashboard


class RustyStorage:
    """Home Assistant storage wrapper."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, STORAGE_KEY, private=True)
        self.profiles: dict[str, dict[str, Any]] = {}
        self.providers: dict[str, dict[str, Any]] = {}
        self.devices: dict[str, DeviceRecord] = {}
        self.revisions: list[dict[str, Any]] = []
        self.next_revision = 1

    async def async_load(self) -> None:
        """Load stored state."""
        data = await self._store.async_load() or {}
        self.profiles = data.get("profiles") or {
            DEFAULT_PROFILE_ID: {
                "name": "Default",
                "published": deepcopy(DEFAULT_PROFILE),
                "draft": deepcopy(DEFAULT_PROFILE),
            }
        }
        self.providers = data.get("providers", {})
        self.devices = {
            device_id: DeviceRecord.from_dict(device)
            for device_id, device in data.get("devices", {}).items()
        }
        self.revisions = data.get("revisions", [])[-MAX_REVISIONS:]
        self.next_revision = max(
            int(data.get("next_revision", 1)),
            max((int(item.get("revision", 0)) + 1 for item in self.revisions), default=1),
        )

    async def async_save(self) -> None:
        """Persist state."""
        await self._store.async_save(
            {
                "profiles": self.profiles,
                "providers": self.providers,
                "devices": {
                    device_id: device.persistent_dict()
                    for device_id, device in self.devices.items()
                },
                "revisions": self.revisions[-MAX_REVISIONS:],
                "next_revision": self.next_revision,
            }
        )

    def effective_config(self, device: DeviceRecord) -> dict[str, Any]:
        """Resolve profile and device override without expanding secrets."""
        profile = self.profiles.get(device.profile_id) or self.profiles[DEFAULT_PROFILE_ID]
        config = merge_patch(profile["published"], device.override)
        config["provider_bindings"] = deepcopy(device.provider_bindings)
        config["device"] = {
            "id": device.device_id,
            "name": device.name,
            "display": deepcopy(device.display),
            "capabilities": deepcopy(device.capabilities),
        }
        return config

    async def async_publish_profile(self, profile_id: str) -> int:
        """Publish a draft and create a revision."""
        profile = self.profiles[profile_id]
        validate_dashboard(profile["draft"])
        profile["published"] = deepcopy(profile["draft"])
        revision = self.next_revision
        self.next_revision += 1
        self.revisions.append(
            {
                "revision": revision,
                "profile_id": profile_id,
                "published_at": utc_iso(),
                "config": deepcopy(profile["published"]),
            }
        )
        self.revisions = self.revisions[-MAX_REVISIONS:]
        for device in self.devices.values():
            if device.profile_id == profile_id:
                device.config_revision = revision
        await self.async_save()
        return revision

    async def async_rollback(self, revision: int) -> int:
        """Publish a prior revision as a new monotonic revision."""
        prior = next(
            (item for item in self.revisions if item["revision"] == revision), None
        )
        if prior is None:
            raise KeyError(revision)
        profile = self.profiles[prior["profile_id"]]
        profile["draft"] = deepcopy(prior["config"])
        return await self.async_publish_profile(prior["profile_id"])

    async def async_publish_device(self, device: DeviceRecord) -> int:
        """Create a monotonic revision for a device-only configuration change."""
        validate_dashboard(self.effective_config(device))
        revision = self.next_revision
        self.next_revision += 1
        device.config_revision = revision
        self.revisions.append(
            {
                "revision": revision,
                "device_id": device.device_id,
                "profile_id": device.profile_id,
                "published_at": utc_iso(),
                "config": self.effective_config(device),
            }
        )
        self.revisions = self.revisions[-MAX_REVISIONS:]
        await self.async_save()
        return revision
