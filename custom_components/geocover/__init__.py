"""The Geocover (Decathlon connected e-bikes) integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pygeocover import GeocoverClient, TokenSet

from .const import CONF_TOKENS
from .coordinator import GeocoverConfigEntry, GeocoverCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: GeocoverConfigEntry) -> bool:
    """Set up Geocover from a config entry."""

    @callback
    def save_tokens(tokens: TokenSet) -> None:
        # The refresh token is rotating and single-use: it MUST be persisted on
        # every refresh, otherwise the next restart would require a new sign-in.
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_TOKENS: tokens.to_dict()}
        )

    client = GeocoverClient(
        async_get_clientsession(hass),
        TokenSet.from_dict(entry.data[CONF_TOKENS]),
        on_tokens_updated=save_tokens,
    )
    coordinator = GeocoverCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GeocoverConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
