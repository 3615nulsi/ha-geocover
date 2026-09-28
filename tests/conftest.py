"""Fixtures : API Geocover simulée au niveau HTTP (la vraie bibliothèque pygeocover est utilisée)."""
from __future__ import annotations

import time
from typing import Any

import pytest
from pygeocover.const import IDS_API, TOKEN_URL, bike_api_url
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
    "login_page_allowed_redirect_uris": ["tech.conneq.decathlon://decathlon.app.ids.conneq.tech"],
}
USER = {"id": 10, "username": USER_UUID, "name": "cycliste", "display_name": "Cycliste",
        "email": "cycliste@example.com", "country": "FR"}
BIKE = {
    "id": 1, "name": "Vélo test", "imei": "000000000000000", "battery_percentage": 65,
    "last_location": {"id": "x", "lat": 48.85, "lon": 2.35, "date": "2026-09-28T16:37:45+0000",
                      "speed": 0, "battery_percentage": 65, "bike_id": 1, "is_moving": False},
    "geofences": [], "odometer": 5969800, "frame_number": "F1", "ride_in_progress": False,
}
STATE = [{"powered_on": False, "ecu_locked": False, "battery_percentage": 65, "charging": True,
          "range": 76, "odometer": 5970}]
HEALTH = [
    {"key": "last_connection", "status": True, "value": "2026-09-28T16:38:00+0000", "value_type": "datetime"},
    {"key": "gps_battery", "status": True, "value": "99%", "value_type": "string"},
]
RIDES = {"meta": {"limit": 1, "offset": 0, "total_records": 678}, "data": [{
    "id": 678, "start_date": "2026-09-28T16:13:36+0000", "end_date": "2026-09-28T16:37:36+0000",
    "distance_traveled": 7370, "active_time": 1440, "avg_speed": 19, "elevation_up": 245,
    "elevation_down": 225, "calories": 90, "co2": 1800, "name": ""}]}


def token_response(n: int) -> dict[str, Any]:
    return {"token_type": "Bearer", "access_token": f"at_{n}", "expires_in": 14400,
            "refresh_token": f"rt_{n}", "id_token": "x.y.z"}


def mock_api(aioclient_mock: AiohttpClientMocker, *, token_status: int = 200) -> None:
    """Enregistre toutes les réponses ; POST /oauth répond selon grant_type."""

    async def oauth(method, url, data):
        if token_status != 200:
            return AiohttpClientMockResponse(method, url, status=token_status,
                                             json={"error": "invalid_grant"})
        payload = {"code": "IDSCODE"} if data.get("grant_type") == "idp_authorization_code" \
            else token_response(1)
        return AiohttpClientMockResponse(method, url, json=payload)

    aioclient_mock.get(f"{IDS_API}/client/5c0d36ce-7396-46f0-bcc0-3c6e16c0d2b6/setting/loginpage",
                       json=LOGIN_SETTINGS)
    aioclient_mock.post(TOKEN_URL, side_effect=oauth)
    aioclient_mock.get(API + "user/me", json=USER)
    aioclient_mock.get(API + "bike", json=[BIKE])
    aioclient_mock.get(API + "bike/1/state", json=STATE)
    aioclient_mock.get(API + "bike/1/health", json=HEALTH)
    aioclient_mock.get(API + "v2/bike/1/ride", json=RIDES)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN, title="Cycliste", unique_id=USER_UUID,
        data={CONF_TOKENS: {"access_token": "at_0", "refresh_token": "rt_0",
                            "expires_at": time.time() + 3600}},
    )
