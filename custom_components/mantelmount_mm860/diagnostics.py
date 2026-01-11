"""Diagnostics support for MantelMount MM860."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_HOST, CONF_PORT


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id, {})
    coordinator = data.get("coordinator")

    coordinator_data = {}
    if coordinator and coordinator.data:
        coord_data = coordinator.data
        mmq = coord_data.get("mmq")
        coordinator_data = {
            "mmq_ok": coord_data.get("mmq_ok"),
            "moving": coord_data.get("moving"),
            "last_command": coord_data.get("last_command"),
            "last_reply": coord_data.get("last_reply"),
            "mmq": mmq.as_attrs() if mmq else None,
        }

    return {
        "config_entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": {
                CONF_HOST: entry.data.get(CONF_HOST),
                CONF_PORT: entry.data.get(CONF_PORT),
            },
            "options": dict(entry.options),
        },
        "coordinator": coordinator_data,
        "lock_while_moving": data.get("lock_while_moving"),
    }
