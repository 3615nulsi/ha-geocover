"""Tests for the setup, unload and token handling of the integration."""

from __future__ import annotations

import time

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.geocover.const import CONF_TOKENS, DOMAIN

from .conftest import (
    API,
    SetupIntegration,
    bikes_with,
    load_fixture,
    mock_api,
    next_update,
)


async def test_setup_and_unload(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """One device per bike is created, and the entry unloads cleanly."""
    entry = await setup_integration()
    assert entry.state is ConfigEntryState.LOADED

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert [d.identifiers for d in devices] == [{(DOMAIN, "1")}]
    assert devices[0].name == "Vélo test"
    assert devices[0].serial_number == "F1"

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_rotated_refresh_token_is_persisted(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """A refreshed (rotating, single-use) refresh token is saved in the entry."""
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry,
        data={
            CONF_TOKENS: {
                "access_token": "at_0",
                "refresh_token": "rt_0",
                "expires_at": 0,
            }
        },
    )
    mock_api(aioclient_mock)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.data[CONF_TOKENS]["refresh_token"] == "rt_1"
    assert config_entry.data[CONF_TOKENS]["access_token"] == "at_1"


async def test_rejected_token_starts_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """A refresh token rejected by the server opens a reauthentication flow."""
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry,
        data={
            CONF_TOKENS: {
                "access_token": "",
                "refresh_token": "rt_dead",
                "expires_at": 0,
            }
        },
    )
    mock_api(aioclient_mock, token_status=400)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_device_info(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """The device shows the manufacturer and product reference, no fake model."""
    entry = await setup_integration()
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "1")})
    assert device is not None
    assert device.config_entries == {entry.entry_id}
    assert device.manufacturer == "Decathlon"
    assert device.model is None
    assert device.model_id == "0000000000000"


async def test_device_from_older_version_is_fixed(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_integration: SetupIntegration,
) -> None:
    """Versions < 0.3 stored the bike name as model: it is cleared."""
    config_entry.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "1")},
        name="Vélo test",
        manufacturer="Decathlon",
        model="Vélo test",
    )
    await setup_integration()
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "1")})
    assert device is not None
    assert device.model is None
    assert device.model_id == "0000000000000"


async def test_renamed_bike_renames_device(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A bike renamed in the app is renamed in Home Assistant, not over a user name."""
    await setup_integration()
    registry = dr.async_get(hass)
    device = registry.async_get_device(identifiers={(DOMAIN, "1")})
    assert device is not None
    registry.async_update_device(device.id, name_by_user="Mon vélo")

    mock_api(aioclient_mock, payloads={"bike": bikes_with(name="Nouveau nom")})
    await next_update(hass, freezer)

    device = registry.async_get_device(identifiers={(DOMAIN, "1")})
    assert device is not None
    assert device.name == "Nouveau nom"
    assert device.name_by_user == "Mon vélo"


async def test_new_bike_is_added(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A bike added to the account appears without reloading the integration."""
    await setup_integration()
    second = {**load_fixture("bikes")[0], "id": 2, "name": "Second vélo"}
    mock_api(aioclient_mock, payloads={"bike": [*load_fixture("bikes"), second]})
    for path in ("bike/2/state", "bike/2/health", "v2/bike/2/ride"):
        aioclient_mock.get(API + path, status=404, json={})
    await next_update(hass, freezer)

    assert dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "2")})
    assert hass.states.get("device_tracker.second_velo") is not None
    assert hass.states.get("sensor.second_velo_battery").state == "65"


async def test_removed_bike_removes_device(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A bike that left the account no longer leaves a ghost device."""
    await setup_integration()
    mock_api(aioclient_mock, payloads={"bike": []})
    await next_update(hass, freezer)

    assert dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "1")}) is None
    assert hass.states.get("device_tracker.velo_test") is None


async def test_failed_update_keeps_devices(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Devices are never removed because of an API error."""
    await setup_integration()
    mock_api(aioclient_mock, errors={"bike": 500})
    await next_update(hass, freezer)
    assert dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "1")})


async def test_remove_device(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    setup_integration: SetupIntegration,
) -> None:
    """A device can only be removed by hand once its bike left the account."""
    assert await async_setup_component(hass, "config", {})
    entry = await setup_integration()
    registry = dr.async_get(hass)
    bike = registry.async_get_device(identifiers={(DOMAIN, "1")})
    old = registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "99")}
    )
    assert bike is not None

    client = await hass_ws_client(hass)
    for device, removable in ((bike, False), (old, True)):
        response = await client.remove_device(device.id, entry.entry_id)
        assert response["success"] is removable


async def test_shared_bike_is_provided_once(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: SetupIntegration,
) -> None:
    """A bike shared with a second configured account is only provided once."""
    await setup_integration()

    other = MockConfigEntry(
        domain=DOMAIN,
        title="Autre",
        unique_id="other-account",
        data={
            CONF_TOKENS: {
                "access_token": "at_0",
                "refresh_token": "rt_0",
                "expires_at": time.time() + 3600,
            }
        },
    )
    mock_api(
        aioclient_mock,
        payloads={"bike": bikes_with(is_requesting_user_owner=False)},
    )
    other.add_to_hass(hass)
    await hass.config_entries.async_setup(other.entry_id)
    await hass.async_block_till_done()

    assert other.state is ConfigEntryState.LOADED
    assert other.runtime_data.data == {}
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "1")})
    assert device is not None
    assert other.entry_id not in device.config_entries


async def test_entities_disabled_by_default(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """Secondary entities are created disabled."""
    await setup_integration()
    registry = er.async_get(hass)
    for entity_id in (
        "sensor.velo_test_speed",
        "sensor.velo_test_last_position_update",
        "sensor.velo_test_last_connection",
        "sensor.velo_test_gps_tracker_battery",
        "sensor.velo_test_last_ride_average_speed",
        "sensor.velo_test_last_ride_elevation_gain",
    ):
        entity = registry.async_get(entity_id)
        assert entity is not None, entity_id
        assert entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get("sensor.velo_test_battery") is not None
