"""Tests for the Geocover binary sensors."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.const import STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import snapshot_platform
from syrupy.assertion import SnapshotAssertion

from .conftest import SetupIntegration


async def test_binary_sensors(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """Binary sensor values come from the bike and its state."""
    await setup_integration()

    assert hass.states.get("binary_sensor.velo_test_charging").state == STATE_ON
    assert hass.states.get("binary_sensor.velo_test_moving").state == STATE_OFF
    assert hass.states.get("binary_sensor.velo_test_powered_on").state == STATE_OFF
    assert (
        hass.states.get("binary_sensor.velo_test_ride_in_progress").state == STATE_OFF
    )


@pytest.mark.latest_ha_only
async def test_snapshot(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """All the entities of the platform, with their registry entries and states."""
    with patch("custom_components.geocover.PLATFORMS", [Platform.BINARY_SENSOR]):
        entry = await setup_integration()
    await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)
