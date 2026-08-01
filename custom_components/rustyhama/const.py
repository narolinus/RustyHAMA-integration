"""Constants for RustyHAMA."""

from __future__ import annotations

DOMAIN = "rustyhama"
NAME = "RustyHAMA"
PROTOCOL_VERSION = 1
MIN_APP_PROTOCOL = 1
STORAGE_KEY = "rustyhama"
STORAGE_VERSION = 1
SUBENTRY_TYPE_DEVICE = "device"

PAIR_PATH = "/api/rustyhama/v1/pair"
DEVICE_WS_PATH = "/api/rustyhama/v1/device/ws"
STREAM_PATH = "/api/rustyhama/v1/device/streams/{session_id}"
PROVIDER_PATH = "/api/rustyhama/v1/device/providers/{provider_id}/immich/{tail:.*}"
MA_PROVIDER_PATH = (
    "/api/rustyhama/v1/device/providers/{provider_id}/music_assistant/{tail:.*}"
)
PANEL_PATH = "/api/rustyhama/frontend"
PANEL_URL = "rustyhama"

PLATFORMS = (
    "assist_satellite",
    "binary_sensor",
    "button",
    "camera",
    "media_player",
    "number",
    "select",
    "sensor",
    "switch",
)

DEFAULT_PROFILE_ID = "default"
DEFAULT_PROFILE = {
    "schema_version": 1,
    "theme": "dark",
    "app": {"language": "auto", "keep_screen_on": True},
    "voice_assistant": {"enabled": False, "wake_word": False},
    "device_cameras": {
        "enabled": False,
        "transport": "direct",
        "stream_fps": 5,
        "jpeg_quality": 75,
        "max_width": 1280,
    },
    "media_player": {"enabled": False},
    "tabs": [
        {
            "id": "overview",
            "title": "Overview",
            "columns": 2,
            "widgets": [{"id": "clock", "type": "clock", "colspan": 2}],
        }
    ],
}

MAX_REVISIONS = 20
PAIR_TTL_SECONDS = 600
PAIR_MAX_ATTEMPTS = 5
DEVICE_TOKEN_BYTES = 32
HEARTBEAT_SECONDS = 15
OFFLINE_AFTER_SECONDS = 45

SERVICE_SEND_NOTIFICATION = "send_notification"
SERVICE_SET_ACTIVE_TAB = "set_active_tab"
SERVICE_SET_SCREENSAVER = "set_screensaver"
SERVICE_RELOAD_CONFIGURATION = "reload_configuration"

EVENT_DEVICE_UPDATED = "rustyhama_device_updated"
SIGNAL_DEVICE_UPDATED = f"{DOMAIN}_device_updated"
SIGNAL_DEVICES_CHANGED = f"{DOMAIN}_devices_changed"
SIGNAL_ASSIST_START = f"{DOMAIN}_assist_start"
SIGNAL_ASSIST_EVENT = f"{DOMAIN}_assist_event"

SECRET_FIELDS = frozenset(
    {"api_key", "token", "password", "secret", "credential", "device_token_hash"}
)
