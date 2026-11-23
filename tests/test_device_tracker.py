"""Tests for the Geocover device tracker."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import snapshot_platform
from syrupy.assertion import SnapshotAssertion

from .conftest import SetupIntegration


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
