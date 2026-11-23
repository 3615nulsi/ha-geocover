"""GPS position of the bike."""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GeocoverConfigEntry, GeocoverCoordinator
from .entity import GeocoverEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GeocoverConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one tracker per bike."""
    coordinator = entry.runtime_data
    async_add_entities(
        GeocoverTracker(coordinator, bike_id) for bike_id in coordinator.data
    )


class GeocoverTracker(GeocoverEntity, TrackerEntity):
    """Last GPS position reported by the bike."""

    _attr_name = None  # use the device (bike) name
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: GeocoverCoordinator, bike_id: int) -> None:
        """Initialize the tracker."""
        super().__init__(coordinator, bike_id, "location")

    @property
    def latitude(self) -> float | None:
        """Return the latitude of the last GPS fix."""
        loc = self.bike_data.bike.last_location
        return loc.lat if loc else None

    @property
    def longitude(self) -> float | None:
        """Return the longitude of the last GPS fix."""
        loc = self.bike_data.bike.last_location
        return loc.lon if loc else None
