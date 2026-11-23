"""Data update coordinator: one update cycle for all the bikes of the account."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from pygeocover import (
    Bike,
    BikeState,
    GeocoverApiError,
    GeocoverAuthError,
    GeocoverClient,
    GeocoverConnectionError,
    GeocoverError,
    GeocoverResponseError,
    Health,
    Ride,
)

from .const import DOMAIN, LOGGER, UPDATE_INTERVAL

type GeocoverConfigEntry = ConfigEntry[GeocoverCoordinator]

# Health (tracker battery, last connection) changes slowly.
HEALTH_REFRESH: Final = timedelta(hours=1)
# The latest ride only changes when a ride ends; this is a safety net.
RIDE_REFRESH: Final = timedelta(hours=1)

# Errors of a complementary request that must not fail the whole update.
_OPTIONAL_ERRORS = (GeocoverApiError, GeocoverConnectionError, GeocoverResponseError)


class _Failed:
    """Marker of a complementary request that failed."""


_FAILED: Final = _Failed()


@dataclass(frozen=True, slots=True)
class BikeData:
    """Everything known about one bike after an update cycle."""

    bike: Bike
    state: BikeState | None
    health: Health | None
    latest_ride: Ride | None


class GeocoverCoordinator(DataUpdateCoordinator[dict[int, BikeData]]):
    """Fetch the bikes (position, battery, odometer), then their complementary data.

    Requests per bike and cycle: the bike list (shared) and its state; health and
    latest ride only when they may have changed (see `_async_bike_data`).
    """

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
            always_update=False,
        )
        self.client = client
        self._health_fetched: dict[int, datetime] = {}
        self._ride_fetched: dict[int, datetime] = {}
        # (bike id, data name) of complementary data currently failing
        self._failing: set[tuple[int, str]] = set()

    async def _async_update_data(self) -> dict[int, BikeData]:
        """Fetch data for every bike of the account."""
        try:
            bikes = await self.client.async_get_bikes()
            # Bikes one after the other, to spare the API.
            return {bike.id: await self._async_bike_data(bike) for bike in bikes}
        except GeocoverAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="auth_failed"
            ) from err
        except GeocoverError as err:
            retry_after = err.retry_after if isinstance(err, GeocoverApiError) else None
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
                retry_after=retry_after,
            ) from err

    async def _async_bike_data(self, bike: Bike) -> BikeData:
        """Fetch the complementary data of one bike.

        The state (charging, range) is fetched on every cycle. Health and the latest
        ride are fetched again only when they may have changed. When a request fails,
        the last known value is kept: the position and battery level, which come with
        the bike itself, are never lost because of it.
        """
        previous = self.data.get(bike.id) if self.data else None
        now = dt_util.utcnow()

        fetch_health = previous is None or _is_due(
            self._health_fetched.get(bike.id), now, HEALTH_REFRESH
        )
        fetch_ride = previous is None or _is_due(
            self._ride_fetched.get(bike.id), now, RIDE_REFRESH
        )
        if previous is not None and not bike.ride_in_progress:
            ride_ended = previous.bike.ride_in_progress
            moved = previous.bike.odometer_m != bike.odometer_m
            fetch_ride = fetch_ride or ride_ended or moved

        state, health, ride = await asyncio.gather(
            self._optional(bike, "state", self.client.async_get_state(bike.id)),
            self._optional(bike, "health", self.client.async_get_health(bike.id))
            if fetch_health
            else _none(),
            self._optional(
                bike, "latest_ride", self.client.async_get_latest_ride(bike.id)
            )
            if fetch_ride
            else _none(),
        )

        if not isinstance(health, _Failed) and fetch_health:
            self._health_fetched[bike.id] = now
        if not isinstance(ride, _Failed) and fetch_ride:
            self._ride_fetched[bike.id] = now

        return BikeData(
            bike=bike,
            state=_pick(state, previous.state if previous else None),
            health=_pick(health, previous.health if previous else None, fetch_health),
            latest_ride=_pick(
                ride, previous.latest_ride if previous else None, fetch_ride
            ),
        )

    async def _optional[T](
        self, bike: Bike, name: str, call: Awaitable[T]
    ) -> T | _Failed:
        """Await a complementary request; log once when it starts or stops failing."""
        key = (bike.id, name)
        try:
            result = await call
        except _OPTIONAL_ERRORS as err:
            if key not in self._failing:
                self._failing.add(key)
                LOGGER.info(
                    "%s of bike %s is unavailable, keeping the last known value: %s",
                    name,
                    bike.id,
                    err,
                )
            return _FAILED
        if key in self._failing:
            self._failing.discard(key)
            LOGGER.info("%s of bike %s is available again", name, bike.id)
        return result


def _is_due(last: datetime | None, now: datetime, interval: timedelta) -> bool:
    """Return True if data fetched at `last` should be fetched again."""
    return last is None or now - last >= interval


async def _none() -> None:
    """Stand in for a request that is not needed in this cycle."""
    return


def _pick[T](
    result: T | _Failed | None, previous: T | None, fetched: bool = True
) -> T | None:
    """Return the fresh value, or the previous one if not fetched or if it failed."""
    if not fetched or isinstance(result, _Failed):
        return previous
    return result
