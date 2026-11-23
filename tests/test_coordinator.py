"""Tests for the data update coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import aiohttp
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.geocover.const import UPDATE_INTERVAL

from .conftest import API, SetupIntegration, api_calls, load_fixture, mock_api

TRACKER = "device_tracker.velo_test"
RANGE = "sensor.velo_test_range"


async def _next_update(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    delta: timedelta = UPDATE_INTERVAL,
) -> None:
    """Move time forward and let the coordinator update."""
    freezer.tick(delta)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _bike(**changes: Any) -> list[dict[str, Any]]:
    """Return the bike list fixture with some fields changed."""
    bikes = load_fixture("bikes")
    bikes[0].update(changes)
    return bikes


async def test_api_error_retries_setup(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """A server error on the bike list makes the setup retry later."""
    entry = await setup_integration(errors={"bike": 500})
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_malformed_bike_list_retries_setup(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """An unexpected answer of the API is an update failure, not a crash."""
    entry = await setup_integration(payloads={"bike": [{"name": "no id"}]})
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_complementary_data_error_at_setup(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """An error on state, health or latest ride does not hide position and battery."""
    entry = await setup_integration(
        errors={"bike/1/state": 500, "bike/1/health": 500, "v2/bike/1/ride": 500}
    )
    assert entry.state is ConfigEntryState.LOADED

    assert hass.states.get(TRACKER).attributes["latitude"] == 48.85
    assert hass.states.get("sensor.velo_test_battery").state == "65"
    assert hass.states.get(RANGE).state == STATE_UNKNOWN
    assert hass.states.get("binary_sensor.velo_test_charging").state == STATE_UNKNOWN
    assert hass.states.get("sensor.velo_test_last_ride").state == STATE_UNKNOWN


async def test_update_failure_then_recovery(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Entities become unavailable while the API fails, then come back."""
    await setup_integration()
    assert hass.states.get(TRACKER).state != STATE_UNAVAILABLE

    mock_api(aioclient_mock, errors={"bike": 503})
    await _next_update(hass, freezer)
    assert hass.states.get(TRACKER).state == STATE_UNAVAILABLE

    mock_api(aioclient_mock)
    await _next_update(hass, freezer)
    assert hass.states.get(TRACKER).state != STATE_UNAVAILABLE
    assert hass.states.get(RANGE).state == "76.0"


async def test_connection_error_makes_entities_unavailable(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A network error on the bike list fails the update."""
    await setup_integration()
    aioclient_mock.clear_requests()
    aioclient_mock.get(API + "bike", exc=aiohttp.ClientConnectionError("boom"))
    await _next_update(hass, freezer)
    assert hass.states.get(TRACKER).state == STATE_UNAVAILABLE


async def test_complementary_error_keeps_last_value(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failing state request keeps the last known values, and is logged once."""
    await setup_integration()
    caplog.set_level(logging.INFO, logger="custom_components.geocover")

    mock_api(aioclient_mock, errors={"bike/1/state": 500})
    await _next_update(hass, freezer)
    await _next_update(hass, freezer)
    assert hass.states.get(RANGE).state == "76.0"
    assert hass.states.get("binary_sensor.velo_test_charging").state == "on"
    assert caplog.text.count("state of bike 1 is unavailable") == 1

    mock_api(aioclient_mock)
    await _next_update(hass, freezer)
    await _next_update(hass, freezer)
    assert caplog.text.count("state of bike 1 is available again") == 1


async def test_auth_error_during_operation_starts_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A rejected session opens a reauthentication flow; entities become unavailable."""
    entry = await setup_integration()

    mock_api(aioclient_mock, token_status=400, errors={"bike": 401})
    await _next_update(hass, freezer)

    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == [SOURCE_REAUTH]
    assert flows[0]["context"]["entry_id"] == entry.entry_id
    assert hass.states.get(TRACKER).state == STATE_UNAVAILABLE


async def test_rate_limit_fails_update(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """HTTP 429 fails the update without asking for a new sign-in."""
    entry = await setup_integration()
    mock_api(aioclient_mock, errors={"bike": 429})
    await _next_update(hass, freezer)

    assert hass.states.get(TRACKER).state == STATE_UNAVAILABLE
    assert not hass.config_entries.flow.async_progress()
    assert entry.runtime_data.last_update_success is False


async def test_requests_per_cycle(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Health and latest ride are only requested again when they may have changed."""
    await setup_integration()
    for path in ("bike", "bike/1/state", "bike/1/health", "v2/bike/1/ride"):
        assert api_calls(aioclient_mock, path) == 1, path

    # Bike at rest: bike list and state only.
    mock_api(aioclient_mock)
    await _next_update(hass, freezer)
    assert api_calls(aioclient_mock, "bike") == 1
    assert api_calls(aioclient_mock, "bike/1/state") == 1
    assert api_calls(aioclient_mock, "bike/1/health") == 0
    assert api_calls(aioclient_mock, "v2/bike/1/ride") == 0

    # During a ride, the latest ride is not requested even though the bike moves.
    mock_api(aioclient_mock, payloads={"bike": _bike(ride_in_progress=True)})
    await _next_update(hass, freezer)
    mock_api(
        aioclient_mock,
        payloads={"bike": _bike(ride_in_progress=True, odometer=5975000)},
    )
    await _next_update(hass, freezer)
    assert api_calls(aioclient_mock, "v2/bike/1/ride") == 0

    # The ride ends: the latest ride is requested.
    mock_api(aioclient_mock, payloads={"bike": _bike(odometer=5975000)})
    await _next_update(hass, freezer)
    assert api_calls(aioclient_mock, "v2/bike/1/ride") == 1
    assert api_calls(aioclient_mock, "bike/1/health") == 0

    # One hour later, health and latest ride are refreshed anyway.
    mock_api(aioclient_mock, payloads={"bike": _bike(odometer=5975000)})
    await _next_update(hass, freezer, timedelta(hours=1))
    assert api_calls(aioclient_mock, "bike/1/health") == 1
    assert api_calls(aioclient_mock, "v2/bike/1/ride") == 1


async def test_bike_moved_without_ride_refreshes_latest_ride(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A changed odometer at rest means a ride may have been recorded."""
    await setup_integration()
    mock_api(aioclient_mock, payloads={"bike": _bike(odometer=5980000)})
    await _next_update(hass, freezer)
    assert api_calls(aioclient_mock, "v2/bike/1/ride") == 1


async def test_failed_health_is_requested_again(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Data that could not be fetched is requested again on the next cycle."""
    await setup_integration(errors={"bike/1/health": 500})
    assert hass.states.get("sensor.velo_test_gps_tracker_battery").state == (
        STATE_UNKNOWN
    )
    mock_api(aioclient_mock)
    await _next_update(hass, freezer)
    assert api_calls(aioclient_mock, "bike/1/health") == 1
    assert hass.states.get("sensor.velo_test_gps_tracker_battery").state == "99"
