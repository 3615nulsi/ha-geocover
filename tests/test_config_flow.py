"""Tests for the Geocover config flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import aiohttp
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pygeocover.const import LOGIN_REDIRECT_URL
import pytest

from custom_components.geocover.const import CONF_REDIRECT_URL, CONF_TOKENS, DOMAIN

from .conftest import USER_UUID, load_fixture, mock_api


@pytest.fixture(autouse=True)
def mock_setup_entry() -> Generator[AsyncMock]:
    """Do not actually set up the integration in config flow tests."""
    with patch(
        "custom_components.geocover.async_setup_entry", return_value=True
    ) as mock:
        yield mock


def _whoops_url(result) -> str:
    """Return the address of the "Whoops!" page Decathlon would redirect to."""
    login_url = result["description_placeholders"]["login_url"]
    state = parse_qs(urlparse(login_url).query)["state"][0]
    return f"https://login.ids.conneq.tech/redirect?code=IDPCODE&state={state}"


async def test_user_flow(hass: HomeAssistant, aioclient_mock) -> None:
    mock_api(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["description_placeholders"]["login_url"].startswith(
        "https://idp.example/"
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Cycliste"
    assert result["result"].unique_id == USER_UUID
    assert result["data"][CONF_TOKENS]["refresh_token"] == "rt_1"


async def test_invalid_url_gives_new_link(hass: HomeAssistant, aioclient_mock) -> None:
    mock_api(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    first_url = result["description_placeholders"]["login_url"]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: "https://example.com/wrong-page"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}
    assert result["description_placeholders"]["login_url"] != first_url

    # The new link can then be used successfully.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_expired_code(hass: HomeAssistant, aioclient_mock) -> None:
    mock_api(aioclient_mock, token_status=400)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)}
    )
    assert result["errors"] == {"base": "invalid_url"}


async def test_already_configured(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    config_entry.add_to_hass(hass)
    mock_api(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    config_entry.add_to_hass(hass)
    mock_api(aioclient_mock)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_TOKENS]["refresh_token"] == "rt_1"
    await hass.async_block_till_done()


async def test_reauth_wrong_account(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(config_entry, unique_id="autre-compte")
    mock_api(aioclient_mock)
    result = await config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"


async def _start(hass: HomeAssistant) -> ConfigFlowResult:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_whoops_url_placeholder(hass: HomeAssistant, aioclient_mock) -> None:
    """The address to paste is shown, derived from the library."""
    mock_api(aioclient_mock)
    result = await _start(hass)
    assert result["description_placeholders"]["whoops_url"] == (
        f"{LOGIN_REDIRECT_URL}?code=…"
    )


@pytest.mark.parametrize(
    ("exc", "reason"),
    [
        (aiohttp.ClientConnectionError("boom"), "cannot_connect"),
        (RuntimeError("unexpected"), "unknown"),
    ],
)
async def test_cannot_prepare_sign_in(
    hass: HomeAssistant, aioclient_mock, exc: Exception, reason: str
) -> None:
    """The flow aborts when the sign-in page settings cannot be fetched."""
    mock_api(aioclient_mock, login_settings_exc=exc)
    result = await _start(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason


@pytest.mark.parametrize(
    ("exc", "error"),
    [
        (aiohttp.ClientConnectionError("boom"), "cannot_connect"),
        (RuntimeError("unexpected"), "unknown"),
    ],
)
async def test_errors_while_finishing(
    hass: HomeAssistant, aioclient_mock, exc: Exception, error: str
) -> None:
    """Errors during the token exchange are shown, then a new attempt succeeds."""
    mock_api(aioclient_mock, token_exc=exc)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_api(aioclient_mock)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_unexpected_code_exchange_answer(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """A malformed answer of the identity server is an unknown error."""
    mock_api(aioclient_mock)
    result = await _start(hass)
    with patch(
        "pygeocover.client.GeocoverClient._raw_request",
        # code exchange, then the settings of the new sign-in link
        side_effect=[{"unexpected": True}, load_fixture("login_settings")],
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)}
        )
    assert result["errors"] == {"base": "unknown"}


async def test_code_only_is_accepted(hass: HomeAssistant, aioclient_mock) -> None:
    """Pasting the code alone, instead of the whole address, works too."""
    mock_api(aioclient_mock)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: "IDPCODE"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_address_of_another_sign_in(hass: HomeAssistant, aioclient_mock) -> None:
    """An address from an older sign-in (different state) is rejected."""
    mock_api(aioclient_mock)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_REDIRECT_URL: f"{LOGIN_REDIRECT_URL}?code=IDPCODE&state=other"},
    )
    assert result["errors"] == {"base": "invalid_url"}
