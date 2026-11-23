"""Event fired when a ride is finished: a natural trigger for automations."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BikeData, GeocoverConfigEntry, GeocoverCoordinator
from .entity import GeocoverEntity, async_setup_bike_entities
from .rides import ride_summary

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
