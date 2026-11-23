"""Event fired when a ride is finished: a natural trigger for automations."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from pygeocover import Ride

from .coordinator import BikeData, GeocoverConfigEntry, GeocoverCoordinator
from .entity import GeocoverEntity, async_setup_bike_entities

PARALLEL_UPDATES = 0

RIDE_FINISHED = "ride_finished"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GeocoverConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one ride event entity per bike."""
    async_setup_bike_entities(
        entry,
        async_add_entities,
        lambda coordinator, bike_id: [GeocoverRideEvent(coordinator, bike_id)],
    )


def ride_summary(ride: Ride) -> dict[str, Any]:
    """Return the attributes of a ride finished event."""
    return {
        "ride_id": ride.id,
        "start": ride.start_date.isoformat() if ride.start_date else None,
        "end": ride.end_date.isoformat() if ride.end_date else None,
        "distance_km": ride.distance_km,
        "duration_min": round(ride.active_time_s / 60)
        if ride.active_time_s is not None
        else None,
        "average_speed_kmh": ride.avg_speed,
        "elevation_gain_m": ride.elevation_up,
        "elevation_loss_m": ride.elevation_down,
        "calories_kcal": ride.calories,
        "co2_saved_g": ride.co2,
    }


class GeocoverRideEvent(GeocoverEntity, EventEntity):
    """Fired once per new ride, when the ride is over."""

    _attr_translation_key = "ride"

    def __init__(self, coordinator: GeocoverCoordinator, bike_id: int) -> None:
        """Initialize the event entity; the current latest ride is not an event."""
        super().__init__(coordinator, bike_id, "ride")
        self._attr_event_types = [RIDE_FINISHED]
        self._last_ride_id: int | None = None
        self._baseline_known = False
        self._update_baseline(coordinator.data[bike_id])

    def _update_baseline(self, data: BikeData) -> None:
        if data.rides is not None:
            ride = data.latest_ride
            self._last_ride_id = ride.id if ride else None
            self._baseline_known = True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fire the event when a new finished ride shows up."""
        data = self.coordinator.data.get(self.bike_id)
        if data is not None and data.rides is not None:
            ride = data.latest_ride
            if not self._baseline_known:
                # the rides could not be fetched so far: nothing to compare with
                self._update_baseline(data)
            elif (
                ride is not None
                and ride.id != self._last_ride_id
                # an unfinished ride may already be listed: wait for its end
                and not data.bike.ride_in_progress
                and ride.end_date is not None
            ):
                self._last_ride_id = ride.id
                self._trigger_event(RIDE_FINISHED, ride_summary(ride))
        super()._handle_coordinator_update()
