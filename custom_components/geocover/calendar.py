"""Calendar of the rides: every recorded ride is an event."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from pygeocover import GeocoverError, Ride

from .const import DOMAIN
from .coordinator import GeocoverConfigEntry, GeocoverCoordinator
from .entity import GeocoverEntity, async_setup_bike_entities

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GeocoverConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one ride calendar per bike."""
    async_setup_bike_entities(
        entry,
        async_add_entities,
        lambda coordinator, bike_id: [GeocoverRideCalendar(coordinator, bike_id)],
    )


def ride_event(ride: Ride) -> CalendarEvent | None:
    """Return the calendar event of a ride, e.g. "7.4 km · 24 min"."""
    if ride.start_date is None:
        return None
    end = ride.end_date or ride.start_date
    if end <= ride.start_date:
        end = ride.start_date + timedelta(minutes=1)
    parts = []
    if ride.distance_km is not None:
        parts.append(f"{ride.distance_km:.1f} km")
    if ride.active_time_s is not None:
        parts.append(f"{round(ride.active_time_s / 60)} min")
    details = []
    if ride.avg_speed is not None:
        details.append(f"⌀ {ride.avg_speed:.1f} km/h")
    if ride.elevation_up is not None:
        details.append(f"↗ {ride.elevation_up} m")
    if ride.elevation_down is not None:
        details.append(f"↘ {ride.elevation_down} m")
    if ride.calories is not None:
        details.append(f"{ride.calories} kcal")
    return CalendarEvent(
        start=ride.start_date,
        end=end,
        summary=" · ".join(parts) or "🚲",
        description=" · ".join(details) or None,
        uid=str(ride.id),
    )


class GeocoverRideCalendar(GeocoverEntity, CalendarEntity):
    """The rides of a bike, read from the Geocover history when displayed."""

    _attr_translation_key = "rides"

    def __init__(self, coordinator: GeocoverCoordinator, bike_id: int) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator, bike_id, "rides")

    @property
    def event(self) -> CalendarEvent | None:
        """Return the latest ride (no request: it comes with every update)."""
        data = self.coordinator.data.get(self.bike_id)
        ride = data.latest_ride if data else None
        return ride_event(ride) if ride else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return the rides of a period (the history is fetched only once)."""
        data = self.coordinator.data.get(self.bike_id)
        history = self.coordinator.ride_history(self.bike_id)
        try:
            rides = await history.async_between(
                start_date, end_date, data.ride_count if data else None
            )
        except GeocoverError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="rides_unavailable",
                translation_placeholders={"error": str(err)},
            ) from err
        return [event for ride in rides if (event := ride_event(ride)) is not None]
