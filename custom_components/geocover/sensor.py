"""Sensors: battery, range, odometer, last position, rides."""

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
    UnitOfMass,
    UnitOfSpeed,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from pygeocover import Location

from .coordinator import BikeData, GeocoverConfigEntry, GeocoverCoordinator
from .entity import GeocoverEntity, async_setup_bike_entities

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


def _speed(d: BikeData) -> float | None:
    """Return the speed of the last GPS fix; 0 when the bike is not moving.

    The last fix may have been sent while riding: its speed must not stay
    displayed once the bike is at rest.
    """
    if (loc := _loc(d)) is None:
        return None
    return loc.speed if loc.is_moving else 0


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
        suggested_display_precision=0,
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
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=_speed,
    ),
    GeocoverSensorDescription(
        key="last_position",
        translation_key="last_position",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        value_fn=lambda d: loc.date if (loc := _loc(d)) else None,
    ),
    GeocoverSensorDescription(
        key="last_connection",
        translation_key="last_connection",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.health.last_connection if d.health else None,
    ),
    GeocoverSensorDescription(
        key="tracker_battery",
        translation_key="tracker_battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
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
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.latest_ride.avg_speed if d.latest_ride else None,
    ),
    GeocoverSensorDescription(
        key="last_ride_elevation_gain",
        translation_key="last_ride_elevation_gain",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.latest_ride.elevation_up if d.latest_ride else None,
    ),
    GeocoverSensorDescription(
        key="ride_count",
        translation_key="ride_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.ride_count,
    ),
    GeocoverSensorDescription(
        key="last_ride_end",
        translation_key="last_ride_end",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.latest_ride.end_date if d.latest_ride else None,
    ),
    GeocoverSensorDescription(
        key="last_ride_elevation_loss",
        translation_key="last_ride_elevation_loss",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.latest_ride.elevation_down if d.latest_ride else None,
    ),
    GeocoverSensorDescription(
        key="last_ride_calories",
        translation_key="last_ride_calories",
        native_unit_of_measurement="kcal",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.latest_ride.calories if d.latest_ride else None,
    ),
    GeocoverSensorDescription(
        # The API does not document the unit; grams match the distances observed
        # (about 250 g per km, the emissions of a car).
        key="last_ride_co2_saved",
        translation_key="last_ride_co2_saved",
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.GRAMS,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.latest_ride.co2 if d.latest_ride else None,
    ),
    GeocoverSensorDescription(
        key="last_full_charge",
        translation_key="last_full_charge",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.state.last_full_charge if d.state else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GeocoverConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors of every bike."""
    async_setup_bike_entities(
        entry,
        async_add_entities,
        lambda coordinator, bike_id: (
            GeocoverSensor(coordinator, bike_id, description) for description in SENSORS
        ),
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
