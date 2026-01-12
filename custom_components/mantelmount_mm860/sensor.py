"""Sensor platform for MantelMount MM860."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MantelMountCoordinator, get_device_info

_LOGGER = logging.getLogger(__name__)

# Position tolerance for matching presets (in device units)
POSITION_TOLERANCE = 3


@dataclass(frozen=True, kw_only=True)
class MantelMountSensorEntityDescription(SensorEntityDescription):
    """Describes a MantelMount sensor entity."""

    mmq_key: str


SENSORS: tuple[MantelMountSensorEntityDescription, ...] = (
    MantelMountSensorEntityDescription(
        key="elevation",
        mmq_key="elevation",
        translation_key="elevation",
        name="Elevation",
        icon="mdi:arrow-up-down",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MantelMountSensorEntityDescription(
        key="azimuth",
        mmq_key="azimuth",
        translation_key="azimuth",
        name="Azimuth",
        icon="mdi:arrow-left-right",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MantelMountSensorEntityDescription(
        key="left_actuator",
        mmq_key="left_actuator",
        translation_key="left_actuator",
        name="Left actuator",
        icon="mdi:ray-vertex",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MantelMountSensorEntityDescription(
        key="right_actuator",
        mmq_key="right_actuator",
        translation_key="right_actuator",
        name="Right actuator",
        icon="mdi:ray-vertex",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MantelMountSensorEntityDescription(
        key="temperature",
        mmq_key="temperature",
        translation_key="temperature",
        name="Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        # No entity_category - shown as main sensor
    ),
    MantelMountSensorEntityDescription(
        key="tv_current",
        mmq_key="tv_current",
        translation_key="tv_current",
        name="TV current",
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MantelMountSensorEntityDescription(
        key="left_motor_current",
        mmq_key="left_motor_current",
        translation_key="left_motor_current",
        name="Left motor current",
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MantelMountSensorEntityDescription(
        key="right_motor_current",
        mmq_key="right_motor_current",
        translation_key="right_motor_current",
        name="Right motor current",
        icon="mdi:current-ac",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MantelMountSensorEntityDescription(
        key="firmware_version",
        mmq_key="firmware_version",
        translation_key="firmware_version",
        name="Firmware version",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MantelMountSensorEntityDescription(
        key="last_preset",
        mmq_key="last_preset",
        translation_key="last_preset",
        name="Last preset",
        icon="mdi:numeric",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MantelMount sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities: list[SensorEntity] = [
        MantelMountSensor(entry, coordinator, description) for description in SENSORS
    ]
    
    # Add the special current preset sensor
    entities.append(MantelMountCurrentPresetSensor(hass, entry, coordinator))
    
    async_add_entities(entities)


class MantelMountSensor(CoordinatorEntity[MantelMountCoordinator], SensorEntity):
    """Sensor entity for MantelMount."""

    _attr_has_entity_name = True
    entity_description: MantelMountSensorEntityDescription

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: MantelMountCoordinator,
        description: MantelMountSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def device_info(self):
        """Return device info."""
        mmq = (self.coordinator.data or {}).get("mmq")
        firmware = mmq.firmware_version if mmq else None
        return get_device_info(self._entry, firmware)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
        data = self.coordinator.data or {}
        return data.get("mmq_ok", False)

    @property
    def native_value(self):
        """Return the sensor value."""
        data = self.coordinator.data or {}
        mmq = data.get("mmq")
        if not mmq:
            return None
        return getattr(mmq, self.entity_description.mmq_key, None)


class MantelMountCurrentPresetSensor(CoordinatorEntity[MantelMountCoordinator], SensorEntity):
    """Sensor showing current preset based on position matching."""

    _attr_has_entity_name = True
    _attr_name = "Current Preset"
    _attr_icon = "mdi:bookmark"
    _attr_translation_key = "current_preset"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: MantelMountCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_current_preset"

    @property
    def device_info(self):
        """Return device info."""
        mmq = (self.coordinator.data or {}).get("mmq")
        firmware = mmq.firmware_version if mmq else None
        return get_device_info(self._entry, firmware)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
        data = self.coordinator.data or {}
        return data.get("mmq_ok", False)

    def _get_current_position(self) -> tuple[int, int] | None:
        """Get current elevation and azimuth."""
        mmq = (self.coordinator.data or {}).get("mmq")
        if not mmq:
            return None
        return (mmq.elevation, mmq.azimuth)

    def _find_matching_preset(self) -> str | None:
        """Find which preset matches current position, if any."""
        current = self._get_current_position()
        if current is None:
            return None

        data = self._hass.data[DOMAIN][self._entry.entry_id]
        stored = data.get("stored_presets", {})

        current_elev, current_azim = current

        for preset_name, (stored_elev, stored_azim) in stored.items():
            elev_diff = abs(current_elev - stored_elev)
            azim_diff = abs(current_azim - stored_azim)

            if elev_diff <= POSITION_TOLERANCE and azim_diff <= POSITION_TOLERANCE:
                return preset_name

        return None

    @property
    def native_value(self) -> str | None:
        """Return the current preset name or None."""
        data = self._hass.data[DOMAIN][self._entry.entry_id]
        moving = (self.coordinator.data or {}).get("moving", False)
        pending = data.get("pending_preset")

        # If moving to a preset, show that as the target
        if moving and pending:
            return pending

        # Otherwise find matching preset based on position
        return self._find_matching_preset()

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        data = self._hass.data[DOMAIN][self._entry.entry_id]
        stored = data.get("stored_presets", {})
        current = self._get_current_position()
        moving = (self.coordinator.data or {}).get("moving", False)

        attrs = {
            "learned_presets": list(stored.keys()),
            "moving": moving,
        }

        if current:
            attrs["current_elevation"] = current[0]
            attrs["current_azimuth"] = current[1]

        return attrs
