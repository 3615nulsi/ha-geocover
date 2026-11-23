"""Tests for the actions returning data."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.geocover.const import DOMAIN

from .conftest import API, SetupIntegration, bike_device, mock_api

LOCATIONS = [
    {"id": "b", "lat": 48.86, "lon": 2.36, "date": "2026-09-28T16:30:00+0000",
     "speed": 21, "is_moving": True, "bike_id": 1, "battery_percentage": 0},
    {"id": "a", "lat": 48.85, "lon": 2.35, "date": "2026-09-28T16:20:00+0000",
     "speed": 0, "is_moving": False, "bike_id": 1, "battery_percentage": 0},
]  # fmt: skip


async def _call(hass: HomeAssistant, service: str, **data: Any) -> Any:
    return await hass.services.async_call(
        DOMAIN, service, data, blocking=True, return_response=True
    )


async def _device_id(hass: HomeAssistant) -> str:
    device = bike_device(hass, 1)
    assert device is not None
    return device.id


async def test_get_rides(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """The rides of a bike are returned, filtered by period."""
    await setup_integration()
    device_id = await _device_id(hass)

    response = await _call(hass, "get_rides", device_id=device_id)
    assert [r["ride_id"] for r in response["rides"]] == [678]
    assert response["rides"][0]["distance_km"] == 7.37

    response = await _call(
        hass,
        "get_rides",
        device_id=device_id,
        start="2026-10-01T00:00:00+00:00",
        end="2026-11-01T00:00:00+00:00",
    )
    assert response["rides"] == []


async def test_get_locations(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
) -> None:
    """The GPS track is returned oldest first."""
    await setup_integration()
    aioclient_mock.get(API + "bike/1/location", json=LOCATIONS)
    response = await _call(
        hass,
        "get_locations",
        device_id=await _device_id(hass),
        start="2026-09-28 16:00:00",
        end="2026-09-28 17:00:00",
    )
    assert [p["latitude"] for p in response["locations"]] == [48.85, 48.86]
    assert response["locations"][1]["moving"] is True


@pytest.mark.parametrize(
    ("service", "data", "key"),
    [
        ("get_rides", {"device_id": "unknown"}, "bike_not_found"),
        (
            "get_rides",
            {"start": "2026-09-28 17:00:00", "end": "2026-09-28 16:00:00"},
            "invalid_period",
        ),
        (
            "get_locations",
            {"start": "2026-09-01 00:00:00", "end": "2026-09-28 00:00:00"},
            "period_too_long",
        ),
    ],
)
async def test_invalid_calls(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    service: str,
    data: dict[str, Any],
    key: str,
) -> None:
    """Invalid calls are explained to the user."""
    await setup_integration()
    data = {"device_id": await _device_id(hass), **data}
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, service, **data)
    assert err.value.translation_key == key


async def test_request_failed(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
) -> None:
    """A server error is reported."""
    await setup_integration()
    device_id = await _device_id(hass)
    mock_api(aioclient_mock, errors={"v2/bike/1/ride": 500})
    aioclient_mock.get(API + "bike/1/location", status=500, json={})
    with pytest.raises(HomeAssistantError):
        await _call(hass, "get_rides", device_id=device_id)
    with pytest.raises(HomeAssistantError):
        await _call(
            hass,
            "get_locations",
            device_id=device_id,
            start="2026-09-28 16:00:00",
            end="2026-09-28 17:00:00",
        )
