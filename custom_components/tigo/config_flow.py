"""Config flow to configure Tigo CCA integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_NAME, DOMAIN
from .tigo_cca import TigoCCA

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="tigo.local"): str,
        vol.Required(CONF_USERNAME, default="Tigo"): str,
        vol.Required(CONF_PASSWORD, default="$olar"): str,
    }
)

_LOGGER = logging.getLogger(__name__)


class TigoFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Tigo CCA config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input:
            host = user_input[CONF_HOST]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                tigo = TigoCCA(host, username, password)
                status = await tigo.get_status()
            except Exception:
                errors["base"] = "connection_error"
            else:
                await self.async_set_unique_id(status.unit_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )
