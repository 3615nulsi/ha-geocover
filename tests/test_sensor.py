"""Tests for the Geocover sensors."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.const import STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import snapshot_platform
from syrupy.assertion import SnapshotAssertion

from .conftest import SetupIntegration, load_fixture


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


async def test_missing_location_and_unset_dates(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """Without GPS fix, position sensors are unknown; 1970 means "not set"."""
    bikes = load_fixture("bikes")
    bikes[0]["last_location"] = None
    health = load_fixture("health")
    health[0]["value"] = "1970-01-01T00:00:00+0000"
    await setup_integration(payloads={"bike": bikes, "bike/1/health": health})

    for entity_id in (
        "sensor.velo_test_speed",
        "sensor.velo_test_last_position_update",
        "sensor.velo_test_last_connection",
    ):
        assert hass.states.get(entity_id).state == STATE_UNKNOWN, entity_id
    assert hass.states.get("binary_sensor.velo_test_moving").state == STATE_UNKNOWN
    assert "latitude" not in hass.states.get("device_tracker.velo_test").attributes


async def test_no_ride_yet(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """A bike without any recorded ride has unknown ride sensors."""
    await setup_integration(
        payloads={
            "v2/bike/1/ride": {
                "meta": {"limit": 1, "offset": 0, "total_records": 0},
                "data": [],
            },
            "bike/1/state": [],
        }
    )
    assert hass.states.get("sensor.velo_test_last_ride").state == STATE_UNKNOWN
    assert hass.states.get("sensor.velo_test_range").state == STATE_UNKNOWN


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.latest_ha_only
async def test_snapshot(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """All the sensors, with their registry entries and states."""
    with patch("custom_components.geocover.PLATFORMS", [Platform.SENSOR]):
        entry = await setup_integration()
    await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)
