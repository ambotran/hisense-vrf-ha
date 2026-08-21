"""Config flow for Hisense VRF integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import HisenseVRFApi
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_HOME_ID, CONF_WIFI_ID

_LOGGER = logging.getLogger(__name__)


class HisenseVRFConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hisense VRF."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._api: HisenseVRFApi | None = None
        self._username: str = ""
        self._password: str = ""
        self._homes: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            self._api = HisenseVRFApi(self._username, self._password)

            if await self._api.login():
                self._homes = await self._api.get_homes()
                if self._homes:
                    return await self.async_step_home()
                errors["base"] = "no_homes"
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )

    async def async_step_home(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle home selection step."""
        if user_input is not None:
            home_id = user_input[CONF_HOME_ID]
            wifi_id = user_input[CONF_WIFI_ID]

            return self.async_create_entry(
                title=f"Hisense VRF ({self._username})",
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_HOME_ID: home_id,
                    CONF_WIFI_ID: wifi_id,
                },
            )

        home_options = {
            h.get("homeId", ""): h.get("homeName", h.get("homeId", "Unknown"))
            for h in self._homes
        }

        return self.async_show_form(
            step_id="home",
            data_schema=vol.Schema({
                vol.Required(CONF_HOME_ID): vol.In(home_options),
                vol.Required(CONF_WIFI_ID): str,
            }),
            description_placeholders={
                "wifi_id_hint": "Find your Hi-Mit II WiFi ID in the ConnectLife app device details"
            },
        )
