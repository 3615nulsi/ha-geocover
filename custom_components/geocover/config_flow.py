"""Config flow: sign in to the Decathlon account.

The Geocover app only allows a redirect to its own scheme (tech.conneq.decathlon://).
The user therefore signs in with their browser, then pastes the address of the
"Whoops!" error page shown at the end (see pygeocover.auth).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

try:
    import probatio as vol
except ImportError:  # Home Assistant < 2026.9 validates with voluptuous
    import voluptuous as vol  # type: ignore[no-redef]

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pygeocover import (
    GeocoverClient,
    GeocoverConnectionError,
    GeocoverLoginError,
    LoginRequest,
)
from pygeocover.const import LOGIN_REDIRECT_URL

from .const import CONF_REDIRECT_URL, CONF_TOKENS, DOMAIN, LOGGER

SCHEMA = vol.Schema({vol.Required(CONF_REDIRECT_URL): str})
# Address of the error page to paste (hassfest forbids hard-coded URLs in translations).
WHOOPS_URL = f"{LOGIN_REDIRECT_URL}?code=…"


class GeocoverConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Geocover."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._client: GeocoverClient | None = None
        self._login: LoginRequest | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial sign-in."""
        return await self._async_login_step("user", user_input)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a rejected session."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to sign in again."""
        return await self._async_login_step("reauth_confirm", user_input)

    async def _async_login_step(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        """Show the sign-in link, then finish the sign-in with the pasted address."""
        errors: dict[str, str] = {}
        if self._client is None:
            self._client = GeocoverClient(async_get_clientsession(self.hass))

        if user_input is not None and self._login is not None:
            try:
                tokens = await self._client.async_finish_login(
                    self._login, user_input[CONF_REDIRECT_URL]
                )
                user = await self._client.async_get_user()
            except GeocoverLoginError as err:
                LOGGER.debug("Sign-in rejected: %s", err)
                errors["base"] = "invalid_url"
            except GeocoverConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error during sign-in")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user.username)
                data = {CONF_TOKENS: tokens.to_dict()}
                if self.source == SOURCE_REAUTH:
                    self._abort_if_unique_id_mismatch(reason="wrong_account")
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(), data_updates=data
                    )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user.name or user.username, data=data
                )
            # The Decathlon code is single-use and expires quickly: new link on every try.
            self._login = None

        if self._login is None:
            try:
                self._login = await self._client.async_start_login()
            except GeocoverConnectionError:
                return self.async_abort(reason="cannot_connect")
            except Exception:
                LOGGER.exception("Unexpected error while preparing the sign-in")
                return self.async_abort(reason="unknown")

        return self.async_show_form(
            step_id=step_id,
            data_schema=SCHEMA,
            errors=errors,
            description_placeholders={
                "login_url": self._login.url,
                "whoops_url": WHOOPS_URL,
            },
        )
