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
        self._api: HisenseVRFApi | None = None
        self._username: str = ""
        self._password: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            self._api = HisenseVRFApi(self._username, self._password)
            if await self._api.login():
                return await self.async_step_home()
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
        if user_input is not None:
            return self.async_create_entry(
                title=f"Hisense VRF ({self._username})",
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_HOME_ID: user_input[CONF_HOME_ID],
                    CONF_WIFI_ID: user_input[CONF_WIFI_ID],
                },
            )
        return self.async_show_form(
            step_id="home",
            data_schema=vol.Schema({
                vol.Required(CONF_HOME_ID, default="107515"): str,
                vol.Required(CONF_WIFI_ID, default="865004100040004000400000187e04497d1c"): str,
            }),
        )