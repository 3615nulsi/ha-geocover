"""Tests for the setup, unload and token handling of the integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.geocover.const import CONF_TOKENS, DOMAIN

from .conftest import SetupIntegration, mock_api


async def test_setup_and_unload(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """One device per bike is created, and the entry unloads cleanly."""
    entry = await setup_integration()
    assert entry.state is ConfigEntryState.LOADED

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert [d.identifiers for d in devices] == [{(DOMAIN, "1")}]
    assert devices[0].name == "Vélo test"
    assert devices[0].manufacturer == "Decathlon"
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
