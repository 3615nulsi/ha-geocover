"""Constants for the Geocover integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Final

DOMAIN: Final = "geocover"
LOGGER = logging.getLogger(__package__)

CONF_TOKENS: Final = "tokens"
CONF_REDIRECT_URL: Final = "redirect_url"

# The bike only reports its position when it moves or connects: polling more often
# would not bring fresher data and would put needless load on a third-party service.
# The interval adapts to the bikes' activity (see coordinator.interval_for).
UPDATE_INTERVAL: Final = timedelta(minutes=5)
RIDING_INTERVAL: Final = timedelta(minutes=1)
IDLE_INTERVAL: Final = timedelta(minutes=15)
# Time without any reported position after which the bikes are considered asleep.
IDLE_AFTER: Final = timedelta(hours=3)
