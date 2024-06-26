"""Constants for the Tigo CCA component."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "tigo"

PLATFORMS = [Platform.BUTTON, Platform.SENSOR]

DEFAULT_NAME = "Tigo CCA"
SCAN_INTERVAL = timedelta(seconds=30)

KEY_COORDINATOR = "coordinator"
