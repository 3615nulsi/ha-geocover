"""Coordinateur : un cycle de mise à jour pour tous les vélos du compte."""
from __future__ import annotations

from dataclasses import dataclass

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

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER, UPDATE_INTERVAL

type GeocoverConfigEntry = ConfigEntry[GeocoverCoordinator]


@dataclass
class BikeData:
    bike: Bike
    state: BikeState | None
    health: Health | None
    latest_ride: Ride | None


class GeocoverCoordinator(DataUpdateCoordinator[dict[int, BikeData]]):
    """Par cycle : `GET bike` (position, batterie, odomètre) + état, santé et dernier trajet."""

    config_entry: GeocoverConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: GeocoverConfigEntry, client: GeocoverClient
    ) -> None:
        super().__init__(
            hass, LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL
        )
        self.client = client

    async def _async_update_data(self) -> dict[int, BikeData]:
        try:
            bikes = await self.client.async_get_bikes()
            return {bike.id: await self._async_bike_data(bike) for bike in bikes}
        except GeocoverAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="auth_failed"
            ) from err
        except GeocoverError as err:
            raise UpdateFailed(f"Erreur de l'API Geocover : {err}") from err

    async def _async_bike_data(self, bike: Bike) -> BikeData:
        # données complémentaires : une erreur de l'API sur l'une d'elles ne doit pas
        # priver l'utilisateur de la position et de la batterie
        async def optional(coro):
            try:
                return await coro
            except GeocoverApiError as err:
                LOGGER.debug("Donnée complémentaire indisponible pour %s : %s", bike.id, err)
                return None

        return BikeData(
            bike=bike,
            state=await optional(self.client.async_get_state(bike.id)),
            health=await optional(self.client.async_get_health(bike.id)),
            latest_ride=await optional(self.client.async_get_latest_ride(bike.id)),
        )
