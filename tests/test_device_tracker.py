"""Tests for the Geocover device tracker."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

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
