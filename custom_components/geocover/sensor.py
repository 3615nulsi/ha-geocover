"""Sensors: battery, range, odometer, last position and latest ride."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from pygeocover import Location

from .coordinator import BikeData, GeocoverConfigEntry, GeocoverCoordinator
from .entity import GeocoverEntity

PARALLEL_UPDATES = 0

# Sensor values: numbers, or a datetime for timestamp sensors.
type GeocoverValue = StateType | datetime


@dataclass(frozen=True, kw_only=True)
class GeocoverSensorDescription(SensorEntityDescription):
    """Describe a Geocover sensor."""

    value_fn: Callable[[BikeData], GeocoverValue]


def _loc(d: BikeData) -> Location | None:
    """Return the last GPS fix of the bike, if any."""
    return d.bike.last_location


SENSORS: tuple[GeocoverSensorDescription, ...] = (
    GeocoverSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.bike.battery_percentage,
    ),
    GeocoverSensorDescription(
        key="range",
        translation_key="range",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.state.range_km if d.state else None,
    ),
    GeocoverSensorDescription(
        key="odometer",
        translation_key="odometer",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda d: d.bike.odometer_km,
    ),
    GeocoverSensorDescription(
        key="speed",
        translation_key="speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: loc.speed if (loc := _loc(d)) else None,
    ),
    GeocoverSensorDescription(
        key="last_position",
        translation_key="last_position",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: loc.date if (loc := _loc(d)) else None,
    ),
    GeocoverSensorDescription(
        key="last_connection",
        translation_key="last_connection",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.health.last_connection if d.health else None,
    ),
    GeocoverSensorDescription(
        key="tracker_battery",
        translation_key="tracker_battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.health.gps_battery if d.health else None,
    ),
    GeocoverSensorDescription(
        key="last_ride_start",
        translation_key="last_ride_start",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.latest_ride.start_date if d.latest_ride else None,
    ),
    GeocoverSensorDescription(
        key="last_ride_distance",
        translation_key="last_ride_distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        value_fn=lambda d: d.latest_ride.distance_km if d.latest_ride else None,
    ),
    GeocoverSensorDescription(
        key="last_ride_duration",
        translation_key="last_ride_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=0,
        value_fn=lambda d: d.latest_ride.active_time_s if d.latest_ride else None,
    ),
    GeocoverSensorDescription(
        key="last_ride_avg_speed",
        translation_key="last_ride_avg_speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        value_fn=lambda d: d.latest_ride.avg_speed if d.latest_ride else None,
    ),
    GeocoverSensorDescription(
        key="last_ride_elevation_gain",
        translation_key="last_ride_elevation_gain",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        value_fn=lambda d: d.latest_ride.elevation_up if d.latest_ride else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GeocoverConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors of every bike."""
    coordinator = entry.runtime_data
    async_add_entities(
        GeocoverSensor(coordinator, bike_id, description)
        for bike_id in coordinator.data
        for description in SENSORS
    )


class GeocoverSensor(GeocoverEntity, SensorEntity):
    """A sensor of a Geocover bike."""

    entity_description: GeocoverSensorDescription

    def __init__(
        self,
        coordinator: GeocoverCoordinator,
        bike_id: int,
        description: GeocoverSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, bike_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> GeocoverValue:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.bike_data)
