"""RustyHAMA runtime manager."""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import secrets
import time
from collections.abc import AsyncIterator
from datetime import date, datetime
from functools import partial
from hashlib import sha256
from types import MappingProxyType
from typing import Any
from uuid import uuid4

from homeassistant.components.calendar import DATA_COMPONENT as CALENDAR_COMPONENT
from homeassistant.components.calendar import WEBSOCKET_EVENT_SCHEMA
from homeassistant.components.recorder import get_instance as get_recorder_instance
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import (
    DEVICE_TOKEN_BYTES,
    OFFLINE_AFTER_SECONDS,
    PAIR_MAX_ATTEMPTS,
    PAIR_TTL_SECONDS,
    SIGNAL_ASSIST_EVENT,
    SIGNAL_ASSIST_START,
    SIGNAL_DEVICE_UPDATED,
    SIGNAL_DEVICES_CHANGED,
    SUBENTRY_TYPE_DEVICE,
)
from .dashboard_compiler import Compilation, DashboardCompiler
from .models import DeviceRecord, DeviceSession, PairingRequest, utc_iso
from .protocol import envelope, validate_message
from .storage import RustyStorage

_LOGGER = logging.getLogger(__name__)

ALLOWED_SERVICES: dict[str, frozenset[str]] = {
    "button": frozenset({"press"}),
    "climate": frozenset(
        {
            "set_fan_mode",
            "set_hvac_mode",
            "set_preset_mode",
            "set_swing_horizontal_mode",
            "set_swing_mode",
            "set_temperature",
        }
    ),
    "cover": frozenset({"close_cover", "open_cover", "set_cover_position", "stop_cover"}),
    "fan": frozenset(
        {
            "oscillate",
            "set_direction",
            "set_percentage",
            "set_preset_mode",
            "toggle",
            "turn_off",
            "turn_on",
        }
    ),
    "light": frozenset({"turn_off", "turn_on", "toggle"}),
    "media_player": frozenset(
        {
            "clear_playlist",
            "join",
            "media_next_track",
            "media_pause",
            "media_play",
            "media_previous_track",
            "media_seek",
            "play_media",
            "select_source",
            "unjoin",
            "volume_set",
        }
    ),
    "select": frozenset({"select_option"}),
    "switch": frozenset({"turn_off", "turn_on", "toggle"}),
}


def token_hash(value: str) -> str:
    """Hash a high-entropy token for storage."""
    return sha256(value.encode()).hexdigest()


class RustyManager:
    """Coordinate storage, paired devices, and live sessions."""

    DEVICE_REQUEST_TYPES = frozenset(
        {
            "calendar_create",
            "calendar_delete",
            "calendar_events",
            "calendar_update",
            "history",
            "weather_forecast",
        }
    )

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.storage = RustyStorage(hass)
        self.pairings: dict[str, PairingRequest] = {}
        self.sessions: dict[str, DeviceSession] = {}
        self.streams: dict[str, asyncio.Queue[bytes | None]] = {}
        self._pending_acks: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self.compiler = DashboardCompiler(hass)
        self._compiled: dict[str, Compilation] = {}
        self._refresh_tasks: dict[str, asyncio.Task[None]] = {}
        self._watchdog_tasks: dict[str, asyncio.Task[None]] = {}

    async def async_setup(self) -> None:
        """Load state."""
        await self.storage.async_load()
        self.entry.async_on_unload(
            self.hass.bus.async_listen("state_changed", self._async_state_changed)
        )

    async def async_shutdown(self) -> None:
        """Close live transports and background work before an entry reload."""
        sessions = tuple(self.sessions.values())
        self.sessions.clear()
        for task in (*self._watchdog_tasks.values(), *self._refresh_tasks.values()):
            task.cancel()
        self._watchdog_tasks.clear()
        self._refresh_tasks.clear()
        for future in self._pending_acks.values():
            if not future.done():
                future.set_exception(ConnectionError("integration_unloaded"))
        self._pending_acks.clear()
        for queue in self.streams.values():
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                # Shutdown is authoritative: discard one buffered chunk so a
                # blocked stream consumer always receives the end marker.
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                queue.put_nowait(None)
        self.streams.clear()
        for session in sessions:
            if not session.websocket.closed:
                # OkHttp 3.x on legacy Android rejects RFC 6455's later 1012
                # service-restart code as reserved. 1001 communicates the same
                # intentional server departure and is understood by all clients.
                await session.websocket.close(code=1001, message=b"integration reload")
        changed = False
        for device in self.storage.devices.values():
            if device.online:
                device.online = False
                device.last_seen = utc_iso()
                changed = True
        if changed:
            await self.storage.async_save()

    async def async_create_pairing(
        self,
        *,
        name: str,
        profile_id: str,
        area_id: str | None,
        certificate_fingerprint: str | None = None,
        public_key_pin: str | None = None,
    ) -> dict[str, Any]:
        """Create a short-lived manual and QR pairing authorization."""
        self._purge_pairings()
        code = f"{secrets.randbelow(100_000_000):08d}"
        while token_hash(code) in self.pairings:
            code = f"{secrets.randbelow(100_000_000):08d}"
        qr_token = secrets.token_urlsafe(32)
        request = PairingRequest(
            code_hash=token_hash(code),
            qr_token_hash=token_hash(qr_token),
            name=name.strip() or "RustyHAMA",
            profile_id=profile_id,
            area_id=area_id,
            expires_at=time.time() + PAIR_TTL_SECONDS,
        )
        self.pairings[request.code_hash] = request
        return {
            "code": code,
            "qr_token": qr_token,
            "expires_in": PAIR_TTL_SECONDS,
            "max_attempts": PAIR_MAX_ATTEMPTS,
            "certificate_fingerprint": certificate_fingerprint or "",
            "public_key_pin": public_key_pin or "",
        }

    async def async_complete_pairing(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Consume a pairing request and register a device subentry."""
        self._purge_pairings()
        supplied = str(payload.get("code") or "")
        qr_token = str(payload.get("qr_token") or "")
        candidate_hashes = [token_hash(value) for value in (supplied, qr_token) if value]
        pair_key: str | None = None
        pairing: PairingRequest | None = None
        for key, item in self.pairings.items():
            if any(
                hmac.compare_digest(candidate, expected)
                for candidate in candidate_hashes
                for expected in (item.code_hash, item.qr_token_hash)
            ):
                pair_key, pairing = key, item
                break
        if pairing is None or pair_key is None:
            raise PermissionError("invalid_pairing_code")
        pairing.attempts += 1
        if pairing.attempts > PAIR_MAX_ATTEMPTS or pairing.expires_at <= time.time():
            self.pairings.pop(pair_key, None)
            raise PermissionError("pairing_expired")

        device_id = uuid4().hex
        credential = secrets.token_urlsafe(DEVICE_TOKEN_BYTES)
        subentry = ConfigSubentry(
            data=MappingProxyType(
                {
                    "device_id": device_id,
                    "profile_id": pairing.profile_id,
                    "area_id": pairing.area_id,
                }
            ),
            subentry_type=SUBENTRY_TYPE_DEVICE,
            title=pairing.name,
            unique_id=device_id,
        )
        self.hass.config_entries.async_add_subentry(self.entry, subentry)
        device = DeviceRecord(
            device_id=device_id,
            name=pairing.name,
            token_hash=token_hash(credential),
            subentry_id=subentry.subentry_id,
            profile_id=pairing.profile_id,
            area_id=pairing.area_id,
            capabilities=dict(payload.get("capabilities") or {}),
            display=dict(payload.get("display") or {}),
        )
        self.storage.devices[device_id] = device
        registry = dr.async_get(self.hass)
        registry_device = registry.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            config_subentry_id=subentry.subentry_id,
            identifiers={("rustyhama", device_id)},
            manufacturer="RustyHAMA",
            name=pairing.name,
            model=str(payload.get("model") or "Android device"),
            sw_version=str(payload.get("app_version") or "unknown"),
            configuration_url=f"homeassistant://navigate/rustyhama/device/{device_id}",
        )
        if pairing.area_id:
            registry.async_update_device(registry_device.id, area_id=pairing.area_id)
        self.pairings.pop(pair_key, None)
        await self.storage.async_save()
        async_dispatcher_send(self.hass, SIGNAL_DEVICES_CHANGED)
        return {
            "protocol_version": 1,
            "device_id": device_id,
            "credential": credential,
            "config_revision": device.config_revision,
            "config": self._compile(device).config,
        }

    def authenticate(self, device_id: str, credential: str) -> DeviceRecord | None:
        """Authenticate one paired device using constant-time comparison."""
        device = self.storage.devices.get(device_id)
        if device is None or not credential:
            return None
        if not hmac.compare_digest(device.token_hash, token_hash(credential)):
            return None
        return device

    async def async_attach(self, device: DeviceRecord, websocket: Any) -> DeviceSession:
        """Replace any prior live session for a device."""
        # Compile before replacing the current connection. A malformed draft must
        # never tear down a healthy device session.
        compilation = self._compile(device)
        old = self.sessions.pop(device.device_id, None)
        old_watchdog = self._watchdog_tasks.pop(device.device_id, None)
        if old_watchdog is not None:
            old_watchdog.cancel()
        if old is not None and not old.websocket.closed:
            await old.websocket.close(code=4001, message=b"replaced")
        device.session_generation += 1
        device.online = True
        device.last_seen = utc_iso()
        session = DeviceSession(device.device_id, websocket, device.session_generation)
        self.sessions[device.device_id] = session
        self._watchdog_tasks[device.device_id] = self.hass.async_create_background_task(
            self._async_watch_session(session),
            f"RustyHAMA watchdog {device.device_id}",
        )
        await websocket.send_json(
            envelope(
                "hello",
                {
                    "session_generation": session.generation,
                    "config": compilation.config,
                },
                revision=device.config_revision,
            )
        )
        await websocket.send_json(
            envelope("states", {"states": self._initial_states(compilation)})
        )
        try:
            await self.storage.async_save()
        except Exception:
            # Online/last-seen persistence is diagnostic. It must not make the
            # live control channel unusable when HA storage is temporarily busy.
            _LOGGER.exception(
                "Could not persist RustyHAMA session state for %s", device.device_id
            )
        self._signal_device(device.device_id)
        return session

    async def async_detach(self, session: DeviceSession) -> None:
        """Detach a session only if it is still current."""
        current = self.sessions.get(session.device_id)
        if current is not session:
            return
        self.sessions.pop(session.device_id, None)
        watchdog = self._watchdog_tasks.pop(session.device_id, None)
        if watchdog is not None and watchdog is not asyncio.current_task():
            watchdog.cancel()
        refresh = self._refresh_tasks.pop(session.device_id, None)
        if refresh is not None:
            refresh.cancel()
        device = self.storage.devices.get(session.device_id)
        if device:
            device.online = False
            device.last_seen = utc_iso()
            await self.storage.async_save()
            self._signal_device(device.device_id)

    async def async_handle_message(
        self, session: DeviceSession, raw: dict[str, Any]
    ) -> None:
        """Handle a validated device message."""
        message = validate_message(raw)
        session.last_activity_monotonic = time.monotonic()
        device = self.storage.devices[session.device_id]
        if message["id"] in device.recent_message_ids:
            await self._async_try_ws_send(
                session, envelope("ack", {}, message_id=message["id"])
            )
            return
        device.recent_message_ids.append(message["id"])
        device.last_seen = utc_iso()
        kind = message["type"]
        payload = message["payload"]
        persist = False
        if kind == "heartbeat":
            await self._async_try_ws_send(
                session, envelope("heartbeat_ack", {}, message_id=message["id"])
            )
        elif kind == "telemetry":
            device.telemetry.update(payload)
            persist = True
            self._signal_device(device.device_id)
        elif kind == "capabilities":
            device.capabilities = dict(payload)
            persist = True
            self._signal_device(device.device_id)
        elif kind == "display":
            device.display = dict(payload)
            persist = True
            self._signal_device(device.device_id)
        elif kind == "config_ack":
            device.acknowledged_revision = int(message["revision"])
            persist = True
            self._resolve_ack(message["id"], payload)
            self._signal_device(device.device_id)
        elif kind == "command_ack":
            self._resolve_ack(message["id"], payload)
        elif kind == "stream_chunk":
            stream_id = str(payload.get("stream_id", ""))
            data = payload.get("data")
            if stream_id in self.streams and isinstance(data, str):
                import base64
                await self.streams[stream_id].put(base64.b64decode(data))
        elif kind == "stream_end":
            stream_id = str(payload.get("stream_id", ""))
            if stream_id in self.streams:
                await self.streams[stream_id].put(None)
        elif kind == "assist_start":
            async_dispatcher_send(
                self.hass, SIGNAL_ASSIST_START, device.device_id, dict(payload)
            )
        elif kind in {"tts_finished", "tts_failed"}:
            async_dispatcher_send(
                self.hass, SIGNAL_ASSIST_EVENT, device.device_id, kind, dict(payload)
            )
        elif kind == "entity_action":
            await self._async_entity_action(device, message)
        elif kind in self.DEVICE_REQUEST_TYPES:
            await self._async_device_request(device, message)
        if persist:
            try:
                await self.storage.async_save()
            except Exception:
                _LOGGER.exception(
                    "Could not persist RustyHAMA message state for %s",
                    device.device_id,
                )

    async def async_send_command(
        self,
        device_id: str,
        command: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float = 10,
    ) -> dict[str, Any]:
        """Send a command to an online device and wait for its ACK."""
        session = self.sessions.get(device_id)
        if session is None or session.websocket.closed:
            raise ConnectionError("device_unavailable")
        message = envelope(command, payload)
        future: asyncio.Future[dict[str, Any]] = self.hass.loop.create_future()
        self._pending_acks[message["id"]] = future
        session.pending[message["id"]] = message
        try:
            await self._async_try_ws_send(session, message)
            return await asyncio.wait_for(future, timeout)
        finally:
            self._pending_acks.pop(message["id"], None)
            session.pending.pop(message["id"], None)

    async def async_push_configuration(self, device_id: str, *, force: bool = True) -> bool:
        """Send a compiled configuration and its narrow state projection."""
        device = self.storage.devices[device_id]
        session = self.sessions.get(device_id)
        if session is None or session.websocket.closed:
            return False
        previous = self._compiled.get(device_id)
        compilation = self._compile(device)
        if not force and previous is not None and previous.fingerprint == compilation.fingerprint:
            return False
        configuration = envelope(
            "configuration",
            {"config": compilation.config},
            revision=device.config_revision,
        )
        states = envelope("states", {"states": self._initial_states(compilation)})
        await self._async_try_ws_send(session, configuration)
        await self._async_try_ws_send(session, states)
        return True

    async def async_update_device_config(
        self, device_id: str, patch: dict[str, Any]
    ) -> int:
        """Merge a device override, publish a revision, and deploy if online."""
        from .merge import merge_patch

        device = self.storage.devices[device_id]
        device.override = merge_patch(device.override, patch)
        revision = await self.storage.async_publish_device(device)
        await self.async_push_configuration(device_id)
        self._signal_device(device_id)
        return revision

    async def async_send_event(
        self, device_id: str, event: str, payload: dict[str, Any] | None = None
    ) -> None:
        """Send an ephemeral event without replay or ACK bookkeeping."""
        session = self.sessions.get(device_id)
        if session is None or session.websocket.closed:
            raise ConnectionError("device_unavailable")
        message = envelope(event, payload)
        await self._async_try_ws_send(session, message)

    async def _async_try_ws_send(
        self, session: DeviceSession, message: dict[str, Any]
    ) -> bool:
        """Best-effort WebSocket delivery bounded independently of HTTP polling."""
        try:
            await asyncio.wait_for(session.websocket.send_json(message), timeout=1.0)
        except Exception:
            _LOGGER.debug(
                "RustyHAMA WebSocket delivery deferred to HTTP poll for %s",
                session.device_id,
                exc_info=True,
            )
            return False
        return True

    async def async_stream(self, stream_id: str) -> AsyncIterator[bytes]:
        """Yield an authenticated logical media stream."""
        queue = self.streams.setdefault(stream_id, asyncio.Queue(maxsize=8))
        try:
            while (chunk := await queue.get()) is not None:
                yield chunk
        finally:
            self.streams.pop(stream_id, None)

    async def async_remove_device(self, device_id: str) -> None:
        """Revoke a device and remove its subentry."""
        device = self.storage.devices.pop(device_id)
        self._compiled.pop(device_id, None)
        refresh = self._refresh_tasks.pop(device_id, None)
        if refresh is not None:
            refresh.cancel()
        session = self.sessions.pop(device_id, None)
        watchdog = self._watchdog_tasks.pop(device_id, None)
        if watchdog is not None:
            watchdog.cancel()
        if session and not session.websocket.closed:
            await session.websocket.close(code=4003, message=b"revoked")
        self.hass.config_entries.async_remove_subentry(self.entry, device.subentry_id)
        await self.storage.async_save()
        async_dispatcher_send(self.hass, SIGNAL_DEVICES_CHANGED)

    async def async_rotate_credential(self, device_id: str) -> None:
        """Atomically rotate a credential after the online device accepts it."""
        device = self.storage.devices[device_id]
        credential = secrets.token_urlsafe(DEVICE_TOKEN_BYTES)
        result = await self.async_send_command(
            device_id, "rotate_credential", {"credential": credential}
        )
        if not result.get("success", False):
            raise RuntimeError(str(result.get("error", "credential_rejected")))
        device.token_hash = token_hash(credential)
        await self.storage.async_save()

    def public_snapshot(self) -> dict[str, Any]:
        """Return an admin-panel snapshot without secrets."""
        return {
            "profiles": json.loads(json.dumps(self.storage.profiles)),
            "providers": {
                provider_id: {
                    key: value
                    for key, value in provider.items()
                    if key not in {"api_key", "token", "password", "secret"}
                }
                for provider_id, provider in self.storage.providers.items()
            },
            "devices": [
                {
                    **device.persistent_dict(),
                    "token_hash": "**REDACTED**",
                    "online": device.online,
                    "effective_config": self.storage.effective_config(device),
                    "compiled_config": self._compile(device).config,
                }
                for device in self.storage.devices.values()
            ],
            "revisions": self.storage.revisions,
        }

    def _resolve_ack(self, message_id: str, payload: dict[str, Any]) -> None:
        future = self._pending_acks.get(message_id)
        if future and not future.done():
            future.set_result(payload)

    async def _async_watch_session(self, session: DeviceSession) -> None:
        """Close half-open sessions using the versioned application heartbeat."""
        try:
            while self.sessions.get(session.device_id) is session:
                await asyncio.sleep(OFFLINE_AFTER_SECONDS)
                if self.sessions.get(session.device_id) is not session:
                    return
                silence = time.monotonic() - session.last_activity_monotonic
                if silence < OFFLINE_AFTER_SECONDS:
                    continue
                _LOGGER.warning(
                    "Closing stale RustyHAMA session for %s after %.1f seconds",
                    session.device_id,
                    silence,
                )
                if not session.websocket.closed:
                    await session.websocket.close(code=4000, message=b"heartbeat timeout")
                return
        except asyncio.CancelledError:
            return

    def _purge_pairings(self) -> None:
        now = time.time()
        self.pairings = {
            key: pairing
            for key, pairing in self.pairings.items()
            if pairing.expires_at > now and pairing.attempts <= PAIR_MAX_ATTEMPTS
        }

    def _signal_device(self, device_id: str) -> None:
        async_dispatcher_send(self.hass, SIGNAL_DEVICE_UPDATED, device_id)

    def allowed_entities(self, device: DeviceRecord) -> set[str]:
        """Return only the entities selected by the compiled dashboard."""
        compilation = self._compiled.get(device.device_id)
        if compilation is None:
            compilation = self._compile(device)
        return set(compilation.entity_ids)

    def _compile(self, device: DeviceRecord) -> Compilation:
        """Compile a fresh view model; callers decide whether to deploy it."""
        compilation = self.compiler.compile(self.storage.effective_config(device), device.area_id)
        self._compiled[device.device_id] = compilation
        return compilation

    def _initial_states(self, compilation: Compilation) -> list[dict[str, Any]]:
        return [
            self._json_compatible(state.as_dict())
            for entity_id in sorted(compilation.entity_ids)
            if (state := self.hass.states.get(entity_id)) is not None
        ]

    async def _async_state_changed(self, event: Any) -> None:
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        if not entity_id or new_state is None:
            return
        for device_id, session in tuple(self.sessions.items()):
            device = self.storage.devices.get(device_id)
            compilation = self._compiled.get(device_id)
            if device is None:
                continue
            if compilation is None:
                compilation = self._compile(device)
            if entity_id in compilation.entity_ids and not session.websocket.closed:
                message = envelope(
                    "state",
                    {"state": self._json_compatible(new_state.as_dict())},
                )
                try:
                    await session.websocket.send_json(message)
                except Exception:
                    # aiohttp can transition to closing after the closed check but
                    # before the frame write. Detach only if this is still the active
                    # generation; replacement sessions must remain untouched.
                    _LOGGER.debug(
                        "State delivery failed for %s; detaching stale session",
                        device_id,
                        exc_info=True,
                    )
                    await self.async_detach(session)
                    continue
            if compilation.dynamic:
                self._schedule_dashboard_refresh(device_id)

    def _schedule_dashboard_refresh(self, device_id: str) -> None:
        """Coalesce global query re-evaluation after bursts of state events."""
        pending = self._refresh_tasks.get(device_id)
        if pending is not None and not pending.done():
            return

        async def refresh() -> None:
            try:
                await asyncio.sleep(0.25)
                await self.async_push_configuration(device_id, force=False)
            except (ConnectionError, KeyError):
                return
            finally:
                self._refresh_tasks.pop(device_id, None)

        self._refresh_tasks[device_id] = self.hass.async_create_task(refresh())

    async def _async_device_request(
        self, device: DeviceRecord, message: dict[str, Any]
    ) -> None:
        """Serve a narrow HA data operation over the paired device channel."""
        session = self.sessions.get(device.device_id)
        if session is None or session.websocket.closed:
            return
        try:
            result = await self._async_execute_device_request(
                device, message["type"], message["payload"]
            )
        except Exception as err:
            _LOGGER.warning(
                "RustyHAMA request %s failed for %s: %s",
                message["type"],
                device.device_id,
                err,
            )
            payload = {"success": False, "error": str(err) or "request_failed"}
        else:
            payload = {"success": True, "result": self._json_compatible(result)}
        response = envelope("request_result", payload, message_id=message["id"])
        await self._async_try_ws_send(session, response)

    async def _async_execute_device_request(
        self, device: DeviceRecord, kind: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute one allow-listed data request."""
        entity_id = self._allowed_request_entity(device, payload, kind)
        if kind.startswith("calendar_"):
            component = self.hass.data.get(CALENDAR_COMPONENT)
            entity = component.get_entity(entity_id) if component is not None else None
            if entity is None:
                raise ValueError("calendar_not_found")
            if kind == "calendar_events":
                start = dt_util.parse_datetime(str(payload.get("start", "")))
                end = dt_util.parse_datetime(str(payload.get("end", "")))
                if start is None or end is None or end <= start:
                    raise ValueError("invalid_calendar_range")
                events = await entity.async_get_events(
                    self.hass, dt_util.as_local(start), dt_util.as_local(end)
                )
                return {"events": [event.as_dict() for event in events]}
            if kind == "calendar_create":
                event = WEBSOCKET_EVENT_SCHEMA(dict(payload.get("event") or {}))
                await entity.async_create_event(**event)
                return {}
            uid = str(payload.get("uid", ""))
            if not uid:
                raise ValueError("calendar_uid_required")
            recurrence_id = str(payload.get("recurrence_id") or "") or None
            recurrence_range = str(payload.get("recurrence_range") or "") or None
            if kind == "calendar_update":
                event = WEBSOCKET_EVENT_SCHEMA(dict(payload.get("event") or {}))
                await entity.async_update_event(
                    uid,
                    event,
                    recurrence_id=recurrence_id,
                    recurrence_range=recurrence_range,
                )
                return {}
            await entity.async_delete_event(
                uid,
                recurrence_id=recurrence_id,
                recurrence_range=recurrence_range,
            )
            return {}
        if kind == "weather_forecast":
            forecast_type = str(payload.get("forecast_type") or "daily")
            if forecast_type not in {"daily", "hourly", "twice_daily"}:
                raise ValueError("invalid_forecast_type")
            response = await self.hass.services.async_call(
                "weather",
                "get_forecasts",
                {"type": forecast_type},
                blocking=True,
                target={"entity_id": entity_id},
                return_response=True,
            )
            return dict(response or {})
        if kind == "history":
            start = dt_util.parse_datetime(str(payload.get("start", "")))
            end = dt_util.parse_datetime(str(payload.get("end", "")))
            if start is None or end is None or end <= start:
                raise ValueError("invalid_history_range")
            values = await get_recorder_instance(self.hass).async_add_executor_job(
                partial(
                    get_significant_states,
                    self.hass,
                    start,
                    end,
                    entity_ids=[entity_id],
                    minimal_response=True,
                    no_attributes=True,
                )
            )
            return {"history": [values.get(entity_id, [])]}
        raise ValueError("unsupported_request")

    def _allowed_request_entity(
        self, device: DeviceRecord, payload: dict[str, Any], kind: str
    ) -> str:
        """Validate that a data request stays inside the compiled dashboard scope."""
        entity_id = str(payload.get("entity_id", ""))
        expected_domain = (
            "calendar"
            if kind.startswith("calendar_")
            else "weather"
            if kind == "weather_forecast"
            else ""
        )
        domain = entity_id.partition(".")[0]
        if (
            not entity_id
            or entity_id not in self.allowed_entities(device)
            or (expected_domain and domain != expected_domain)
        ):
            raise PermissionError("operation_not_allowed")
        return entity_id

    @classmethod
    def _json_compatible(cls, value: Any) -> Any:
        """Convert HA dates, states and mappings to an aiohttp JSON value."""
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if hasattr(value, "as_dict"):
            return cls._json_compatible(value.as_dict())
        if isinstance(value, dict):
            return {str(key): cls._json_compatible(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set, frozenset)):
            return [cls._json_compatible(item) for item in value]
        return value

    async def _async_entity_action(
        self, device: DeviceRecord, message: dict[str, Any]
    ) -> None:
        payload = message["payload"]
        entity_id = str(payload.get("entity_id", ""))
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        service = str(payload.get("service", ""))
        session = self.sessions.get(device.device_id)
        if session is None:
            return
        if (
            entity_id not in self.allowed_entities(device)
            or service not in ALLOWED_SERVICES.get(domain, frozenset())
        ):
            response = envelope(
                "command_ack",
                {"success": False, "error": "operation_not_allowed"},
                message_id=message["id"],
            )
            await self._async_try_ws_send(session, response)
            return
        data = dict(payload.get("data") or {})
        data["entity_id"] = entity_id
        try:
            await self.hass.services.async_call(domain, service, data, blocking=True)
        except Exception as err:  # Home Assistant turns this into a typed device failure.
            _LOGGER.warning("Device action failed for %s: %s", entity_id, err)
            result = {"success": False, "error": str(err)}
        else:
            result = {"success": True}
        response = envelope("command_ack", result, message_id=message["id"])
        await self._async_try_ws_send(session, response)
