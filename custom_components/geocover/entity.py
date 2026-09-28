"""Entité de base : une entité par vélo, rattachée à l'appareil « vélo »."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BikeData, GeocoverCoordinator


class GeocoverEntity(CoordinatorEntity[GeocoverCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: GeocoverCoordinator, bike_id: int, key: str) -> None:
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
        return self.coordinator.data[self.bike_id]

    @property
    def available(self) -> bool:
        return super().available and self.bike_id in self.coordinator.data
