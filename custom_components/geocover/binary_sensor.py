"""Binary sensors: moving, charging, powered on, ride in progress."""

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

from .coordinator import BikeData, GeocoverConfigEntry, GeocoverCoordinator
from .entity import GeocoverEntity, async_setup_bike_entities

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class GeocoverBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Geocover binary sensor."""

    value_fn: Callable[[BikeData], bool | None]


BINARY_SENSORS: tuple[GeocoverBinarySensorDescription, ...] = (
    GeocoverBinarySensorDescription(
        key="moving",
        device_class=BinarySensorDeviceClass.MOVING,
        value_fn=lambda d: (
            d.bike.last_location.is_moving if d.bike.last_location else None
        ),
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
    """Set up the binary sensors of every bike."""
    async_setup_bike_entities(
        entry,
        async_add_entities,
        lambda coordinator, bike_id: (
            GeocoverBinarySensor(coordinator, bike_id, description)
            for description in BINARY_SENSORS
        ),
    )


class GeocoverBinarySensor(GeocoverEntity, BinarySensorEntity):
    """A binary sensor of a Geocover bike."""

    entity_description: GeocoverBinarySensorDescription

    def __init__(
        self,
        coordinator: GeocoverCoordinator,
        bike_id: int,
        description: GeocoverBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, bike_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        return self.entity_description.value_fn(self.bike_data)
