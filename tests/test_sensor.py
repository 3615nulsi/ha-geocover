"""Tests for the Geocover sensors."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .conftest import SetupIntegration


async def test_sensors(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """Sensor values come from the bike, its state, health and latest ride."""
    await setup_integration()

    numeric = {
        "sensor.velo_test_battery": 65,
        "sensor.velo_test_odometer": 5969.8,
        "sensor.velo_test_range": 76,
        "sensor.velo_test_speed": 0,
        "sensor.velo_test_gps_tracker_battery": 99,
        "sensor.velo_test_last_ride_distance": 7.37,
        "sensor.velo_test_last_ride_average_speed": 19,
        "sensor.velo_test_last_ride_elevation_gain": 245,
    }
    for entity_id, value in numeric.items():
        assert float(hass.states.get(entity_id).state) == value, entity_id

    timestamps = {
        "sensor.velo_test_last_position_update": "2026-09-28T16:37:45+00:00",
        "sensor.velo_test_last_connection": "2026-09-28T16:38:00+00:00",
        "sensor.velo_test_last_ride": "2026-09-28T16:13:36+00:00",
    }
    for entity_id, value in timestamps.items():
        assert hass.states.get(entity_id).state == value, entity_id

    duration = hass.states.get("sensor.velo_test_last_ride_duration")
    assert float(duration.state) == 24
    assert duration.attributes["unit_of_measurement"] == "min"
