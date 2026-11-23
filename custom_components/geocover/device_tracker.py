"""GPS position of the bike."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.location import distance
from pygeocover import Geofence, Location

from .coordinator import GeocoverConfigEntry, GeocoverCoordinator
from .entity import GeocoverEntity, async_setup_bike_entities

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GeocoverConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one tracker per bike."""
    async_setup_bike_entities(
        entry,
        async_add_entities,
        lambda coordinator, bike_id: [GeocoverTracker(coordinator, bike_id)],
    )


class GeocoverTracker(GeocoverEntity, TrackerEntity):
    """Last GPS position reported by the bike."""

    _attr_name = None  # use the device (bike) name
    _attr_source_type = SourceType.GPS
    _attr_translation_key = "location"

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

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the bike, shown on the map."""
        return self.bike_data.bike.battery_percentage

    @property
    def entity_picture(self) -> str | None:
        """Return the photo of the bike model provided by the app."""
        data = self.coordinator.data.get(self.bike_id)
        return data.bike.image_url if data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return when the position was reported, and the app's geofences.

        `geofences` lists the active geofences defined in the Geocover app,
        `in_geofences` those the bike is in.
        """
        bike = self.bike_data.bike
        loc = bike.last_location
        active = [g for g in bike.geofences if g.active]
        return {
            "last_position_update": loc.date if loc and loc.date else None,
            "geofences": [g.name for g in active],
            "in_geofences": [g.name for g in active if _inside(g, loc)],
        }


def _inside(geofence: Geofence, loc: Location | None) -> bool:
    """Return True if the position is within the geofence."""
    if loc is None or loc.lat is None or loc.lon is None:
        return False
    lat, lon, radius = geofence.lat, geofence.lon, geofence.radius
    if lat is None or lon is None or radius is None:
        return False
    meters = distance(loc.lat, loc.lon, lat, lon)
    return meters is not None and meters <= radius
