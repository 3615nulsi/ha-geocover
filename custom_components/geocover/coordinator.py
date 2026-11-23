"""Data update coordinator: one update cycle for all the bikes of the account."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
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
    RidePage,
)

from .const import (
    DOMAIN,
    IDLE_AFTER,
    IDLE_INTERVAL,
    LOGGER,
    RIDING_INTERVAL,
    UPDATE_INTERVAL,
)
from .issues import async_delete_bike_issues, async_update_issues

type GeocoverConfigEntry = ConfigEntry[GeocoverCoordinator]


def manufacturer(bike: Bike) -> str:
    """Return the display name of the bike's manufacturer."""
    return (bike.manufacturer or "decathlon").title()


# Health (tracker battery, last connection) changes slowly.
HEALTH_REFRESH: Final = timedelta(hours=1)
# The latest ride only changes when a ride ends; this is a safety net.
RIDE_REFRESH: Final = timedelta(hours=1)

# A GPS fix older than this does not tell whether the bike is moving now.
RECENT_FIX: Final = timedelta(minutes=10)

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
    # latest ride and number of rides; None if never fetched successfully
    rides: RidePage | None

    @property
    def latest_ride(self) -> Ride | None:
        """Return the latest recorded ride, if any."""
        return self.rides.rides[0] if self.rides and self.rides.rides else None

    @property
    def ride_count(self) -> int | None:
        """Return the number of rides recorded for the bike."""
        return self.rides.total if self.rides else None


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
        # shared bikes skipped because another account provides them
        self._skipped_shared: set[int] = set()

    async def _async_update_data(self) -> dict[int, BikeData]:
        """Fetch data for every bike of the account."""
        try:
            bikes = self._without_shared_duplicates(await self.client.async_get_bikes())
            # Bikes one after the other, to spare the API.
            data = {bike.id: await self._async_bike_data(bike) for bike in bikes}
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
        self._async_sync_devices(data)
        async_update_issues(self.hass, data)
        self._adapt_update_interval(data)
        return data

    def _adapt_update_interval(self, data: dict[int, BikeData]) -> None:
        """Poll often while a bike is ridden, rarely when all bikes sleep.

        - a ride is in progress or a bike moves: every minute;
        - a bike is charging or powered on, or moved recently: every 5 minutes;
        - every bike has been still for a few hours: every 15 minutes.
        """
        interval = interval_for(data, dt_util.utcnow())
        if interval != self.update_interval:
            LOGGER.debug("Polling every %s from now on", interval)
            self.update_interval = interval

    def _without_shared_duplicates(self, bikes: list[Bike]) -> list[Bike]:
        """Drop the shared bikes that another configured account already provides.

        A bike shared with several accounts is returned to each of them; the same
        entities created twice would clash. The owner's account keeps the bike.
        """
        provided_elsewhere: set[int] = set()
        for entry in self.hass.config_entries.async_loaded_entries(DOMAIN):
            if entry.entry_id != self.config_entry.entry_id and entry.runtime_data.data:
                provided_elsewhere.update(entry.runtime_data.data)
        kept = []
        for bike in bikes:
            owned = bike.raw.get("is_requesting_user_owner") is not False
            if not owned and bike.id in provided_elsewhere:
                if bike.id not in self._skipped_shared:
                    self._skipped_shared.add(bike.id)
                    LOGGER.info(
                        "Bike %s is shared with another configured account, "
                        "which already provides it: skipped",
                        bike.id,
                    )
                continue
            self._skipped_shared.discard(bike.id)
            kept.append(bike)
        return kept

    @callback
    def _async_sync_devices(self, data: dict[int, BikeData]) -> None:
        """Keep the device registry in line with the bikes of the account.

        Renamed bikes are renamed (unless the user renamed the device), and the
        devices of bikes that left the account are removed.
        """
        registry = dr.async_get(self.hass)
        entry_id = self.config_entry.entry_id
        for device in dr.async_entries_for_config_entry(registry, entry_id):
            bike_id = next(
                (
                    int(ident)
                    for domain, ident in device.identifiers
                    if domain == DOMAIN
                ),
                None,
            )
            if bike_id is None or bike_id not in data:
                LOGGER.info(
                    "Removing the device of bike %s, no longer in the account", bike_id
                )
                registry.async_update_device(device.id, remove_config_entry_id=entry_id)
                if bike_id is not None:
                    async_delete_bike_issues(self.hass, bike_id)
                continue
            bike = data[bike_id].bike
            changes: dict[str, Any] = {
                "name": bike.name,
                "manufacturer": manufacturer(bike),
                # versions < 0.3 stored the bike name as model
                "model": None,
                "model_id": bike.article_number,
            }
            if any(getattr(device, key) != value for key, value in changes.items()):
                registry.async_update_device(device.id, **changes)

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
                bike, "latest_ride", self.client.async_get_rides(bike.id, limit=1)
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
            rides=_pick(ride, previous.rides if previous else None, fetch_ride),
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


def interval_for(data: dict[int, BikeData], now: datetime) -> timedelta:
    """Return the polling interval suited to the bikes' activity (see above)."""
    if not data:
        return UPDATE_INTERVAL
    states = [d.state for d in data.values() if d.state]
    if any(d.bike.ride_in_progress or _moving(d, now) for d in data.values()):
        return RIDING_INTERVAL
    if any(s.charging or s.powered_on for s in states):
        return UPDATE_INTERVAL
    for d in data.values():
        last_seen = d.bike.last_location.date if d.bike.last_location else None
        if last_seen is None or now - last_seen < IDLE_AFTER:
            return UPDATE_INTERVAL
    return IDLE_INTERVAL


def _moving(data: BikeData, now: datetime) -> bool:
    """Return True if the last GPS fix is recent and says the bike moves.

    The bike may stop reporting while parked: an old "moving" fix is not trusted.
    """
    loc = data.bike.last_location
    return bool(loc and loc.is_moving and loc.date and now - loc.date < RECENT_FIX)


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
