"""Sensor platform for Hisense VRF integration."""
from __future__ import annotations

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROP_ROOM_TEMP, PROP_SET_TEMP, PROP_OPERATING_STATE
from .coordinator import HisenseVRFCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hisense VRF sensors."""
    coordinator: HisenseVRFCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in coordinator.devices:
        device_id = device.get("deviceId", "")
        name = device.get("deviceNickName") or device.get("deviceName") or device_id
        if not device_id:
            continue
        entities.append(HisenseRoomTempSensor(coordinator, device_id, name))
        entities.append(HisenseTargetTempSensor(coordinator, device_id, name))
        entities.append(HisenseOperatingStateSensor(coordinator, device_id, name))
    async_add_entities(entities)


class HisenseVRFSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for Hisense VRF."""

    def __init__(
        self,
        coordinator: HisenseVRFCoordinator,
        device_id: str,
        device_name: str,
        sensor_key: str,
        sensor_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._sensor_key = sensor_key
        self._attr_unique_id = f"hisense_vrf_{device_id}_{sensor_key}"
        self._attr_name = f"{device_name} {sensor_suffix}"
        self._device_name = device_name

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        def on_ws_update(functions: dict) -> None:
            self.hass.loop.call_soon_threadsafe(
                self.coordinator.async_set_updated_data,
                {**self.coordinator.data, self._device_id: functions},
            )

        self.coordinator.api.register_state_callback(self._device_id, on_ws_update)
    @property
    def _status(self) -> dict:
        return self.coordinator.data.get(self._device_id, {})

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "Hisense",
            "model": "VRF Indoor Unit",
        }


class HisenseRoomTempSensor(HisenseVRFSensor):
    """Room temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, device_id, device_name):
        super().__init__(coordinator, device_id, device_name, PROP_ROOM_TEMP, "Room Temperature")

    @property
    def native_value(self) -> float | None:
        val = self._status.get(PROP_ROOM_TEMP)
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None


class HisenseTargetTempSensor(HisenseVRFSensor):
    """Target temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, device_id, device_name):
        super().__init__(coordinator, device_id, device_name, PROP_SET_TEMP, "Target Temperature")

    @property
    def native_value(self) -> float | None:
        val = self._status.get(PROP_SET_TEMP)
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

class HisenseOperatingStateSensor(HisenseVRFSensor):
    """Operating state sensor."""

    def __init__(self, coordinator, device_id, device_name):
        super().__init__(coordinator, device_id, device_name, PROP_OPERATING_STATE, "Operating State")

    @property
    def native_value(self) -> str | None:
        return self._status.get(PROP_OPERATING_STATE)