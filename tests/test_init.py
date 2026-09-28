from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.geocover.const import CONF_TOKENS, DOMAIN
from custom_components.geocover.diagnostics import async_get_config_entry_diagnostics

from .conftest import mock_api


async def _setup(hass, entry):
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_creates_entities(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    mock_api(aioclient_mock)
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "1")})
    assert device.name == "Vélo test" and device.manufacturer == "Decathlon"

    tracker = hass.states.get("device_tracker.velo_test")
    assert tracker.attributes["latitude"] == 48.85
    assert tracker.attributes["source_type"] == "gps"
    assert hass.states.get("sensor.velo_test_battery").state == "65"
    assert hass.states.get("sensor.velo_test_odometer").state == "5969.8"
    assert hass.states.get("sensor.velo_test_range").state == "76.0"
    assert hass.states.get("sensor.velo_test_gps_tracker_battery").state == "99"
    assert hass.states.get("sensor.velo_test_last_ride_distance").state == "7.37"
    assert hass.states.get("sensor.velo_test_last_ride").state == "2026-09-28T16:13:36+00:00"
    assert hass.states.get("binary_sensor.velo_test_charging").state == "on"
    assert hass.states.get("binary_sensor.velo_test_moving").state == "off"

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_rotated_refresh_token_is_persisted(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry, data={CONF_TOKENS: {"access_token": "at_0", "refresh_token": "rt_0", "expires_at": 0}})
    mock_api(aioclient_mock)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.data[CONF_TOKENS]["refresh_token"] == "rt_1"
    assert config_entry.data[CONF_TOKENS]["access_token"] == "at_1"


async def test_rejected_token_starts_reauth(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry, data={CONF_TOKENS: {"access_token": "", "refresh_token": "rt_dead", "expires_at": 0}})
    mock_api(aioclient_mock, token_status=400)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_diagnostics_are_redacted(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    mock_api(aioclient_mock)
    await _setup(hass, config_entry)
    diag = await async_get_config_entry_diagnostics(hass, config_entry)
    text = str(diag)
    for secret in ("at_0", "rt_0", "48.85", "000000000000000", "F1"):
        assert secret not in text
    assert diag["bikes"][1]["bike"]["battery_percentage"] == 65
