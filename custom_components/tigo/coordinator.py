"""Update coordinator for Tigo CCA."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL
from .tigo_cca import PanelStatus, PanelVersionInfo, TigoCCA, TigoCcaStatus

_LOGGER = logging.getLogger(__name__)


class TigoUpdateCoordinator(DataUpdateCoordinator[TigoCcaStatus]):
    """Gather data for the energy device."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        cca: TigoCCA,
        status: TigoCcaStatus,
    ) -> None:
        """Initialize update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=SCAN_INTERVAL,
            update_method=self._async_update_data,
        )
        self.cca = cca
        self.serial_nr = status.unit_id
        self.device_info = _cca_device(cca, status)
        self.panel_device_infos = {
            p.label: _panel_device(status, p) for p in cca.panels.values()
        }

    async def _async_update_data(self) -> TigoCcaStatus:
        """Fetch data from the inverter."""
        try:
            return await self.cca.get_status()
        except Exception as ex:
            raise UpdateFailed(ex) from ex

    def panel_status(self, label: str) -> PanelStatus:
        """Return panel status."""
        return self.data.panels.get(label)


def _cca_device(cca: TigoCCA, status: TigoCcaStatus) -> DeviceInfo:
    return DeviceInfo(
        configuration_url=cca.url_root + "/cgi-bin/mmdstatus",
        identifiers={(DOMAIN, status.unit_id)},
        name=f"Tigo CCA {status.unit_id}",
        manufacturer="Tigo",
        serial_number=status.unit_id,
        hw_version=status.hw_platform,
        sw_version=status.fw_version,
    )


def _panel_device(cca: TigoCcaStatus, panel: PanelVersionInfo) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, panel.mac)},
        name=f"Panel {panel.label}",
        manufacturer="Tigo",
        model=panel.model,
        via_device=(DOMAIN, cca.unit_id),
        serial_number=panel.mac,
        hw_version=panel.hw,
        sw_version=panel.fw,
    )
