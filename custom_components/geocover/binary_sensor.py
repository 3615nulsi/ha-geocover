"""Capteurs binaires : en mouvement, en charge, allumé, trajet en cours."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BikeData, GeocoverConfigEntry
from .entity import GeocoverEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class GeocoverBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[BikeData], bool | None]


BINARY_SENSORS: tuple[GeocoverBinarySensorDescription, ...] = (
    GeocoverBinarySensorDescription(
        key="moving",
        device_class=BinarySensorDeviceClass.MOVING,
        value_fn=lambda d: d.bike.last_location.is_moving if d.bike.last_location else None,
    ),
    GeocoverBinarySensorDescription(
        key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda d: d.state.charging if d.state else None,
    ),
    GeocoverBinarySensorDescription(
        key="powered_on",
        translation_key="powered_on",
        device_class=BinarySensorDeviceClass.POWER,
        value_fn=lambda d: d.state.powered_on if d.state else None,
    ),
    GeocoverBinarySensorDescription(
        key="ride_in_progress",
        translation_key="ride_in_progress",
        value_fn=lambda d: d.bike.ride_in_progress,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GeocoverConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        GeocoverBinarySensor(coordinator, bike_id, description)
        for bike_id in coordinator.data
        for description in BINARY_SENSORS
    )


class GeocoverBinarySensor(GeocoverEntity, BinarySensorEntity):
    entity_description: GeocoverBinarySensorDescription

    def __init__(
        self, coordinator, bike_id: int, description: GeocoverBinarySensorDescription
    ) -> None:
        super().__init__(coordinator, bike_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.bike_data)
