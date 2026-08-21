"""Climate platform for Hisense VRF."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import FAN_AUTO, FAN_HIGH, FAN_LOW, FAN_MEDIUM
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    PROP_SET_TEMP,
    PROP_ROOM_TEMP,
    PROP_POWER,
    MODE_REFRIGERATION,
    MODE_HEATING,
    MODE_AUTOMATIC,
    MODE_DEHUMIDIFICATION,
    MODE_SUPPLY_AIR,
    FAN_HIGH as FAN_HIGH_PROP,
    FAN_MEDIUM as FAN_MEDIUM_PROP,
    FAN_LOW as FAN_LOW_PROP,
    FAN_SUPER_HIGH,
    FAN_QUIET,
    FAN_AUTO as FAN_AUTO_PROP,
    TEMP_MIN,
    TEMP_MAX,
)
from .coordinator import HisenseVRFCoordinator

_LOGGER = logging.getLogger(__name__)

FAN_SUPER_HIGH_NAME = "super_high"
FAN_QUIET_NAME = "quiet"

HVAC_MODE_MAP = {
    MODE_REFRIGERATION: HVACMode.COOL,
    MODE_HEATING: HVACMode.HEAT,
    MODE_AUTOMATIC: HVACMode.AUTO,
    MODE_DEHUMIDIFICATION: HVACMode.DRY,
    MODE_SUPPLY_AIR: HVACMode.FAN_ONLY,
}

HVAC_MODE_TO_PROPS = {v: k for k, v in HVAC_MODE_MAP.items()}

FAN_MODE_MAP = {
    FAN_LOW_PROP: FAN_LOW,
    FAN_MEDIUM_PROP: FAN_MEDIUM,
    FAN_HIGH_PROP: FAN_HIGH,
    FAN_SUPER_HIGH: FAN_SUPER_HIGH_NAME,
    FAN_QUIET: FAN_QUIET_NAME,
    FAN_AUTO_PROP: FAN_AUTO,
}

FAN_MODE_TO_PROPS = {v: k for k, v in FAN_MODE_MAP.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hisense VRF climate entities."""
    coordinator: HisenseVRFCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in coordinator.devices:
        device_id = device.get("deviceId", "")
        name = device.get("deviceNickName", device.get("deviceId", "Unknown"))
        if device_id:
            entities.append(
                HisenseVRFClimate(coordinator, device_id, name)
            )
    async_add_entities(entities)


class HisenseVRFClimate(CoordinatorEntity, ClimateEntity):
    """Hisense VRF climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = TEMP_MIN
    _attr_max_temp = TEMP_MAX
    _attr_target_temperature_step = 1.0
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.AUTO,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _attr_fan_modes = [
        FAN_LOW,
        FAN_MEDIUM,
        FAN_HIGH,
        FAN_SUPER_HIGH_NAME,
        FAN_QUIET_NAME,
        FAN_AUTO,
    ]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        coordinator: HisenseVRFCoordinator,
        device_id: str,
        name: str,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_name = name
        self._attr_unique_id = f"hisense_vrf_{device_id}"

    @property
    def _status(self) -> dict[str, str]:
        """Get current device status."""
        return self.coordinator.data.get(self._device_id, {})

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature."""
        val = self._status.get(PROP_ROOM_TEMP)
        return float(val) if val else None

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        val = self._status.get(PROP_SET_TEMP)
        return float(val) if val else None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        if self._status.get(PROP_POWER) != "1":
            return HVACMode.OFF
        for prop, mode in HVAC_MODE_MAP.items():
            if self._status.get(prop) == "1":
                return mode
        return HVACMode.COOL

    @property
    def fan_mode(self) -> str | None:
        """Return current fan mode."""
        if self._status.get(FAN_AUTO_PROP) == "1":
            return FAN_AUTO
        for prop, mode in FAN_MODE_MAP.items():
            if prop != FAN_AUTO_PROP and self._status.get(prop) == "1":
                return mode
        return None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        commands = []
        if hvac_mode == HVACMode.OFF:
            commands.append({"name": PROP_POWER, "value": "0"})
        else:
            # Turn on
            commands.append({"name": PROP_POWER, "value": "1"})
            # Clear all modes
            for prop in HVAC_MODE_MAP:
                commands.append({"name": prop, "value": "0"})
            # Set new mode
            mode_prop = HVAC_MODE_TO_PROPS.get(hvac_mode, MODE_REFRIGERATION)
            commands.append({"name": mode_prop, "value": "1"})

        await self.coordinator.api.send_command(
            self.coordinator.wifi_id, self._device_id, commands
        )
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temp = kwargs.get("temperature")
        if temp is None:
            return
        await self.coordinator.api.send_command(
            self.coordinator.wifi_id,
            self._device_id,
            [{"name": PROP_SET_TEMP, "value": str(int(temp))}],
        )
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        commands = []
        # Clear all fan modes
        for prop in FAN_MODE_TO_PROPS.values():
            commands.append({"name": prop, "value": "0"})
        # Set new fan mode
        fan_prop = FAN_MODE_TO_PROPS.get(fan_mode)
        if fan_prop:
            commands.append({"name": fan_prop, "value": "1"})

        await self.coordinator.api.send_command(
            self.coordinator.wifi_id, self._device_id, commands
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn on."""
        await self.coordinator.api.send_command(
            self.coordinator.wifi_id,
            self._device_id,
            [{"name": PROP_POWER, "value": "1"}],
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn off."""
        await self.coordinator.api.send_command(
            self.coordinator.wifi_id,
            self._device_id,
            [{"name": PROP_POWER, "value": "0"}],
        )
        await self.coordinator.async_request_refresh()
