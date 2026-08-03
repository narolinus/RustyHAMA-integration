"""Authenticated admin WebSocket API used by the HA panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DEFAULT_PROFILE_ID, DOMAIN
from .schema import DashboardValidationError, referenced_providers, validate_dashboard


def _manager(hass: HomeAssistant) -> Any:
    return hass.data[DOMAIN]["manager"]


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "rustyhama/get_snapshot"})
@websocket_api.async_response
async def ws_get_snapshot(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Return the complete redacted editor model."""
    connection.send_result(msg["id"], _manager(hass).public_snapshot())


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "rustyhama/compile_preview",
        vol.Required("config"): dict,
        vol.Optional("device_id"): str,
    }
)
@websocket_api.async_response
async def ws_compile_preview(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Compile an editor draft with the same server logic used for Android."""
    manager = _manager(hass)
    device = manager.storage.devices.get(msg.get("device_id", ""))
    area_id = device.area_id if device is not None else None
    try:
        validate_dashboard(msg["config"])
        compilation = manager.compiler.compile(msg["config"], area_id)
    except DashboardValidationError as err:
        connection.send_error(msg["id"], "invalid_config", str(err))
        return
    connection.send_result(
        msg["id"],
        {
            "config": compilation.config,
            "entity_ids": sorted(compilation.entity_ids),
            "dynamic": compilation.dynamic,
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "rustyhama/create_pairing",
        vol.Required("name"): str,
        vol.Optional("profile_id", default=DEFAULT_PROFILE_ID): str,
        vol.Optional("area_id"): vol.Any(str, None),
        vol.Optional("certificate_fingerprint"): str,
        vol.Optional("public_key_pin"): str,
    }
)
@websocket_api.async_response
async def ws_create_pairing(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Create a one-time pairing authorization."""
    result = await _manager(hass).async_create_pairing(
        name=msg["name"],
        profile_id=msg["profile_id"],
        area_id=msg.get("area_id"),
        certificate_fingerprint=msg.get("certificate_fingerprint"),
        public_key_pin=msg.get("public_key_pin"),
    )
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "rustyhama/save_profile",
        vol.Required("profile_id"): str,
        vol.Required("name"): str,
        vol.Required("config"): dict,
    }
)
@websocket_api.async_response
async def ws_save_profile(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Save a validated draft without deploying it."""
    manager = _manager(hass)
    try:
        warnings = validate_dashboard(msg["config"])
    except DashboardValidationError as err:
        connection.send_error(msg["id"], "invalid_config", str(err))
        return
    prior = manager.storage.profiles.get(msg["profile_id"], {})
    manager.storage.profiles[msg["profile_id"]] = {
        "name": msg["name"],
        "draft": msg["config"],
        "published": prior.get("published", msg["config"]),
    }
    await manager.storage.async_save()
    connection.send_result(msg["id"], {"warnings": warnings})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "rustyhama/delete_profile", vol.Required("profile_id"): str}
)
@websocket_api.async_response
async def ws_delete_profile(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Delete an unused non-default profile."""
    manager = _manager(hass)
    profile_id = msg["profile_id"]
    if profile_id == DEFAULT_PROFILE_ID:
        connection.send_error(msg["id"], "profile_in_use", "The default profile cannot be deleted")
        return
    if profile_id not in manager.storage.profiles:
        connection.send_error(msg["id"], "unknown_profile", "Profile not found")
        return
    assigned = [
        device.name
        for device in manager.storage.devices.values()
        if device.profile_id == profile_id
    ]
    if assigned:
        connection.send_error(
            msg["id"],
            "profile_in_use",
            f"Profile is assigned to: {', '.join(sorted(assigned))}",
        )
        return
    manager.storage.profiles.pop(profile_id)
    await manager.storage.async_save()
    connection.send_result(msg["id"], {"success": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "rustyhama/publish_profile", vol.Required("profile_id"): str}
)
@websocket_api.async_response
async def ws_publish_profile(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Publish a draft and push it to online devices."""
    manager = _manager(hass)
    try:
        profile = manager.storage.profiles[msg["profile_id"]]
        missing = referenced_providers(profile["draft"]) - manager.storage.providers.keys()
        if missing:
            raise DashboardValidationError(
                f"Missing provider connections: {', '.join(sorted(missing))}"
            )
        revision = await manager.storage.async_publish_profile(msg["profile_id"])
    except (KeyError, DashboardValidationError) as err:
        connection.send_error(msg["id"], "publish_failed", str(err))
        return
    for device in manager.storage.devices.values():
        if device.profile_id == msg["profile_id"]:
            await manager.async_push_configuration(device.device_id)
    connection.send_result(msg["id"], {"revision": revision})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "rustyhama/rollback", vol.Required("revision"): int}
)
@websocket_api.async_response
async def ws_rollback(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Republish an older revision."""
    manager = _manager(hass)
    try:
        revision = await manager.storage.async_rollback(msg["revision"])
    except KeyError:
        connection.send_error(msg["id"], "unknown_revision", "Revision not found")
        return
    for device in manager.storage.devices.values():
        await manager.async_push_configuration(device.device_id)
    connection.send_result(msg["id"], {"revision": revision})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "rustyhama/update_device",
        vol.Required("device_id"): str,
        vol.Optional("name"): str,
        vol.Optional("profile_id"): str,
        vol.Optional("override"): dict,
        vol.Optional("provider_bindings"): dict,
    }
)
@websocket_api.async_response
async def ws_update_device(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Update per-device settings."""
    manager = _manager(hass)
    device = manager.storage.devices.get(msg["device_id"])
    if device is None:
        connection.send_error(msg["id"], "unknown_device", "Device not found")
        return
    requested_profile = msg.get("profile_id")
    if requested_profile is not None and requested_profile not in manager.storage.profiles:
        connection.send_error(msg["id"], "unknown_profile", "Profile not found")
        return
    for field in ("name", "profile_id", "override", "provider_bindings"):
        if field in msg:
            setattr(device, field, msg[field])
    revision = await manager.storage.async_publish_device(device)
    await manager.async_push_configuration(device.device_id)
    connection.send_result(msg["id"], {"success": True, "revision": revision})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "rustyhama/save_provider",
        vol.Required("provider_id"): str,
        vol.Required("provider"): dict,
    }
)
@websocket_api.async_response
async def ws_save_provider(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Save a provider including secrets; responses never echo them."""
    manager = _manager(hass)
    provider = dict(msg["provider"])
    if provider.get("type") not in {"immich", "music_assistant"} or not provider.get("url"):
        connection.send_error(msg["id"], "invalid_provider", "Type and URL are required")
        return
    secret_field = "api_key" if provider["type"] == "immich" else "token"
    if not provider.get(secret_field):
        prior = manager.storage.providers.get(msg["provider_id"], {})
        if prior.get(secret_field):
            provider[secret_field] = prior[secret_field]
        else:
            connection.send_error(msg["id"], "invalid_provider", "Credential is required")
            return
    manager.storage.providers[msg["provider_id"]] = provider
    await manager.storage.async_save()
    connection.send_result(msg["id"], {"success": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "rustyhama/remove_device", vol.Required("device_id"): str}
)
@websocket_api.async_response
async def ws_remove_device(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Revoke and remove a device."""
    try:
        await _manager(hass).async_remove_device(msg["device_id"])
    except KeyError:
        connection.send_error(msg["id"], "unknown_device", "Device not found")
        return
    connection.send_result(msg["id"], {"success": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "rustyhama/rotate_credential", vol.Required("device_id"): str}
)
@websocket_api.async_response
async def ws_rotate_credential(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Rotate a device credential without exposing it to the browser."""
    try:
        await _manager(hass).async_rotate_credential(msg["device_id"])
    except (KeyError, ConnectionError, RuntimeError) as err:
        connection.send_error(msg["id"], "rotation_failed", str(err))
        return
    connection.send_result(msg["id"], {"success": True})


COMMANDS = (
    ws_get_snapshot,
    ws_compile_preview,
    ws_create_pairing,
    ws_save_profile,
    ws_delete_profile,
    ws_publish_profile,
    ws_rollback,
    ws_update_device,
    ws_save_provider,
    ws_remove_device,
    ws_rotate_credential,
)


def register_websocket_commands(hass: HomeAssistant) -> None:
    """Register panel commands."""
    for command in COMMANDS:
        websocket_api.async_register_command(hass, command)
