"""Tests for the Geocover device tracker."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pygeocover import Geofence, Location
import pytest
from pytest_homeassistant_custom_component.common import snapshot_platform
from syrupy.assertion import SnapshotAssertion

from custom_components.geocover.device_tracker import _inside

from .conftest import SetupIntegration, bikes_with


async def test_tracker(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """The tracker carries the last GPS fix and takes the bike's name."""
    await setup_integration()

    tracker = hass.states.get("device_tracker.velo_test")
    assert tracker.attributes["latitude"] == 48.85
    assert tracker.attributes["longitude"] == 2.35
    assert tracker.attributes["source_type"] == "gps"
    assert tracker.attributes["friendly_name"] == "Vélo test"
    assert tracker.attributes["battery_level"] == 65
    assert tracker.attributes["entity_picture"] == "https://img.example/bike.jpg"
    assert tracker.attributes["last_position_update"] is not None


@pytest.mark.latest_ha_only
async def test_snapshot(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """All the entities of the platform, with their registry entries and states."""
    with patch("custom_components.geocover.PLATFORMS", [Platform.DEVICE_TRACKER]):
        entry = await setup_integration()
    await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)


async def test_geofences(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """The geofences of the app are listed, with those the bike is in."""
    geofence = {
        "id": 5,
        "name": "Maison",
        "center": {"lat": 48.8501, "lon": 2.3501},
        "radius": 150,
        "active_state": 0,
    }
    far = {**geofence, "id": 6, "name": "Travail", "center": {"lat": 45.0, "lon": 3.0}}
    off = {**geofence, "id": 7, "name": "Ancien", "active_state": 1}
    await setup_integration(
        payloads={"bike": bikes_with(geofences=[geofence, far, off])}
    )
    attributes = hass.states.get("device_tracker.velo_test").attributes
    assert attributes["geofences"] == ["Maison", "Travail"]
    assert attributes["in_geofences"] == ["Maison"]


def test_inside_with_missing_coordinates() -> None:
    """Without coordinates, the bike is in no geofence."""
    geofence = Geofence(id=1, name="x", lat=None, lon=2.0, radius=10, active=True)
    location = Location.from_dict({"lat": 48.0, "lon": 2.0})
    assert not _inside(geofence, location)
    assert not _inside(geofence, Location.from_dict({}))
