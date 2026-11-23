"""Tests for the Geocover binary sensors."""

from __future__ import annotations

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

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
