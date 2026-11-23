"""Data update coordinator: one update cycle for all the bikes of the account."""

from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pygeocover import (
    Bike,
    BikeState,
    GeocoverApiError,
    GeocoverAuthError,
    GeocoverClient,
    GeocoverError,
    Health,
    Ride,
)

from .const import DOMAIN, LOGGER, UPDATE_INTERVAL

type GeocoverConfigEntry = ConfigEntry[GeocoverCoordinator]


@dataclass
class BikeData:
    """Everything known about one bike after an update cycle."""

    bike: Bike
    state: BikeState | None
    health: Health | None
    latest_ride: Ride | None


class GeocoverCoordinator(DataUpdateCoordinator[dict[int, BikeData]]):
    """Fetch the bikes (position, battery, odometer), then their state, health and latest ride."""

    config_entry: GeocoverConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: GeocoverConfigEntry, client: GeocoverClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[int, BikeData]:
        """Fetch data for every bike of the account."""
        try:
            bikes = await self.client.async_get_bikes()
            return {bike.id: await self._async_bike_data(bike) for bike in bikes}
        except GeocoverAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="auth_failed"
            ) from err
        except GeocoverError as err:
            raise UpdateFailed(
                f"Error communicating with the Geocover API: {err}"
            ) from err

    async def _async_bike_data(self, bike: Bike) -> BikeData:
        """Fetch the complementary data of one bike.

        An API error on one of them must not deprive the user of the position and
        battery level, which come with the bike itself.
        """

        async def optional[T](call: Awaitable[T]) -> T | None:
            try:
                return await call
            except GeocoverApiError as err:
                LOGGER.debug(
                    "Complementary data unavailable for bike %s: %s", bike.id, err
                )
                return None

        return BikeData(
            bike=bike,
            state=await optional(self.client.async_get_state(bike.id)),
            health=await optional(self.client.async_get_health(bike.id)),
            latest_ride=await optional(self.client.async_get_latest_ride(bike.id)),
        )
