"""Base entity: entities are attached to one device per bike."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BikeData, GeocoverCoordinator


class GeocoverEntity(CoordinatorEntity[GeocoverCoordinator]):
    """Common base for all Geocover entities."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: GeocoverCoordinator, bike_id: int, key: str
    ) -> None:
        """Initialize the entity and its device info."""
        super().__init__(coordinator)
        self.bike_id = bike_id
        bike = coordinator.data[bike_id].bike
        self._attr_unique_id = f"{bike_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(bike_id))},
            name=bike.name,
            manufacturer="Decathlon",
            model=bike.name,
            serial_number=bike.frame_number,
        )

    @property
    def bike_data(self) -> BikeData:
        """Return the latest data of this entity's bike."""
        return self.coordinator.data[self.bike_id]

    @property
    def available(self) -> bool:
        """Return True if the bike is still part of the latest update."""
        return super().available and self.bike_id in self.coordinator.data
