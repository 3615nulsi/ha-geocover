"""Intégration Home Assistant pour les vélos Decathlon connectés (Geocover)."""
from __future__ import annotations

from pygeocover import GeocoverClient, TokenSet

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_TOKENS
from .coordinator import GeocoverConfigEntry, GeocoverCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: GeocoverConfigEntry) -> bool:
    @callback
    def save_tokens(tokens: TokenSet) -> None:
        # refresh_token rotatif à usage unique : le persister à CHAQUE rafraîchissement
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
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
