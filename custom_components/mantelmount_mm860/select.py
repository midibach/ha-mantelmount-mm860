"""Select platform for MantelMount MM860."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MantelMountCoordinator, get_device_info

_LOGGER = logging.getLogger(__name__)

OPTIONS = ["Home", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]

# Position tolerance for matching presets (in device units)
# Tighter tolerance ensures accurate preset detection
POSITION_TOLERANCE = 3


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MantelMount select entity."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MantelMountPositionSelect(hass, entry, data["coordinator"])])


class MantelMountPositionSelect(CoordinatorEntity[MantelMountCoordinator], SelectEntity, RestoreEntity):
    """Select entity for MantelMount position presets."""

    _attr_has_entity_name = True
    _attr_name = "Position"
    _attr_options = OPTIONS
    _attr_icon = "mdi:television"
    _attr_translation_key = "position"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: MantelMountCoordinator,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_position"
        
        # Register callback for when movement stops
        coordinator.register_on_movement_stopped(self._on_movement_stopped)

    async def async_added_to_hass(self) -> None:
        """Restore learned presets when entity is added."""
        await super().async_added_to_hass()
        
        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            # Restore learned presets from attributes
            attrs = last_state.attributes
            data = self._hass.data[DOMAIN][self._entry.entry_id]
            
            for preset in OPTIONS:
                elev_key = f"{preset}_elevation"
                azim_key = f"{preset}_azimuth"
                if elev_key in attrs and azim_key in attrs:
                    data["stored_presets"][preset] = (attrs[elev_key], attrs[azim_key])
                    _LOGGER.debug("Restored preset %s: (%s, %s)", preset, attrs[elev_key], attrs[azim_key])
            
            if data["stored_presets"]:
                _LOGGER.info("Restored %d learned presets from previous state", len(data["stored_presets"]))

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callback when entity is removed."""
        self.coordinator.unregister_on_movement_stopped(self._on_movement_stopped)
        await super().async_will_remove_from_hass()

    @callback
    def _on_movement_stopped(self) -> None:
        """Handle movement stopped - learn preset position if we were moving to one."""
        data = self._hass.data[DOMAIN][self._entry.entry_id]
        pending = data.get("pending_preset")
        
        if pending is None:
            return
            
        # Get current position
        mmq = (self.coordinator.data or {}).get("mmq")
        if not mmq:
            _LOGGER.warning("Movement stopped but no MMQ data available")
            return
            
        # Store the position for this preset
        position = (mmq.elevation, mmq.azimuth)
        data["stored_presets"][pending] = position
        _LOGGER.info(
            "Learned position for preset %s: elevation=%d, azimuth=%d",
            pending, mmq.elevation, mmq.azimuth
        )
        
        # Clear pending
        data["pending_preset"] = None
        
        # Update state
        self.async_write_ha_state()

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
    def current_option(self) -> str | None:
        """Return the current preset based on position matching."""
        data = self._hass.data[DOMAIN][self._entry.entry_id]
        
        # If we're moving to a preset, show that as pending
        pending = data.get("pending_preset")
        if pending and (self.coordinator.data or {}).get("moving"):
            return pending  # Show target while moving
            
        # Otherwise, find matching preset based on position
        return self._find_matching_preset()

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes showing learned presets."""
        data = self._hass.data[DOMAIN][self._entry.entry_id]
        stored = data.get("stored_presets", {})
        pending = data.get("pending_preset")
        current = self._get_current_position()
        
        attrs = {
            "learned_presets": list(stored.keys()),
            "pending_preset": pending,
        }
        
        if current:
            attrs["current_elevation"] = current[0]
            attrs["current_azimuth"] = current[1]
            
        # Show stored positions for debugging
        for preset_name, (elev, azim) in stored.items():
            attrs[f"{preset_name}_elevation"] = elev
            attrs[f"{preset_name}_azimuth"] = azim
            
        return attrs

    async def async_select_option(self, option: str) -> None:
        """Change the selected option (move to preset)."""
        data = self._hass.data[DOMAIN][self._entry.entry_id]
        lock = data["lock_while_moving"]
        moving = (self.coordinator.data or {}).get("moving")

        if lock and moving:
            _LOGGER.debug("Command blocked - mount is moving")
            return

        client = data["client"]

        # Home=MMR0, M1=MMR1, M2=MMR2, etc.
        if option == "Home":
            idx = 0
        else:
            idx = int(option[1:])
        cmd = f"MMR{idx}"
        
        # Set pending preset so we learn its position when movement stops
        data["pending_preset"] = option
        
        _LOGGER.debug("Select sending command: %s (option=%r), pending_preset set", cmd, option)
        resp = await client.send(cmd, crlf=False, read_reply=True)
        _LOGGER.debug("Select response: %r", resp.raw)

        # Update coordinator with last command for debugging
        self.coordinator.data = {
            **(self.coordinator.data or {}),
            "last_command": cmd,
            "last_reply": resp.raw,
        }
        self.coordinator.async_set_updated_data(self.coordinator.data)
