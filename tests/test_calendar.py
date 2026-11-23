"""Tests for the ride calendar and the ride history."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.calendar import DOMAIN as CALENDAR_DOMAIN
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.geocover.rides import PAGE_SIZE

from .conftest import API, SetupIntegration, api_calls, load_fixture, mock_api

CALENDAR = "calendar.velo_test_rides"


def _ride(ride_id: int, start: str, end: str) -> dict[str, Any]:
    ride = load_fixture("rides")["data"][0]
    ride.update(id=ride_id, start_date=start, end_date=end)
    return ride


async def _events(hass: HomeAssistant, start: str, end: str) -> list[dict[str, Any]]:
    response = await hass.services.async_call(
        CALENDAR_DOMAIN,
        "get_events",
        {"entity_id": CALENDAR, "start_date_time": start, "end_date_time": end},
        blocking=True,
        return_response=True,
    )
    return response[CALENDAR]["events"]  # type: ignore[index,return-value]


async def test_calendar_state(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """The calendar shows the latest ride without any extra request."""
    await setup_integration()
    state = hass.states.get(CALENDAR)
    assert state.state == STATE_OFF
    assert state.attributes["message"] == "7.4 km · 24 min"


async def test_calendar_events(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
) -> None:
    """Rides of a period are listed; the history is fetched once, page by page."""
    await setup_integration()
    rides = [
        _ride(
            1000 - i,
            f"2026-09-{28 - i // 3:02d}T{8 + i % 3:02d}:00:00+0000",
            f"2026-09-{28 - i // 3:02d}T{8 + i % 3:02d}:30:00+0000",
        )
        for i in range(PAGE_SIZE + 10)
    ]
    aioclient_mock.clear_requests()
    total = len(rides)
    for offset in (0, PAGE_SIZE):
        aioclient_mock.get(
            API + "v2/bike/1/ride",
            params={"limit": PAGE_SIZE, "offset": offset, "order": "start_date;desc"},
            json={
                "meta": {"limit": PAGE_SIZE, "offset": offset, "total_records": total},
                "data": rides[offset : offset + PAGE_SIZE],
            },
        )

    events = await _events(
        hass, "2026-09-28T00:00:00+00:00", "2026-09-29T00:00:00+00:00"
    )
    assert [e["summary"] for e in events] == ["7.4 km · 24 min"] * 3
    assert datetime.fromisoformat(events[0]["start"]) == datetime(
        2026, 9, 28, 8, tzinfo=UTC
    )
    assert events[0]["description"].startswith("⌀ 19.0 km/h")
    assert api_calls(aioclient_mock, "v2/bike/1/ride") == 2

    older = await _events(
        hass, "2026-09-01T00:00:00+00:00", "2026-09-10T00:00:00+00:00"
    )
    assert len(older) == 3
    assert api_calls(aioclient_mock, "v2/bike/1/ride") == 2  # served from memory


async def test_calendar_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
) -> None:
    """A server error while reading the history is reported."""
    await setup_integration()
    mock_api(aioclient_mock, errors={"v2/bike/1/ride": 500})
    with pytest.raises(HomeAssistantError):
        await _events(hass, "2026-09-28T00:00:00+00:00", "2026-09-29T00:00:00+00:00")
