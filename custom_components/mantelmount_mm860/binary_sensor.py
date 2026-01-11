"""Binary sensor platform for MantelMount MM860."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MantelMountCoordinator, get_device_info


@dataclass(frozen=True, kw_only=True)
class MantelMountBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a MantelMount binary sensor entity."""

    value_fn: Callable[[dict], bool | None]


def _get_moving(data: dict) -> bool | None:
    """Get moving state."""
    return data.get("moving")


def _get_left_at_limit(data: dict) -> bool | None:
    """Get left at limit state."""
    mmq = data.get("mmq")
    if not mmq:
        return None
    return mmq.left_at_limit == 1


def _get_right_at_limit(data: dict) -> bool | None:
    """Get right at limit state."""
    mmq = data.get("mmq")
    if not mmq:
        return None
    return mmq.right_at_limit == 1


def _get_lost_flag(data: dict) -> bool | None:
    """Get lost flag state."""
    mmq = data.get("mmq")
    if not mmq:
        return None
    return mmq.lost_flag == 1


BINARY_SENSORS: tuple[MantelMountBinarySensorEntityDescription, ...] = (
    MantelMountBinarySensorEntityDescription(
        key="moving",
        translation_key="moving",
        name="Moving",
        icon="mdi:motion-sensor",
        device_class=BinarySensorDeviceClass.MOVING,
        value_fn=_get_moving,
    ),
    MantelMountBinarySensorEntityDescription(
        key="left_at_limit",
        translation_key="left_at_limit",
        name="Left at limit",
        icon="mdi:arrow-expand-vertical",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_get_left_at_limit,
    ),
    MantelMountBinarySensorEntityDescription(
        key="right_at_limit",
        translation_key="right_at_limit",
        name="Right at limit",
        icon="mdi:arrow-expand-vertical",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_get_right_at_limit,
    ),
    MantelMountBinarySensorEntityDescription(
        key="lost_flag",
        translation_key="lost_flag",
        name="Lost flag",
        icon="mdi:alert-circle-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_get_lost_flag,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MantelMount binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        MantelMountBinarySensor(entry, coordinator, description)
        for description in BINARY_SENSORS
    )


class MantelMountBinarySensor(CoordinatorEntity[MantelMountCoordinator], BinarySensorEntity):
    """Binary sensor entity for MantelMount."""

    _attr_has_entity_name = True
    entity_description: MantelMountBinarySensorEntityDescription

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: MantelMountCoordinator,
        description: MantelMountBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
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
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        data = self.coordinator.data or {}
        return self.entity_description.value_fn(data)
