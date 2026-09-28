"""Assistant de configuration : connexion au compte Decathlon.

L'app n'autorise qu'une redirection vers son propre schéma (tech.conneq.decathlon://).
L'utilisateur se connecte donc dans son navigateur, puis colle l'adresse de la page
d'erreur « Whoops! » affichée à la fin (voir pygeocover.auth).
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pygeocover import (
    GeocoverClient,
    GeocoverConnectionError,
    GeocoverError,
    GeocoverLoginError,
    LoginRequest,
)
import voluptuous as vol

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_REDIRECT_URL, CONF_TOKENS, DOMAIN, LOGGER

SCHEMA = vol.Schema({vol.Required(CONF_REDIRECT_URL): str})
# adresse de la page d'erreur à coller (hassfest interdit les URL en dur dans les traductions)
WHOOPS_URL = "https://login.ids.conneq.tech/redirect?code=…"


class GeocoverConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._client: GeocoverClient | None = None
        self._login: LoginRequest | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_login_step("user", user_input)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_login_step("reauth_confirm", user_input)

    async def _async_login_step(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
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
                LOGGER.debug("Connexion refusée : %s", err)
                errors["base"] = "invalid_url"
            except GeocoverConnectionError:
                errors["base"] = "cannot_connect"
            except GeocoverError:
                LOGGER.exception("Erreur inattendue pendant la connexion")
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
                return self.async_create_entry(title=user.name or user.username, data=data)
            # le code Decathlon est à usage unique et expire vite : nouvelle URL à chaque essai
            self._login = None

        if self._login is None:
            try:
                self._login = await self._client.async_start_login()
            except GeocoverError:
                return self.async_abort(reason="cannot_connect")

        return self.async_show_form(
            step_id=step_id,
            data_schema=SCHEMA,
            errors=errors,
            description_placeholders={"login_url": self._login.url, "whoops_url": WHOOPS_URL},
        )
