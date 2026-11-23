"""Tests for the ride finished event."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import snapshot_platform
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from syrupy.assertion import SnapshotAssertion

from .conftest import SetupIntegration, bikes_with, load_fixture, mock_api, next_update

EVENT = "event.velo_test_ride"


def _rides_with(**changes: Any) -> dict[str, Any]:
    rides = load_fixture("rides")
    rides["data"][0].update(changes)
    rides["meta"]["total_records"] += 1
    return rides


async def test_no_event_at_startup(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """The ride already recorded at startup is not an event."""
    await setup_integration()
    assert hass.states.get(EVENT).state == STATE_UNKNOWN


async def test_ride_finished(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A new ride fires the event once, with its summary, when it is over."""
    await setup_integration()

    # During the ride, an unfinished ride may already be listed: no event.
    mock_api(
        aioclient_mock,
        payloads={
            "bike": bikes_with(ride_in_progress=True),
            "v2/bike/1/ride": _rides_with(id=679, end_date=None),
        },
    )
    await next_update(hass, freezer)
    assert hass.states.get(EVENT).state == STATE_UNKNOWN

    # The ride is over.
    mock_api(
        aioclient_mock,
        payloads={
            "bike": bikes_with(odometer=5977400),
            "v2/bike/1/ride": _rides_with(id=679),
        },
    )
    await next_update(hass, freezer)
    state = hass.states.get(EVENT)
    assert state.state != STATE_UNKNOWN
    assert state.attributes["event_type"] == "ride_finished"
    assert state.attributes["ride_id"] == 679
    assert state.attributes["distance_km"] == 7.37
    assert state.attributes["duration_min"] == 24
    fired_at = state.state

    # Same ride seen again (hourly refresh): no new event.
    mock_api(
        aioclient_mock,
        payloads={
            "bike": bikes_with(odometer=5977400),
            "v2/bike/1/ride": _rides_with(id=679),
        },
    )
    await next_update(hass, freezer, timedelta(hours=1))
    assert hass.states.get(EVENT).state == fired_at


async def test_no_baseline_when_rides_failed(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """If the rides could not be fetched at startup, the first ones are not an event."""
    await setup_integration(errors={"v2/bike/1/ride": 500})
    mock_api(aioclient_mock)
    await next_update(hass, freezer)
    assert hass.states.get(EVENT).state == STATE_UNKNOWN


@pytest.mark.latest_ha_only
async def test_snapshot(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """The event entity, with its registry entry and state."""
    with patch("custom_components.geocover.PLATFORMS", [Platform.EVENT]):
        entry = await setup_integration()
    await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)
