"""Fixtures: the Geocover API is mocked at the HTTP level, the real pygeocover is used."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import time
from typing import Any

from homeassistant.core import HomeAssistant
from pygeocover.const import DEFAULT_CLIENT_ID, IDS_API, TOKEN_URL, bike_api_url
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from custom_components.geocover.const import CONF_TOKENS, DOMAIN

API = bike_api_url()
USER_UUID = "00000000-0000-0000-0000-000000000001"

LOGIN_SETTINGS = {
    "idp_client_id": "idp-client",
    "idp_issuer_id": "https://idp.example/connect",
    "idp_redirect_uri": "https://login.ids.conneq.tech/oauth/idpresponse",
    "idp_scopes": "email openid profile",
    "idp_uri": "https://idp.example/connect/oauth/authorize",
    "login_page_allowed_redirect_uris": [
        "tech.conneq.decathlon://decathlon.app.ids.conneq.tech"
    ],
}
USER = {
    "id": 10,
    "username": USER_UUID,
    "name": "cycliste",
    "display_name": "Cycliste",
    "email": "cycliste@example.com",
    "country": "FR",
}
BIKE = {
    "id": 1,
    "name": "Vélo test",
    "imei": "000000000000000",
    "battery_percentage": 65,
    "last_location": {
        "id": "x",
        "lat": 48.85,
        "lon": 2.35,
        "date": "2026-09-28T16:37:45+0000",
        "speed": 0,
        "battery_percentage": 65,
        "bike_id": 1,
        "is_moving": False,
    },
    "geofences": [],
    "odometer": 5969800,
    "frame_number": "F1",
    "ride_in_progress": False,
}
STATE = [
    {
        "powered_on": False,
        "ecu_locked": False,
        "battery_percentage": 65,
        "charging": True,
        "range": 76,
        "odometer": 5970,
    }
]
HEALTH = [
    {
        "key": "last_connection",
        "status": True,
        "value": "2026-09-28T16:38:00+0000",
        "value_type": "datetime",
    },
    {"key": "gps_battery", "status": True, "value": "99%", "value_type": "string"},
]
RIDES = {
    "meta": {"limit": 1, "offset": 0, "total_records": 678},
    "data": [
        {
            "id": 678,
            "start_date": "2026-09-28T16:13:36+0000",
            "end_date": "2026-09-28T16:37:36+0000",
            "distance_traveled": 7370,
            "active_time": 1440,
            "avg_speed": 19,
            "elevation_up": 245,
            "elevation_down": 225,
            "calories": 90,
            "co2": 1800,
            "name": "",
        }
    ],
}


def token_response(n: int) -> dict[str, Any]:
    """Return the n-th token response of the identity server."""
    return {
        "token_type": "Bearer",
        "access_token": f"at_{n}",
        "expires_in": 14400,
        "refresh_token": f"rt_{n}",
        "id_token": "x.y.z",
    }


def mock_api(
    aioclient_mock: AiohttpClientMocker,
    *,
    token_status: int = 200,
    errors: dict[str, int] | None = None,
) -> None:
    """Register every API response; POST /oauth answers according to grant_type.

    `errors` maps a bike API path (e.g. "bike/1/state") to an HTTP error status.
    """
    errors = errors or {}

    async def oauth(
        method: str, url: Any, data: dict[str, Any]
    ) -> AiohttpClientMockResponse:
        if token_status != 200:
            return AiohttpClientMockResponse(
                method, url, status=token_status, json={"error": "invalid_grant"}
            )
        payload = (
            {"code": "IDSCODE"}
            if data.get("grant_type") == "idp_authorization_code"
            else token_response(1)
        )
        return AiohttpClientMockResponse(method, url, json=payload)

    aioclient_mock.get(
        f"{IDS_API}/client/{DEFAULT_CLIENT_ID}/setting/loginpage", json=LOGIN_SETTINGS
    )
    aioclient_mock.post(TOKEN_URL, side_effect=oauth)
    responses: tuple[tuple[str, Any], ...] = (
        ("user/me", USER),
        ("bike", [BIKE]),
        ("bike/1/state", STATE),
        ("bike/1/health", HEALTH),
        ("v2/bike/1/ride", RIDES),
    )
    for path, payload in responses:
        if path in errors:
            aioclient_mock.get(API + path, status=errors[path], json={})
        else:
            aioclient_mock.get(API + path, json=payload)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable the custom integration in every test."""


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry holding valid tokens."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Cycliste",
        unique_id=USER_UUID,
        data={
            CONF_TOKENS: {
                "access_token": "at_0",
                "refresh_token": "rt_0",
                "expires_at": time.time() + 3600,
            }
        },
    )


type SetupIntegration = Callable[..., Awaitable[MockConfigEntry]]


@pytest.fixture
def setup_integration(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> SetupIntegration:
    """Return a helper that mocks the API, then sets up the config entry."""

    async def _setup(**mock_kwargs: Any) -> MockConfigEntry:
        mock_api(aioclient_mock, **mock_kwargs)
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        return config_entry

    return _setup
