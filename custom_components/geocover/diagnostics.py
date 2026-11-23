"""Diagnostics support, with sensitive data redacted.

The raw API payloads are kept because they are what helps debugging, but the API is
undocumented and may add fields at any time. So, rather than only listing sensitive
keys, every string is redacted unless its key is known to be technical or its value
is obviously harmless (a date, a boolean, a short number or percentage).
"""

from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant
import pygeocover

from .const import CONF_TOKENS
from .coordinator import GeocoverConfigEntry

# Always redacted, whatever the type of the value.
TO_REDACT = {
    CONF_TOKENS,
    "access_token",
    "activation_code",
    "blename",
    "blepass",
    "center",
    "conneqtech_id",
    "email",
    "frame_number",
    "imei",
    "invite_code",
    "invite_code_uri",
    "lat",
    "linked_users",
    "lon",
    "name",
    "owning_user",
    "refresh_token",
    "user_name",
    "username",
}

# Keys whose string values are technical and kept as they are.
SAFE_STRING_KEYS = {
    "brand",
    "key",
    "manufacturer",
    "model",
    "model_name",
    "ride_type",
    "status",
    "timezone",
    "type",
    "value_type",
    "weather_type",
}

_HARMLESS_STRING = re.compile(
    r"""^(
        \d{4}-\d{2}-\d{2}([T ][\d:.]+)?(Z|[+-]\d{2}:?\d{2})?  # date or date-time
        |true|false|null
        |-?\d{1,6}([.,]\d+)?\s?%?                           # short number or percentage
    )$""",
    re.IGNORECASE | re.VERBOSE,
)


def redact(data: Any, key: str | None = None) -> Any:
    """Redact `data` recursively (see the module docstring)."""
    if key in TO_REDACT and data not in (None, "", [], {}):
        return REDACTED
    if isinstance(data, dict):
        return {k: redact(v, k) for k, v in data.items()}
    if isinstance(data, list):
        return [redact(item, key) for item in data]
    if isinstance(data, str) and data and key not in SAFE_STRING_KEYS:
        return data if _HARMLESS_STRING.match(data.strip()) else REDACTED
    return data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GeocoverConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    last_exception = coordinator.last_exception
    return {
        "entry": {
            "version": entry.version,
            "minor_version": entry.minor_version,
            "data": redact(dict(entry.data)),
        },
        "library": {"pygeocover": pygeocover.__version__},
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": type(last_exception).__name__ if last_exception else None,
            "update_interval": str(coordinator.update_interval),
        },
        "bikes": {
            bike_id: {
                "bike": redact(data.bike.raw),
                "state": redact(asdict(data.state)) if data.state else None,
                "health": redact(data.health.raw) if data.health else None,
                "ride_count": data.ride_count,
                "latest_ride": redact(asdict(data.latest_ride))
                if data.latest_ride
                else None,
            }
            for bike_id, data in coordinator.data.items()
        },
    }
