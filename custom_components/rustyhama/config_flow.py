"""Config and device subentry flows for RustyHAMA."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigSubentryFlow

from .const import DOMAIN, SUBENTRY_TYPE_DEVICE


class RustyHAMAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create the single RustyHAMA hub entry."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Set up the hub; devices are subsequently paired in the panel."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title="RustyHAMA", data={})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={"panel": "RustyHAMA"},
        )

    @classmethod
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Expose device subentries to Home Assistant."""
        return {SUBENTRY_TYPE_DEVICE: DeviceSubentryFlow}


class DeviceSubentryFlow(ConfigSubentryFlow):
    """Explain that devices are securely paired through the panel."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Do not create unpaired device records from a plain form."""
        return self.async_abort(reason="use_pairing_panel")
