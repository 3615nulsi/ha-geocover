"""Long-term statistics of the rides, imported from the ride history.

Hourly sums of the distance ridden and of the number of rides, for every bike,
including the rides recorded before the integration was installed. They feed the
statistics graph and statistic cards over months.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from pygeocover import GeocoverError, Ride

from .const import DOMAIN, LOGGER
from .coordinator import GeocoverConfigEntry, GeocoverCoordinator


def statistic_id(bike_id: int, kind: str) -> str:
    """Return the id of a statistic of a bike (e.g. geocover:bike_1_distance)."""
    return f"{DOMAIN}:bike_{bike_id}_{kind}"


def hourly_sums(rides: list[Ride]) -> dict[str, list[StatisticData]]:
    """Return the cumulated distance and number of rides, per hour of ride start."""
    distance: dict[datetime, float] = defaultdict(float)
    count: dict[datetime, int] = defaultdict(int)
    for ride in rides:
        if ride.start_date is None:
            continue
        hour = ride.start_date.replace(minute=0, second=0, microsecond=0)
        distance[hour] += ride.distance_km or 0
        count[hour] += 1

    result: dict[str, list[StatisticData]] = {"distance": [], "rides": []}
    total_distance = 0.0
    total_count = 0
    for hour in sorted(distance):
        total_distance += distance[hour]
        total_count += count[hour]
        result["distance"].append(
            StatisticData(
                start=hour, state=distance[hour], sum=round(total_distance, 3)
            )
        )
        result["rides"].append(
            StatisticData(start=hour, state=count[hour], sum=total_count)
        )
    return result


async def async_import_statistics(
    hass: HomeAssistant, coordinator: GeocoverCoordinator, bike_id: int
) -> None:
    """Fetch the ride history of a bike and import its statistics."""
    data = coordinator.data.get(bike_id)
    if data is None:
        return
    try:
        rides = await coordinator.ride_history(bike_id).async_update(data.ride_count)
    except GeocoverError as err:
        LOGGER.info("Ride statistics of bike %s not updated: %s", bike_id, err)
        return
    sums = hourly_sums(rides)
    name = data.bike.name
    for kind, unit, unit_class, label in (
        ("distance", UnitOfLength.KILOMETERS, "distance", "ride distance"),
        ("rides", None, None, "rides"),
    ):
        if not sums[kind]:
            continue
        metadata = StatisticMetaData(
            has_mean=False,
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=f"{name} {label}",
            source=DOMAIN,
            statistic_id=statistic_id(bike_id, kind),
            unit_class=unit_class,
            unit_of_measurement=unit,
        )
        async_add_external_statistics(hass, metadata, sums[kind])


@callback
def async_setup_statistics(hass: HomeAssistant, entry: GeocoverConfigEntry) -> None:
    """Import the statistics now, then again whenever new rides are recorded."""
    if "recorder" not in hass.config.components:
        return
    coordinator = entry.runtime_data
    imported: dict[int, int | None] = {}

    @callback
    def _schedule() -> None:
        for bike_id, data in coordinator.data.items():
            if bike_id in imported and imported[bike_id] == data.ride_count:
                continue
            if data.rides is None:
                continue  # rides unknown for now: wait for a successful fetch
            imported[bike_id] = data.ride_count
            entry.async_create_background_task(
                hass,
                async_import_statistics(hass, coordinator, bike_id),
                f"{DOMAIN} statistics of bike {bike_id}",
            )

    _schedule()
    entry.async_on_unload(coordinator.async_add_listener(_schedule))
