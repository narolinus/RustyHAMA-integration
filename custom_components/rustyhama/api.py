"""HTTP and device WebSocket API."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, ClassVar

import voluptuous as vol
from aiohttp import WSMsgType, web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DEVICE_MESSAGE_PATH,
    DEVICE_WS_PATH,
    DOMAIN,
    MA_PROVIDER_PATH,
    PAIR_PATH,
    PANEL_PATH,
    PROVIDER_PATH,
    STREAM_PATH,
)
from .protocol import envelope, validate_message
from .schema import referenced_providers

_LOGGER = logging.getLogger(__name__)


def _manager(request: web.Request) -> Any:
    hass: HomeAssistant = request.app["hass"]
    return hass.data[DOMAIN]["manager"]


def _device_auth(request: web.Request) -> tuple[str, str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer RustyHAMA "):
        auth = auth.removeprefix("Bearer ")
    if auth.startswith("RustyHAMA "):
        value = auth.removeprefix("RustyHAMA ")
        if "." in value:
            device_id, credential = value.split(".", 1)
            return device_id, credential
        return "", ""
    return request.query.get("device_id", ""), request.query.get("credential", "")


class PairView(HomeAssistantView):
    """Pair a device without requiring a Home Assistant user token."""

    url = PAIR_PATH
    name = "api:rustyhama:pair"
    requires_auth = False
    _failures: ClassVar[dict[str, list[float]]] = {}

    async def post(self, request: web.Request) -> web.Response:
        if not request.secure:
            return self.json({"error": "https_required"}, status_code=426)
        peer = request.remote or "unknown"
        now = time.monotonic()
        failures = [value for value in self._failures.get(peer, []) if now - value < 600]
        if len(failures) >= 5:
            return self.json({"error": "rate_limited"}, status_code=429)
        try:
            payload = await request.json()
            result = await _manager(request).async_complete_pairing(payload)
        except PermissionError as err:
            failures.append(now)
            self._failures[peer] = failures
            return self.json({"error": str(err)}, status_code=403)
        except (json.JSONDecodeError, ValueError, TypeError):
            return self.json({"error": "invalid_request"}, status_code=400)
        self._failures.pop(peer, None)
        return self.json(result)


class DeviceWebSocketView(HomeAssistantView):
    """Long-lived authenticated device control channel."""

    url = DEVICE_WS_PATH
    name = "api:rustyhama:device_ws"
    requires_auth = False

    async def get(self, request: web.Request) -> web.StreamResponse:
        if not request.secure:
            raise web.HTTPUpgradeRequired(text="HTTPS required")
        device_id, credential = _device_auth(request)
        manager = _manager(request)
        device = manager.authenticate(device_id, credential)
        if device is None:
            raise web.HTTPUnauthorized()
        # Old Android/OkHttp combinations are unreliable with overlapping transport
        # pings. RustyHAMA has a versioned application heartbeat and a server-side
        # watchdog, so the control channel deliberately does not use aiohttp pings.
        websocket = web.WebSocketResponse(max_msg_size=4 * 1024 * 1024)
        await websocket.prepare(request)
        session = None
        try:
            session = await manager.async_attach(device, websocket)
            async for item in websocket:
                if item.type == WSMsgType.TEXT:
                    try:
                        raw = json.loads(item.data)
                        await manager.async_handle_message(session, raw)
                    except (ValueError, TypeError, json.JSONDecodeError, vol.Invalid) as err:
                        await websocket.send_json(
                            envelope("protocol_error", {"error": str(err)})
                        )
                    except Exception:  # Keep one bad command from killing the channel.
                        _LOGGER.exception(
                            "RustyHAMA device message failed for %s", device.device_id
                        )
                        message_id = raw.get("id") if isinstance(raw, dict) else None
                        message_type = raw.get("type") if isinstance(raw, dict) else None
                        response_type = (
                            "request_result"
                            if message_type in manager.DEVICE_REQUEST_TYPES
                            else "command_ack"
                        )
                        await websocket.send_json(
                            envelope(
                                response_type,
                                {"success": False, "error": "internal_error"},
                                message_id=message_id,
                            )
                        )
                elif item.type in (WSMsgType.ERROR, WSMsgType.CLOSE, WSMsgType.CLOSED):
                    break
        except Exception:
            _LOGGER.exception(
                "RustyHAMA device session failed for %s", device.device_id
            )
            if not websocket.closed:
                await websocket.close(code=1011, message=b"device session failed")
        finally:
            if session is not None:
                await manager.async_detach(session)
        return websocket


class DeviceMessageView(HomeAssistantView):
    """Authenticated fallback for critical device-to-HA protocol frames."""

    url = DEVICE_MESSAGE_PATH
    name = "api:rustyhama:device_messages"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        if not request.secure:
            raise web.HTTPUpgradeRequired(text="HTTPS required")
        device_id, credential = _device_auth(request)
        manager = _manager(request)
        device = manager.authenticate(device_id, credential)
        if device is None:
            raise web.HTTPUnauthorized()
        session = manager.sessions.get(device.device_id)
        if session is None or session.websocket.closed:
            raise web.HTTPConflict(text="device session unavailable")
        try:
            raw = await request.json()
            # Validate before acknowledging receipt, but do not couple the HTTP
            # response to the control WebSocket.  This endpoint exists precisely
            # for half-open sockets; async_handle_message may need to emit a
            # heartbeat ACK on that socket and can therefore block on transport
            # backpressure.  Returning immediately also lets command ACKs use a
            # second, healthy connection to resolve the pending HA action.
            validate_message(raw)
        except (ValueError, TypeError, json.JSONDecodeError, vol.Invalid) as err:
            return self.json({"error": str(err)}, status_code=400)
        manager.hass.async_create_background_task(
            self._async_process(manager, session, raw),
            f"RustyHAMA device fallback {device.device_id}",
        )
        return self.json({"success": True}, status_code=202)

    async def _async_process(self, manager: Any, session: Any, raw: dict[str, Any]) -> None:
        """Process a validated fallback frame without holding the HTTP response."""
        try:
            await manager.async_handle_message(session, raw)
        except Exception:
            _LOGGER.exception(
                "RustyHAMA fallback message failed for %s", session.device_id
            )


class DeviceStreamView(HomeAssistantView):
    """Authenticated binary upload stream."""

    url = STREAM_PATH
    name = "api:rustyhama:device_stream"
    requires_auth = False

    async def get(self, request: web.Request, session_id: str) -> web.StreamResponse:
        if not request.secure:
            raise web.HTTPUpgradeRequired(text="HTTPS required")
        device_id, credential = _device_auth(request)
        manager = _manager(request)
        if manager.authenticate(device_id, credential) is None:
            raise web.HTTPUnauthorized()
        websocket = web.WebSocketResponse(max_msg_size=2 * 1024 * 1024)
        await websocket.prepare(request)
        queue = manager.streams.setdefault(session_id, asyncio.Queue(maxsize=8))
        try:
            async for item in websocket:
                if item.type == WSMsgType.BINARY:
                    await queue.put(item.data)
                elif item.type == WSMsgType.TEXT and item.data == "end":
                    await queue.put(None)
                    break
        finally:
            # A cancelled pipeline no longer drains this bounded queue. Never leave
            # the HTTP handler blocked while trying to append an end marker.
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass
        return websocket


class PanelJavaScriptView(HomeAssistantView):
    """Serve the bundled admin panel."""

    url = f"{PANEL_PATH}/panel.js"
    name = "api:rustyhama:frontend"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        path = Path(__file__).parent / "frontend" / "panel.js"
        source = await _manager(request).hass.async_add_executor_job(
            path.read_text, "utf-8"
        )
        return web.Response(
            text=source,
            content_type="text/javascript",
            headers={"Cache-Control": "no-store"},
        )


class PanelFontView(HomeAssistantView):
    """Serve the same Material Symbols font used by the Android dashboard."""

    url = f"{PANEL_PATH}/MaterialSymbolsOutlined.ttf"
    name = "api:rustyhama:frontend_font"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        path = Path(__file__).parent / "frontend" / "MaterialSymbolsOutlined.ttf"
        source = await _manager(request).hass.async_add_executor_job(path.read_bytes)
        return web.Response(
            body=source,
            content_type="font/ttf",
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )


class ImmichProviderView(HomeAssistantView):
    """Proxy a narrow Immich API surface without exposing its key."""

    url = PROVIDER_PATH
    name = "api:rustyhama:immich_provider"
    requires_auth = False

    async def get(
        self, request: web.Request, provider_id: str, tail: str
    ) -> web.StreamResponse:
        return await self._proxy(request, provider_id, tail)

    async def post(
        self, request: web.Request, provider_id: str, tail: str
    ) -> web.StreamResponse:
        return await self._proxy(request, provider_id, tail)

    async def _proxy(
        self, request: web.Request, provider_id: str, tail: str
    ) -> web.StreamResponse:
        if not request.secure:
            raise web.HTTPUpgradeRequired(text="HTTPS required")
        device_id, credential = _device_auth(request)
        manager = _manager(request)
        device = manager.authenticate(device_id, credential)
        if device is None:
            raise web.HTTPUnauthorized()
        allowed = set(device.provider_bindings.values()) | referenced_providers(
            manager.storage.effective_config(device)
        )
        provider = manager.storage.providers.get(provider_id)
        if provider_id not in allowed or not provider or provider.get("type") != "immich":
            raise web.HTTPForbidden()
        permitted = tail in {"api/search/assets", "api/search/metadata"}
        if tail.startswith("api/assets/") and tail.endswith("/thumbnail"):
            asset_id = tail.removeprefix("api/assets/").removesuffix("/thumbnail")
            permitted = bool(asset_id) and all(
                character.isalnum() or character == "-" for character in asset_id
            )
        if not permitted:
            raise web.HTTPNotFound()
        url = str(provider["url"]).rstrip("/") + "/" + tail
        headers = {"x-api-key": str(provider["api_key"])}
        for name in ("Accept", "Content-Type"):
            if value := request.headers.get(name):
                headers[name] = value
        body = await request.read() if request.method == "POST" else None
        session = async_get_clientsession(_manager(request).hass)
        async with session.request(
            request.method,
            url,
            params=request.query,
            data=body,
            headers=headers,
        ) as response:
            content = await response.read()
            return web.Response(
                body=content,
                status=response.status,
                content_type=response.content_type,
            )


class MusicAssistantProviderView(HomeAssistantView):
    """Authenticated server-side adapter for missing Music Assistant features."""

    url = MA_PROVIDER_PATH
    name = "api:rustyhama:music_assistant_provider"
    requires_auth = False

    def _provider(
        self, request: web.Request, provider_id: str
    ) -> dict[str, Any]:
        device_id, credential = _device_auth(request)
        manager = _manager(request)
        device = manager.authenticate(device_id, credential)
        if device is None:
            raise web.HTTPUnauthorized()
        allowed = set(device.provider_bindings.values()) | referenced_providers(
            manager.storage.effective_config(device)
        )
        provider = manager.storage.providers.get(provider_id)
        if (
            provider_id not in allowed
            or not provider
            or provider.get("type") != "music_assistant"
        ):
            raise web.HTTPForbidden()
        return provider

    async def get(
        self, request: web.Request, provider_id: str, tail: str
    ) -> web.StreamResponse:
        if not request.secure:
            raise web.HTTPUpgradeRequired(text="HTTPS required")
        provider = self._provider(request, provider_id)
        if tail == "ws":
            return await self._websocket(request, provider)
        if tail != "imageproxy" and not tail.startswith("imageproxy/"):
            raise web.HTTPNotFound()
        url = str(provider["url"]).rstrip("/") + "/" + tail
        headers = {"Authorization": f"Bearer {provider['token']}"}
        session = async_get_clientsession(_manager(request).hass)
        async with session.get(url, params=request.query, headers=headers) as response:
            return web.Response(
                body=await response.read(),
                status=response.status,
                content_type=response.content_type,
            )

    async def post(
        self, request: web.Request, provider_id: str, tail: str
    ) -> web.StreamResponse:
        """Forward stateless Music Assistant API commands for device clients."""
        if not request.secure:
            raise web.HTTPUpgradeRequired(text="HTTPS required")
        provider = self._provider(request, provider_id)
        if tail != "api":
            raise web.HTTPNotFound()
        url = str(provider["url"]).rstrip("/") + "/api"
        headers = {
            "Authorization": f"Bearer {provider['token']}",
            "Content-Type": request.content_type or "application/json",
            "Accept": "application/json",
        }
        session = async_get_clientsession(_manager(request).hass)
        async with session.post(
            url, params=request.query, headers=headers, data=await request.read()
        ) as response:
            return web.Response(
                body=await response.read(),
                status=response.status,
                content_type=response.content_type,
            )

    async def _websocket(
        self, request: web.Request, provider: dict[str, Any]
    ) -> web.StreamResponse:
        # The app-level watchdog is authoritative. Aiohttp transport pings are not
        # reliable on the oldest supported Android/OkHttp combinations.
        downstream = web.WebSocketResponse(max_msg_size=4 * 1024 * 1024)
        await downstream.prepare(request)
        base = str(provider["url"]).rstrip("/")
        upstream_url = base.replace("https://", "wss://").replace("http://", "ws://")
        if not upstream_url.endswith("/ws"):
            upstream_url += "/ws"
        session = async_get_clientsession(_manager(request).hass)
        async with session.ws_connect(
            upstream_url,
            headers={"Authorization": f"Bearer {provider['token']}"},
            heartbeat=15,
        ) as upstream:
            async def device_to_provider() -> None:
                async for item in downstream:
                    if item.type == WSMsgType.TEXT:
                        data = item.data
                        try:
                            command = json.loads(data)
                        except (TypeError, json.JSONDecodeError):
                            command = None
                        if isinstance(command, dict) and command.get("command") == "auth":
                            command["args"] = {"token": str(provider["token"])}
                            data = json.dumps(command, separators=(",", ":"))
                        await upstream.send_str(data)
                    elif item.type == WSMsgType.BINARY:
                        await upstream.send_bytes(item.data)

            async def provider_to_device() -> None:
                async for item in upstream:
                    if item.type == WSMsgType.TEXT:
                        await downstream.send_str(item.data)
                    elif item.type == WSMsgType.BINARY:
                        await downstream.send_bytes(item.data)

            tasks = {
                asyncio.create_task(device_to_provider()),
                asyncio.create_task(provider_to_device()),
            }
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            for task in done:
                task.result()
        return downstream


def register_http_views(hass: HomeAssistant) -> None:
    """Register all HTTP views once."""
    hass.http.register_view(PairView())
    hass.http.register_view(DeviceWebSocketView())
    hass.http.register_view(DeviceMessageView())
    hass.http.register_view(DeviceStreamView())
    hass.http.register_view(PanelJavaScriptView())
    hass.http.register_view(PanelFontView())
    hass.http.register_view(ImmichProviderView())
    hass.http.register_view(MusicAssistantProviderView())
