"""Data coordinator for Hisense VRF."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HisenseVRFApi
from .const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_HOME_ID,
    CONF_WIFI_ID,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class HisenseVRFCoordinator(DataUpdateCoordinator):
    """Coordinator to manage Hisense VRF data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.api = HisenseVRFApi(
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
        )
        self.home_id: str = entry.data[CONF_HOME_ID]
        self.wifi_id: str = entry.data[CONF_WIFI_ID]
        self.devices: list[dict] = []

        super().__init__(
            hass,
            _LOGGER,
            name="Hisense VRF",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from API."""
        try:
            if not self.api.access_token:
                if not await self.api.login():
                    raise UpdateFailed("Login failed")

            if not self.devices:
                self.devices = await self.api.get_devices(self.home_id)

            # Fetch status for all devices
            status_map = {}
            for device in self.devices:
                device_id = device.get("deviceId", "")
                if device_id:
                    status = await self.api.get_device_status(self.wifi_id, device_id)
                    status_map[device_id] = status

            return status_map

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
