"""RustyHAMA Home Assistant integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import panel_custom
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .api import register_http_views
from .const import (
    DOMAIN,
    PANEL_PATH,
    PANEL_URL,
    PLATFORMS,
    SERVICE_RELOAD_CONFIGURATION,
    SERVICE_SEND_NOTIFICATION,
    SERVICE_SET_ACTIVE_TAB,
    SERVICE_SET_SCREENSAVER,
)
from .manager import RustyManager
from .models import RuntimeData
from .websocket_api import register_websocket_commands

type RustyConfigEntry = ConfigEntry[RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: RustyConfigEntry) -> bool:
    """Set up RustyHAMA from a config entry."""
    manager = RustyManager(hass, entry)
    await manager.async_setup()
    entry.runtime_data = RuntimeData(manager=manager)
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data["manager"] = manager

    if not domain_data.get("api_registered"):
        register_http_views(hass)
        register_websocket_commands(hass)
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL,
            webcomponent_name="rustyhama-panel",
            sidebar_title="RustyHAMA",
            sidebar_icon="mdi:tablet-dashboard",
            module_url=f"{PANEL_PATH}/panel.js",
            require_admin=True,
            config_panel_domain=DOMAIN,
        )
        _register_services(hass)
        domain_data["api_registered"] = True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RustyConfigEntry) -> bool:
    """Unload platforms and detach all transports owned by this manager."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unloaded:
        return False
    manager = entry.runtime_data.manager
    await manager.async_shutdown()
    domain_data = hass.data.get(DOMAIN, {})
    if domain_data.get("manager") is manager:
        domain_data.pop("manager", None)
    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: RustyConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Revoke a paired device when removed from the device registry."""
    identifier = next(
        (value for domain, value in device_entry.identifiers if domain == DOMAIN), None
    )
    if identifier is None:
        return False
    await entry.runtime_data.manager.async_remove_device(identifier)
    return True


def _register_services(hass: HomeAssistant) -> None:
    """Register typed RustyHAMA actions."""
    base_schema = vol.Schema({vol.Required("device_id"): cv.string})

    async def send_notification(call: ServiceCall) -> None:
        await _command(
            hass,
            call.data["device_id"],
            "notification",
            {
                "title": call.data.get("title", "Home Assistant"),
                "message": call.data["message"],
                "duration_ms": call.data.get("duration_ms", 0),
                "play_sound": call.data.get("play_sound", False),
            },
        )

    async def set_active_tab(call: ServiceCall) -> None:
        payload = {key: call.data[key] for key in ("index", "tab_id") if key in call.data}
        await _command(hass, call.data["device_id"], "set_active_tab", payload)

    async def set_screensaver(call: ServiceCall) -> None:
        await _command(
            hass,
            call.data["device_id"],
            "set_screensaver",
            {"state": call.data["state"]},
        )

    async def reload_configuration(call: ServiceCall) -> None:
        manager = hass.data[DOMAIN]["manager"]
        device_id = call.data["device_id"]
        if device_id not in manager.storage.devices:
            raise HomeAssistantError("Unknown RustyHAMA device")
        await manager.async_push_configuration(device_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_NOTIFICATION,
        send_notification,
        schema=base_schema.extend(
            {
                vol.Required("message"): cv.string,
                vol.Optional("title"): cv.string,
                vol.Optional("duration_ms"): vol.All(int, vol.Range(min=0)),
                vol.Optional("play_sound"): cv.boolean,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ACTIVE_TAB,
        set_active_tab,
        schema=base_schema.extend(
            {
                vol.Optional("index"): vol.All(int, vol.Range(min=0)),
                vol.Optional("tab_id"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCREENSAVER,
        set_screensaver,
        schema=base_schema.extend({vol.Required("state"): vol.In({"on", "off", "toggle"})}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RELOAD_CONFIGURATION,
        reload_configuration,
        schema=base_schema,
    )


async def _command(
    hass: HomeAssistant, device_id: str, command: str, payload: dict[str, Any]
) -> None:
    manager = hass.data[DOMAIN]["manager"]
    try:
        result = await manager.async_send_command(device_id, command, payload)
    except ConnectionError as err:
        raise HomeAssistantError("RustyHAMA device is unavailable") from err
    if not result.get("success", True):
        raise HomeAssistantError(str(result.get("error", "Device rejected command")))
