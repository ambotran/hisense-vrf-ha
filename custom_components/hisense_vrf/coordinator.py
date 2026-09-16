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
        try:
            if not self.api.access_token:
                if not await self.api.login():
                    raise UpdateFailed("Login failed")
            if not self.devices:
                self.devices = await self.api.get_devices(self.home_id)
                if not self.devices:
                    raise UpdateFailed("Could not fetch device list (empty response)")
            status_map: dict[str, dict] = {}
            failed_devices: list[str] = []
            for device in self.devices:
                device_id = device.get("deviceId", "")
                if not device_id:
                    continue
                result = await self.api.get_device_properties(
                    [{"deviceId": device_id, "wifiId": self.wifi_id}]
                )
                if not result:
                    failed_devices.append(device_id)
                    continue
                device_data = result[0]
                props = device_data.get("status") or device_data.get("allStatus") or {}
                    props.get("Y_K_Q_control"), props.get("modeRefrigeration"), props.get("modeSupplyAir"))
                if not props:
                    failed_devices.append(device_id)
                    continue
                status_map[device_id] = props
    
            if failed_devices and not status_map:
                # All devices failed — token likely expired, re-login
                _LOGGER.warning("All devices failed, attempting re-login")
                if await self.api.login():
                    self.devices = []  # force device re-fetch
                    raise UpdateFailed("Re-logged in, will retry next cycle")
                raise UpdateFailed(f"No valid status returned for any device (failed: {', '.join(failed_devices)})")
    
            return status_map
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err