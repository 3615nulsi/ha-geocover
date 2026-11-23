"""Tests for the repair issues."""

from __future__ import annotations

from datetime import datetime, timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.geocover.const import DOMAIN

from .conftest import SetupIntegration, bikes_with, load_fixture, mock_api, next_update


def _issue(hass: HomeAssistant, kind: str) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, f"{kind}_1")


def _health(*, battery: str = "99%", last_connection: datetime | None = None) -> list:
    health = load_fixture("health")
    for item in health:
        if item["key"] == "gps_battery":
            item["value"] = battery
        if item["key"] == "last_connection" and last_connection is not None:
            item["value"] = last_connection.strftime("%Y-%m-%dT%H:%M:%S%z")
    return health


async def test_stolen_bike(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A bike reported stolen raises an error issue, removed when it is found."""
    await setup_integration(payloads={"bike": bikes_with(is_stolen=True)})
    issue = _issue(hass, "bike_stolen")
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.ERROR
    assert issue.translation_placeholders == {"bike": "Vélo test"}

    mock_api(aioclient_mock)
    await next_update(hass, freezer)
    assert _issue(hass, "bike_stolen") is None


async def test_tracker_battery(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Low tracker battery raises an issue, cleared only well above the threshold."""
    await setup_integration(payloads={"bike/1/health": _health(battery="15%")})
    issue = _issue(hass, "tracker_battery_low")
    assert issue is not None
    assert issue.translation_placeholders["level"] == "15"

    mock_api(aioclient_mock, payloads={"bike/1/health": _health(battery="22%")})
    await next_update(hass, freezer, timedelta(hours=1))
    assert _issue(hass, "tracker_battery_low") is not None  # hysteresis

    mock_api(aioclient_mock, payloads={"bike/1/health": _health(battery="30%")})
    await next_update(hass, freezer, timedelta(hours=1))
    assert _issue(hass, "tracker_battery_low") is None


async def test_no_connection(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A tracker silent for days raises an issue, cleared when it connects again."""
    now = datetime.now().astimezone()
    await setup_integration(
        payloads={"bike/1/health": _health(last_connection=now - timedelta(days=4))}
    )
    issue = _issue(hass, "no_connection")
    assert issue is not None
    assert issue.translation_placeholders["days"] == "4"

    mock_api(
        aioclient_mock,
        payloads={"bike/1/health": _health(last_connection=now + timedelta(hours=1))},
    )
    await next_update(hass, freezer, timedelta(hours=1))
    assert _issue(hass, "no_connection") is None


async def test_issues_of_removed_bike_are_deleted(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """When a bike leaves the account, its issues go with it."""
    await setup_integration(payloads={"bike": bikes_with(is_stolen=True)})
    assert _issue(hass, "bike_stolen") is not None
    mock_api(aioclient_mock, payloads={"bike": []})
    await next_update(hass, freezer)
    assert _issue(hass, "bike_stolen") is None


async def test_issues_deleted_with_the_entry(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """Removing the integration removes its issues."""
    entry = await setup_integration(payloads={"bike": bikes_with(is_stolen=True)})
    assert _issue(hass, "bike_stolen") is not None
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert _issue(hass, "bike_stolen") is None
