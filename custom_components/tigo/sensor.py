"""Tigo CCA sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, KEY_COORDINATOR
from .coordinator import PanelStatus, TigoUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TigoSensorEntityDescription(SensorEntityDescription):
    """Class describing Tigo sensor entities."""

    getter: Callable[[PanelStatus], Any] = None


_CCA_TEMP: TigoSensorEntityDescription = TigoSensorEntityDescription(
    key="cca_temperature",
    device_class=SensorDeviceClass.TEMPERATURE,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
)

_VOLTAGE_IN: TigoSensorEntityDescription = TigoSensorEntityDescription(
    key="voltage_in",
    device_class=SensorDeviceClass.VOLTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    getter=lambda panel: panel.voltage_in if not panel.outdated else None,
)
_VOLTAGE_OUT: TigoSensorEntityDescription = TigoSensorEntityDescription(
    key="voltage_out",
    device_class=SensorDeviceClass.VOLTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    getter=lambda panel: panel.voltage_out if not panel.outdated else None,
)
_CURRENT: TigoSensorEntityDescription = TigoSensorEntityDescription(
    key="current",
    device_class=SensorDeviceClass.CURRENT,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    getter=lambda panel: panel.current if not panel.outdated else None,
)
_POWER: TigoSensorEntityDescription = TigoSensorEntityDescription(
    key="power",
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=UnitOfPower.WATT,
    getter=lambda panel: panel.power if not panel.outdated else None,
)
_TEMP: TigoSensorEntityDescription = TigoSensorEntityDescription(
    key="temperature",
    device_class=SensorDeviceClass.TEMPERATURE,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    getter=lambda panel: panel.temperature if not panel.outdated else None,
)
_PWM: TigoSensorEntityDescription = TigoSensorEntityDescription(
    key="pwm",
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:numeric",
    getter=lambda panel: panel.pwm if not panel.outdated else None,
    # entity_category=EntityCategory.DIAGNOSTIC,
)
_STATUS: TigoSensorEntityDescription = TigoSensorEntityDescription(
    key="status",
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:information-outline",
    getter=lambda panel: panel.status if not panel.outdated else None,
    # entity_category=EntityCategory.DIAGNOSTIC,
)
_ONLINE: TigoSensorEntityDescription = TigoSensorEntityDescription(
    key="online",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    icon="mdi:connection",
    getter=lambda panel: not panel.outdated,
    entity_category=EntityCategory.DIAGNOSTIC,
)
_RSSI: TigoSensorEntityDescription = TigoSensorEntityDescription(
    key="rssi",
    device_class=SensorDeviceClass.SIGNAL_STRENGTH,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    getter=lambda panel: panel.rssi if not panel.outdated else None,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
)

_PANEL_SENSORS: tuple[TigoSensorEntityDescription] = (
    _VOLTAGE_IN,
    _VOLTAGE_OUT,
    _CURRENT,
    _POWER,
    _TEMP,
    _PWM,
    _STATUS,
    _ONLINE,
    _RSSI,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor entities from a config entry."""
    coordinator: TigoUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        KEY_COORDINATOR
    ]

    entities: list[TigoPanelSensorEntity] = [
        TigoCcaSensorEntity(coordinator, _CCA_TEMP)
    ]

    for panel in coordinator.data.panels.values():
        entities.extend(
            TigoPanelSensorEntity(coordinator, panel, sensor)
            for sensor in _PANEL_SENSORS
        )

    async_add_entities(entities)


class TigoCcaSensorEntity(CoordinatorEntity[TigoUpdateCoordinator], SensorEntity):
    """Representation of Tigo CCA sensor."""

    entity_description: TigoSensorEntityDescription

    def __init__(
        self,
        coordinator: TigoUpdateCoordinator,
        description: TigoSensorEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_name = f"CCA {description.key}"
        self._attr_unique_id = f"{description.key}-{coordinator.serial_nr}"
        self._attr_device_info = coordinator.device_info
        self.entity_description = description

    @property
    def native_value(self):
        """Return the value reported by the sensor."""
        return self.coordinator.data.temperature


class TigoPanelSensorEntity(CoordinatorEntity[TigoUpdateCoordinator], SensorEntity):
    """Representation of Tigo panel sensor."""

    entity_description: TigoSensorEntityDescription

    def __init__(
        self,
        coordinator: TigoUpdateCoordinator,
        panel: PanelStatus,
        description: TigoSensorEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_name = f"Panel {panel.label} {description.key}"
        self._attr_unique_id = f"{description.key}-{panel.mac}-{coordinator.serial_nr}"
        self._attr_device_info = coordinator.panel_device_infos[panel.label]
        self.entity_description = description
        self.panel_id = panel.label

    def _panel_status(self) -> PanelStatus:
        return self.coordinator.panel_status(self.panel_id)

    @property
    def native_value(self):
        """Return the value reported by the sensor."""
        status: PanelStatus = self._panel_status()
        return self.entity_description.getter(status) if status else None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.native_value is not None
