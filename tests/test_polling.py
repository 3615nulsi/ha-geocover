"""Tests for the adaptive polling interval."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pygeocover import Bike, BikeState
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.geocover.const import (
    IDLE_INTERVAL,
    RIDING_INTERVAL,
    UPDATE_INTERVAL,
)
from custom_components.geocover.coordinator import BikeData, interval_for

from .conftest import SetupIntegration, bikes_with, load_fixture, mock_api, next_update

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=dt_util.UTC)


def _data(
    *,
    fix_age: timedelta | None = timedelta(minutes=1),
    moving: bool = False,
    ride: bool = False,
    charging: bool = False,
    powered_on: bool = False,
) -> dict[int, BikeData]:
    raw: dict[str, Any] = load_fixture("bikes")[0]
    raw["ride_in_progress"] = ride
    if fix_age is None:
        raw["last_location"] = None
    else:
        raw["last_location"].update(
            is_moving=moving,
            date=(NOW - fix_age).strftime("%Y-%m-%dT%H:%M:%S%z"),
        )
    state = load_fixture("state")[0]
    state.update(charging=charging, powered_on=powered_on)
    return {
        1: BikeData(
            bike=Bike.from_dict(raw),
            state=BikeState.from_dict(state),
            health=None,
            rides=None,
        )
    }


def test_interval_rules() -> None:
    """Fast while riding, normal when active or recently moved, slow when asleep."""
    assert interval_for({}, NOW) == UPDATE_INTERVAL
    assert interval_for(_data(ride=True), NOW) == RIDING_INTERVAL
    assert interval_for(_data(moving=True), NOW) == RIDING_INTERVAL
    # an old "moving" fix does not say the bike moves now
    assert (
        interval_for(_data(moving=True, fix_age=timedelta(hours=5)), NOW)
        == IDLE_INTERVAL
    )
    assert interval_for(_data(), NOW) == UPDATE_INTERVAL
    assert interval_for(_data(fix_age=timedelta(hours=5)), NOW) == IDLE_INTERVAL
    assert (
        interval_for(_data(fix_age=timedelta(hours=5), charging=True), NOW)
        == UPDATE_INTERVAL
    )
    assert (
        interval_for(_data(fix_age=timedelta(hours=5), powered_on=True), NOW)
        == UPDATE_INTERVAL
    )
    assert interval_for(_data(fix_age=None), NOW) == UPDATE_INTERVAL


async def test_interval_follows_the_bike(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The coordinator polls every minute during a ride, then slows down."""
    entry = await setup_integration()
    coordinator = entry.runtime_data
    # charging bike: normal interval
    assert coordinator.update_interval == UPDATE_INTERVAL

    mock_api(aioclient_mock, payloads={"bike": bikes_with(ride_in_progress=True)})
    await next_update(hass, freezer)
    assert coordinator.update_interval == RIDING_INTERVAL

    # Ride over, not charging, position reported long ago: asleep.
    state = load_fixture("state")
    state[0]["charging"] = False
    mock_api(aioclient_mock, payloads={"bike/1/state": state})
    await next_update(hass, freezer, RIDING_INTERVAL)
    assert coordinator.update_interval == IDLE_INTERVAL
