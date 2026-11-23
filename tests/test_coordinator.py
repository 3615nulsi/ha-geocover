"""Tests for the data update coordinator."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from .conftest import SetupIntegration


async def test_api_error_retries_setup(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """A server error on the bike list makes the setup retry later."""
    entry = await setup_integration(errors={"bike": 500})
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_complementary_data_error_keeps_position(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """An error on state, health or latest ride does not hide position and battery."""
    entry = await setup_integration(
        errors={"bike/1/state": 500, "bike/1/health": 500, "v2/bike/1/ride": 500}
    )
    assert entry.state is ConfigEntryState.LOADED

    assert hass.states.get("device_tracker.velo_test").attributes["latitude"] == 48.85
    assert hass.states.get("sensor.velo_test_battery").state == "65"
    assert hass.states.get("sensor.velo_test_range").state == STATE_UNKNOWN
    assert hass.states.get("binary_sensor.velo_test_charging").state == STATE_UNKNOWN
    assert hass.states.get("sensor.velo_test_last_ride").state == STATE_UNKNOWN
