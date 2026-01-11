"""DataUpdateCoordinator for MantelMount MM860."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import MantelMountClient
from .protocol import parse_mmq
from .const import DOMAIN, MANUFACTURER, MODEL, CONF_HOST, CONF_PORT

_LOGGER = logging.getLogger(__name__)


class MantelMountCoordinator(DataUpdateCoordinator[dict]):
    """Coordinator to manage MantelMount data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MantelMountClient,
        poll_interval: float,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
        )
        self._client = client
        self._prev_left: int | None = None
        self._prev_right: int | None = None
        self._was_moving: bool = False
        self._on_movement_stopped_callbacks: list[Callable[[], None]] = []

    @property
    def client(self) -> MantelMountClient:
        """Return the client."""
        return self._client

    def register_on_movement_stopped(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called when movement stops."""
        self._on_movement_stopped_callbacks.append(callback)

    def unregister_on_movement_stopped(self, callback: Callable[[], None]) -> None:
        """Unregister a movement stopped callback."""
        if callback in self._on_movement_stopped_callbacks:
            self._on_movement_stopped_callbacks.remove(callback)

    async def _async_update_data(self) -> dict:
        """Fetch data from MantelMount."""
        try:
            resp = await self._client.send("MMQ", crlf=True, read_reply=True)
            mmq = parse_mmq(resp.raw)

            if mmq is None:
                return {"mmq_ok": False, "last_status_raw": resp.raw}

            # Movement detection: position deltas only
            moving = False
            if self._prev_left is not None and self._prev_right is not None:
                if (mmq.left_actuator != self._prev_left) or (
                    mmq.right_actuator != self._prev_right
                ):
                    moving = True

            self._prev_left = mmq.left_actuator
            self._prev_right = mmq.right_actuator

            # Detect movement stopped transition
            if self._was_moving and not moving:
                _LOGGER.debug("Movement stopped detected, firing callbacks")
                for callback in self._on_movement_stopped_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        _LOGGER.error("Error in movement stopped callback: %s", e)

            self._was_moving = moving

            return {
                "mmq_ok": True,
                "mmq": mmq,
                "moving": moving,
            }

        except Exception as err:
            raise UpdateFailed(f"Error communicating with MantelMount: {err}") from err


def get_device_info(entry: ConfigEntry, firmware: int | None = None) -> DeviceInfo:
    """Return device info for the MantelMount."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"MantelMount ({entry.data[CONF_HOST]})",
        manufacturer=MANUFACTURER,
        model=MODEL,
        sw_version=str(firmware) if firmware else None,
        configuration_url=f"http://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}/",
    )
