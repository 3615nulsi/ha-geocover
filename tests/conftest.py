"""Fixtures: the Geocover API is mocked at the HTTP level, the real pygeocover is used."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Generator
import copy
from datetime import timedelta
import json
from pathlib import Path
import time
from typing import Any
from unittest.mock import PropertyMock, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pygeocover.const import DEFAULT_CLIENT_ID, IDS_API, TOKEN_URL, bike_api_url
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)
from syrupy.assertion import SnapshotAssertion

from custom_components.geocover.const import CONF_TOKENS, DOMAIN, UPDATE_INTERVAL

API = bike_api_url()
LOGIN_SETTINGS_URL = f"{IDS_API}/client/{DEFAULT_CLIENT_ID}/setting/loginpage"
USER_UUID = "00000000-0000-0000-0000-000000000001"

FIXTURES = Path(__file__).parent / "fixtures"

# Bike API path -> fixture file
API_FIXTURES = {
    "user/me": "user",
    "bike": "bikes",
    "bike/1/state": "state",
    "bike/1/health": "health",
    "v2/bike/1/ride": "rides",
}


def load_fixture(name: str) -> Any:
    """Load a JSON fixture (a fresh copy every time)."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


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
    token_exc: Exception | None = None,
    login_settings_exc: Exception | None = None,
    errors: dict[str, int] | None = None,
    payloads: dict[str, Any] | None = None,
) -> None:
    """Register every API response; POST /oauth answers according to grant_type.

    Previous registrations are cleared, so it can be called again between two
    updates. `errors` maps a bike API path (e.g. "bike/1/state") to an HTTP error
    status, `payloads` replaces the fixture of a path.
    """
    aioclient_mock.clear_requests()
    errors = errors or {}
    payloads = payloads or {}

    async def oauth(
        method: str, url: Any, data: dict[str, Any]
    ) -> AiohttpClientMockResponse:
        if token_exc is not None:
            raise token_exc
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

    if login_settings_exc is not None:
        aioclient_mock.get(LOGIN_SETTINGS_URL, exc=login_settings_exc)
    else:
        aioclient_mock.get(LOGIN_SETTINGS_URL, json=load_fixture("login_settings"))
    aioclient_mock.post(TOKEN_URL, side_effect=oauth)
    for path, fixture in API_FIXTURES.items():
        if path in errors:
            aioclient_mock.get(API + path, status=errors[path], json={})
        else:
            payload = payloads[path] if path in payloads else load_fixture(fixture)
            aioclient_mock.get(API + path, json=copy.deepcopy(payload))


def api_calls(aioclient_mock: AiohttpClientMocker, path: str) -> int:
    """Return how many times a bike API path was requested."""
    return sum(
        1
        for call in aioclient_mock.mock_calls
        if str(call[1].with_query(None)) == API + path
    )


async def next_update(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    delta: timedelta = UPDATE_INTERVAL,
) -> None:
    """Move time forward and let the coordinator update."""
    freezer.tick(delta)
    async_fire_time_changed(hass)
    # The scheduled refresh runs as a background task.
    await hass.async_block_till_done(wait_background_tasks=True)


def bike_device(hass: HomeAssistant, bike_id: int) -> dr.DeviceEntry | None:
    """Return the device of a bike, if any (works on every supported HA version)."""
    return next(
        (
            device
            for device in dr.async_get(hass).devices.values()
            if (DOMAIN, str(bike_id)) in device.identifiers
        ),
        None,
    )


def bikes_with(**changes: Any) -> list[dict[str, Any]]:
    """Return the bike list fixture with some fields changed."""
    bikes = load_fixture("bikes")
    bikes[0].update(changes)
    return bikes


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable the custom integration in every test."""


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Serialize Home Assistant objects without their random ids and dates."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture
def entity_registry_enabled_by_default() -> Generator[None]:
    """Enable the entities that are disabled by default."""
    with patch(
        "homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
        return_value=True,
        new_callable=PropertyMock,
    ):
        yield


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
