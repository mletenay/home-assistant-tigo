"""Tigo CCA action button entities."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, KEY_COORDINATOR
from .coordinator import TigoCCA, TigoUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TigoCcaEntityDescription(ButtonEntityDescription):
    """Class describing Tigo CCA button entities."""

    action: Callable[[TigoCCA], Awaitable[None]]


BUTTONS = (
    TigoCcaEntityDescription(
        key="modules_off",
        translation_key="turn_modules_off",
        icon="mdi:solar-power-variant-outline",
        entity_category=EntityCategory.CONFIG,
        action=lambda cca: cca.turn_modules_off(),
    ),
    TigoCcaEntityDescription(
        key="modules_on",
        translation_key="turn_modules_on",
        icon="mdi:solar-power-variant",
        entity_category=EntityCategory.CONFIG,
        action=lambda cca: cca.turn_modules_on(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the CCA button entities from a config entry."""
    coordinator: TigoUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        KEY_COORDINATOR
    ]

    entities = []

    entities.extend(TigoCcaButtonEntity(coordinator, button) for button in BUTTONS)

    async_add_entities(entities)


class TigoCcaButtonEntity(CoordinatorEntity[TigoUpdateCoordinator], ButtonEntity):
    """Entity representing CCA action button."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    entity_description: TigoCcaEntityDescription

    def __init__(
        self,
        coordinator: TigoUpdateCoordinator,
        description: TigoCcaEntityDescription,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{description.key}--{coordinator.serial_nr}"
        self._attr_device_info = coordinator.device_info
        self.entity_description = description

    async def async_press(self) -> None:
        """Triggers the button press service."""
        await self.entity_description.action(self.coordinator.cca)
