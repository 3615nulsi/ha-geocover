"""Position GPS du vélo."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GeocoverConfigEntry
from .entity import GeocoverEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GeocoverConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(GeocoverTracker(coordinator, bike_id) for bike_id in coordinator.data)


class GeocoverTracker(GeocoverEntity, TrackerEntity):
    _attr_name = None  # prend le nom du vélo
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator, bike_id: int) -> None:
        super().__init__(coordinator, bike_id, "location")

    @property
    def latitude(self) -> float | None:
        loc = self.bike_data.bike.last_location
        return loc.lat if loc else None

    @property
    def longitude(self) -> float | None:
        loc = self.bike_data.bike.last_location
        return loc.lon if loc else None
