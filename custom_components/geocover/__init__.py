"""The Geocover (Decathlon connected e-bikes) integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pygeocover import GeocoverClient, TokenSet

from .const import CONF_TOKENS, DOMAIN
from .coordinator import GeocoverConfigEntry, GeocoverCoordinator
from .issues import async_delete_bike_issues

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.EVENT,
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


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: GeocoverConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Allow removing a bike's device only once the bike left the account."""
    return not any(
        domain == DOMAIN
        and ident in {str(bike_id) for bike_id in entry.runtime_data.data}
        for domain, ident in device.identifiers
    )


async def async_remove_entry(hass: HomeAssistant, entry: GeocoverConfigEntry) -> None:
    """Delete the repair issues of the bikes of a removed account."""
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        for domain, ident in device.identifiers:
            if domain == DOMAIN and ident.isdigit():
                async_delete_bike_issues(hass, int(ident))
