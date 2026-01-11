"""MantelMount MM860 integration for Home Assistant."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .client import MantelMountClient
from .coordinator import MantelMountCoordinator
from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_POLL_INTERVAL,
    CONF_LOCK_WHILE_MOVING,
    DEFAULT_TIMEOUT,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_LOCK_WHILE_MOVING,
    SERVICE_SEND_COMMAND,
    ATTR_COMMAND,
    ATTR_CRLF,
    ATTR_READ_REPLY,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SELECT,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_COMMAND): cv.string,
        vol.Optional(ATTR_CRLF, default=False): cv.boolean,
        vol.Optional(ATTR_READ_REPLY, default=True): cv.boolean,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MantelMount MM860 from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    # Options (with fallbacks for migration)
    timeout = entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
    poll_interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
    # Handle migration from int to float
    if isinstance(poll_interval, int):
        poll_interval = float(poll_interval)
    lock_while_moving = entry.options.get(CONF_LOCK_WHILE_MOVING, DEFAULT_LOCK_WHILE_MOVING)

    client = MantelMountClient(host=host, port=port, timeout=timeout)
    coordinator = MantelMountCoordinator(hass, client, poll_interval=poll_interval)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "lock_while_moving": lock_while_moving,
        # Preset position tracking
        "stored_presets": {},  # {preset_name: (elevation, azimuth)}
        "pending_preset": None,  # Preset we're currently moving to
    }

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    # Register service (only once globally)
    if not hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        async def handle_send_command(call: ServiceCall) -> None:
            """Handle the send_command service call."""
            # Find first available entry (or could add entry_id as service field)
            for eid, data in hass.data.get(DOMAIN, {}).items():
                if isinstance(data, dict) and "client" in data:
                    lock = data["lock_while_moving"]
                    coord = data["coordinator"]

                    if lock and coord.data and coord.data.get("moving"):
                        raise RuntimeError(
                            "MantelMount is moving; command locked. "
                            "Disable lock_while_moving in options to override."
                        )

                    cmd = call.data[ATTR_COMMAND]
                    crlf = call.data[ATTR_CRLF]
                    read_reply = call.data[ATTR_READ_REPLY]

                    resp = await data["client"].send(cmd, crlf=crlf, read_reply=read_reply)

                    coord.data = {
                        **(coord.data or {}),
                        "last_command": cmd,
                        "last_reply": resp.raw,
                    }
                    coord.async_set_updated_data(coord.data)
                    break

        hass.services.async_register(
            DOMAIN, SERVICE_SEND_COMMAND, handle_send_command, schema=SERVICE_SCHEMA
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # Only remove service if no entries left
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SEND_COMMAND)

    return unload_ok
