"""Support for Tigo CCA."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, KEY_COORDINATOR, PLATFORMS
from .coordinator import TigoUpdateCoordinator
from .tigo_cca import TigoCCA

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Tigo CCA components from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    try:
        _LOGGER.debug("Connecting to Tigo CCA at %s", host)
        cca = TigoCCA(host, username, password)
        await cca.read_config()
        status = await cca.get_status()
    except Exception as err:
        raise ConfigEntryNotReady from err

    # Create update coordinator
    coordinator = TigoUpdateCoordinator(hass, entry, cca, status)

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        KEY_COORDINATOR: coordinator,
    }

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
