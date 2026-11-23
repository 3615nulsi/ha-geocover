"""Diagnostics support, with sensitive data redacted."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_TOKENS
from .coordinator import GeocoverConfigEntry

TO_REDACT = {
    CONF_TOKENS,
    "access_token",
    "refresh_token",
    "lat",
    "lon",
    "center",
    "imei",
    "email",
    "user_name",
    "username",
    "name",
    "frame_number",
    "activation_code",
    "blepass",
    "blename",
    "invite_code",
    "invite_code_uri",
    "owning_user",
    "linked_users",
    "conneqtech_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GeocoverConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "bikes": {
            bike_id: async_redact_data(
                {
                    "bike": data.bike.raw,
                    "state": asdict(data.state) if data.state else None,
                    "health": data.health.raw if data.health else None,
                    "latest_ride": asdict(data.latest_ride)
                    if data.latest_ride
                    else None,
                },
                TO_REDACT,
            )
            for bike_id, data in coordinator.data.items()
        },
    }
