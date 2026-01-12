"""Config flow for MantelMount MM860 integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .client import MantelMountClient
from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_LOCK_WHILE_MOVING,
    CONF_HOST,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_POLL_INTERVAL,
    CONF_LOCK_WHILE_MOVING,
)


async def _test_connection(host: str, port: int, timeout: float) -> bool:
    """Test if we can connect to the MantelMount."""
    client = MantelMountClient(host, port, timeout)
    resp = await client.send("MMQ", crlf=True, read_reply=True)
    return resp.raw.startswith("MMQ")


class MantelMountConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MantelMount MM860."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MantelMountOptionsFlow:
        """Get the options flow for this handler."""
        return MantelMountOptionsFlow()

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            timeout = user_input[CONF_TIMEOUT]

            try:
                await _test_connection(host, port, timeout)
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"mantelmount_{host}_{port}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"MantelMount ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                    },
                    options={
                        CONF_TIMEOUT: timeout,
                        CONF_POLL_INTERVAL: user_input[CONF_POLL_INTERVAL],
                        CONF_LOCK_WHILE_MOVING: user_input[CONF_LOCK_WHILE_MOVING],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Coerce(float),
                vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
                    vol.Coerce(float), vol.Range(min=0.1, max=60)
                ),
                vol.Required(CONF_LOCK_WHILE_MOVING, default=DEFAULT_LOCK_WHILE_MOVING): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class MantelMountOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for MantelMount MM860."""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        
        # Handle migration from int to float for poll_interval
        current_poll = options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        if isinstance(current_poll, int):
            current_poll = float(current_poll)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TIMEOUT,
                    default=options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=current_poll,
                ): vol.Coerce(float),
                vol.Required(
                    CONF_LOCK_WHILE_MOVING,
                    default=options.get(CONF_LOCK_WHILE_MOVING, DEFAULT_LOCK_WHILE_MOVING),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
