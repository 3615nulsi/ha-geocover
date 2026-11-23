"""Base entity: entities are attached to one device per bike."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pygeocover import Bike

from .const import DOMAIN
from .coordinator import (
    BikeData,
    GeocoverConfigEntry,
    GeocoverCoordinator,
    manufacturer,
)


def device_info(bike: Bike) -> DeviceInfo:
    """Return the device info of a bike.

    The API has no model name: `article_number` is the product reference.
    """
    return DeviceInfo(
        identifiers={(DOMAIN, str(bike.id))},
        name=bike.name,
        manufacturer=manufacturer(bike),
        model_id=bike.article_number,
        serial_number=bike.frame_number,
    )


@callback
def async_setup_bike_entities(
    entry: GeocoverConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    entities_for_bike: Callable[[GeocoverCoordinator, int], Iterable[Entity]],
) -> None:
    """Add the entities of every bike, now and when a bike appears later."""
    coordinator = entry.runtime_data
    known: set[int] = set()

    @callback
    def _add_new_bikes() -> None:
        new = [bike_id for bike_id in coordinator.data if bike_id not in known]
        if not new:
            return
        known.update(new)
        async_add_entities(
            entity
            for bike_id in new
            for entity in entities_for_bike(coordinator, bike_id)
        )

    _add_new_bikes()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_bikes))


class GeocoverEntity(CoordinatorEntity[GeocoverCoordinator]):
    """Common base for all Geocover entities."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: GeocoverCoordinator, bike_id: int, key: str
    ) -> None:
        """Initialize the entity and its device info."""
        super().__init__(coordinator)
        self.bike_id = bike_id
        self._attr_unique_id = f"{bike_id}_{key}"
        self._attr_device_info = device_info(coordinator.data[bike_id].bike)

    @property
    def bike_data(self) -> BikeData:
        """Return the latest data of this entity's bike."""
        return self.coordinator.data[self.bike_id]

    @property
    def available(self) -> bool:
        """Return True if the bike is still part of the latest update."""
        return super().available and self.bike_id in self.coordinator.data
