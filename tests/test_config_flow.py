from urllib.parse import parse_qs, urlparse

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.geocover.const import CONF_REDIRECT_URL, CONF_TOKENS, DOMAIN

from .conftest import USER_UUID, mock_api


def _whoops_url(result) -> str:
    """Simule l'adresse de la page « Whoops! » renvoyée par Decathlon."""
    login_url = result["description_placeholders"]["login_url"]
    state = parse_qs(urlparse(login_url).query)["state"][0]
    return f"https://login.ids.conneq.tech/redirect?code=IDPCODE&state={state}"


async def test_user_flow(hass: HomeAssistant, aioclient_mock) -> None:
    mock_api(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    assert result["description_placeholders"]["login_url"].startswith("https://idp.example/")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Cycliste"
    assert result["result"].unique_id == USER_UUID
    assert result["data"][CONF_TOKENS]["refresh_token"] == "rt_1"


async def test_invalid_url_gives_new_link(hass: HomeAssistant, aioclient_mock) -> None:
    mock_api(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER})
    first_url = result["description_placeholders"]["login_url"]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: "https://example.com/pas-la-bonne-page"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}
    assert result["description_placeholders"]["login_url"] != first_url

    # on peut ensuite réussir avec le nouveau lien
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_expired_code(hass: HomeAssistant, aioclient_mock) -> None:
    mock_api(aioclient_mock, token_status=400)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)})
    assert result["errors"] == {"base": "invalid_url"}


async def test_already_configured(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    config_entry.add_to_hass(hass)
    mock_api(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"


async def test_reauth(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    config_entry.add_to_hass(hass)
    mock_api(aioclient_mock)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_TOKENS]["refresh_token"] == "rt_1"


async def test_reauth_wrong_account(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(config_entry, unique_id="autre-compte")
    mock_api(aioclient_mock)
    result = await config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REDIRECT_URL: _whoops_url(result)})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "wrong_account"
