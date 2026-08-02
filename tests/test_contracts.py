from __future__ import annotations

import json
from pathlib import Path

import pytest
import voluptuous as vol

from custom_components.rustyhama.api import DeviceWebSocketView, PanelJavaScriptView
from custom_components.rustyhama.merge import merge_patch, redact_secrets
from custom_components.rustyhama.protocol import envelope, validate_message
from custom_components.rustyhama.schema import DashboardValidationError, validate_dashboard


def test_merge_patch_vectors() -> None:
    vectors = json.loads(Path("test-vectors/merge-patch.json").read_text())
    for vector in vectors:
        assert merge_patch(vector["profile"], vector["patch"]) == vector["result"]


def test_protocol_round_trip() -> None:
    message = envelope("heartbeat", {"sequence": 1}, revision=8)
    assert validate_message(message) == message


def test_protocol_rejects_other_version() -> None:
    message = envelope("heartbeat")
    message["version"] = 2
    with pytest.raises(vol.Invalid):
        validate_message(message)


def test_dashboard_validation() -> None:
    assert validate_dashboard({"schema_version": 1, "tabs": [{"id": "a", "widgets": []}]}) == []
    with pytest.raises(DashboardValidationError):
        validate_dashboard({"schema_version": 1, "tabs": []})


def test_secret_redaction_is_recursive() -> None:
    value = redact_secrets({"provider": {"api_key": "secret", "name": "photos"}})
    assert value == {"provider": {"api_key": "**REDACTED**", "name": "photos"}}


def test_panel_module_can_be_loaded_without_auth_header() -> None:
    assert PanelJavaScriptView.requires_auth is False


def test_device_control_channel_uses_application_heartbeat() -> None:
    """Transport pings must not compete with Android's protocol heartbeat."""
    source = Path("custom_components/rustyhama/api.py").read_text()
    control_view = source[source.index("class DeviceWebSocketView") : source.index("class DeviceStreamView")]
    assert "WebSocketResponse(max_msg_size=" in control_view
    assert "heartbeat=" not in control_view
    assert DeviceWebSocketView.requires_auth is False


def test_provider_proxies_preserve_android_compatibility_contract() -> None:
    source = Path("custom_components/rustyhama/api.py").read_text()
    immich = source[
        source.index("class ImmichProviderView") : source.index(
            "class MusicAssistantProviderView"
        )
    ]
    music = source[
        source.index("class MusicAssistantProviderView") : source.index(
            "def register_http_views"
        )
    ]
    assert 'for name in ("Accept", "Content-Type")' in immich
    assert 'tail != "imageproxy"' in music
    downstream = music[music.index("downstream =") : music.index("await downstream.prepare")]
    assert "heartbeat=" not in downstream
