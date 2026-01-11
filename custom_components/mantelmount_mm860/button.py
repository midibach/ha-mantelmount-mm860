"""Button platform for MantelMount MM860."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MantelMountCoordinator, get_device_info

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class MantelMountButtonEntityDescription(ButtonEntityDescription):
    """Describes a MantelMount button entity."""

    command: str
    crlf: bool = False  # Use CR only to match native app (per pcap)
    ignore_lock: bool = False  # For stop button


BUTTONS: tuple[MantelMountButtonEntityDescription, ...] = (
    # Control buttons
    MantelMountButtonEntityDescription(
        key="stop",
        translation_key="stop",
        name="Stop",
        icon="mdi:stop",
        command="MMJ0",
        ignore_lock=True,  # Stop should always work
    ),
    MantelMountButtonEntityDescription(
        key="jog_up",
        translation_key="jog_up",
        name="Jog up",
        icon="mdi:arrow-up-bold",
        command="MMJ2",  # Was MMJ1, swapped per user testing
    ),
    MantelMountButtonEntityDescription(
        key="jog_down",
        translation_key="jog_down",
        name="Jog down",
        icon="mdi:arrow-down-bold",
        command="MMJ4",
    ),
    MantelMountButtonEntityDescription(
        key="jog_left",
        translation_key="jog_left",
        name="Jog left",
        icon="mdi:arrow-left-bold",
        command="MMJ3",
    ),
    MantelMountButtonEntityDescription(
        key="jog_right",
        translation_key="jog_right",
        name="Jog right",
        icon="mdi:arrow-right-bold",
        command="MMJ1",  # Was MMJ2, swapped per user testing
    ),
    # Config buttons
    MantelMountButtonEntityDescription(
        key="save_m1",
        translation_key="save_m1",
        name="Save preset 1",
        icon="mdi:content-save",
        command="MMS1",
        entity_category=EntityCategory.CONFIG,
    ),
    MantelMountButtonEntityDescription(
        key="save_m2",
        translation_key="save_m2",
        name="Save preset 2",
        icon="mdi:content-save",
        command="MMS2",
        entity_category=EntityCategory.CONFIG,
    ),
    MantelMountButtonEntityDescription(
        key="save_m3",
        translation_key="save_m3",
        name="Save preset 3",
        icon="mdi:content-save",
        command="MMS3",
        entity_category=EntityCategory.CONFIG,
    ),
    MantelMountButtonEntityDescription(
        key="save_m4",
        translation_key="save_m4",
        name="Save preset 4",
        icon="mdi:content-save",
        command="MMS4",
        entity_category=EntityCategory.CONFIG,
    ),
    # Diagnostic buttons
    MantelMountButtonEntityDescription(
        key="clear_fault",
        translation_key="clear_fault",
        name="Clear fault",
        icon="mdi:alert-circle-outline",
        command="MMC",
        crlf=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MantelMountButtonEntityDescription(
        key="reboot",
        translation_key="reboot",
        name="Reboot",
        icon="mdi:restart",
        command="MMG",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MantelMount buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        MantelMountButton(hass, entry, coordinator, description)
        for description in BUTTONS
    )


class MantelMountButton(CoordinatorEntity[MantelMountCoordinator], ButtonEntity):
    """Button entity for MantelMount."""

    _attr_has_entity_name = True
    entity_description: MantelMountButtonEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: MantelMountCoordinator,
        description: MantelMountButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._hass = hass
        self._entry = entry
        self.entity_description = description
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
        return self.coordinator.last_update_success

    async def async_press(self) -> None:
        """Handle the button press."""
        data = self._hass.data[DOMAIN][self._entry.entry_id]
        lock = data["lock_while_moving"]
        desc = self.entity_description

        # Check lock unless this button ignores it (like Stop)
        if not desc.ignore_lock and lock and (self.coordinator.data or {}).get("moving"):
            _LOGGER.debug("Button %s blocked - mount is moving", desc.key)
            return

        _LOGGER.debug("Button %s pressed - sending command: %s", desc.key, desc.command)
        resp = await data["client"].send(desc.command, crlf=desc.crlf, read_reply=True)
        _LOGGER.debug("Response: %r", resp.raw)

        # Update coordinator with last command for debugging
        self.coordinator.data = {
            **(self.coordinator.data or {}),
            "last_command": desc.command,
            "last_reply": resp.raw,
        }
        self.coordinator.async_set_updated_data(self.coordinator.data)
