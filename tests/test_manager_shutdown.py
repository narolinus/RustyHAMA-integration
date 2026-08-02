"""Lifecycle regression tests for the RustyHAMA manager."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.rustyhama.manager import RustyManager
from custom_components.rustyhama.models import DeviceSession


@pytest.mark.asyncio
async def test_shutdown_closes_orphanable_sessions_and_background_work() -> None:
    """An integration reload must force devices onto the replacement manager."""
    manager = object.__new__(RustyManager)
    websocket = SimpleNamespace(closed=False, close=AsyncMock())
    session = DeviceSession("device-1", websocket, 1)
    watchdog = MagicMock()
    refresh = MagicMock()
    pending: asyncio.Future[dict[str, object]] = asyncio.get_running_loop().create_future()
    stream: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=1)
    stream.put_nowait(b"buffered")
    device = SimpleNamespace(online=True, last_seen="")
    storage = SimpleNamespace(devices={"device-1": device}, async_save=AsyncMock())

    manager.sessions = {"device-1": session}
    manager._watchdog_tasks = {"device-1": watchdog}
    manager._refresh_tasks = {"device-1": refresh}
    manager._pending_acks = {"command-1": pending}
    manager.streams = {"stream-1": stream}
    manager.storage = storage

    await manager.async_shutdown()

    assert manager.sessions == {}
    watchdog.cancel.assert_called_once_with()
    refresh.cancel.assert_called_once_with()
    websocket.close.assert_awaited_once_with(code=1012, message=b"integration reload")
    assert isinstance(pending.exception(), ConnectionError)
    assert await stream.get() is None
    assert device.online is False
    storage.async_save.assert_awaited_once_with()
