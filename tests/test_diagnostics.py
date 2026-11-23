"""Tests for the Geocover diagnostics."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.geocover.diagnostics import async_get_config_entry_diagnostics

from .conftest import SetupIntegration


async def test_diagnostics_are_redacted(
    hass: HomeAssistant, setup_integration: SetupIntegration
) -> None:
    """Tokens, position, IMEI and frame number never appear in diagnostics."""
    entry = await setup_integration()
    diag = await async_get_config_entry_diagnostics(hass, entry)

    text = str(diag)
    for secret in ("at_0", "rt_0", "48.85", "000000000000000", "F1"):
        assert secret not in text
    assert diag["bikes"][1]["bike"]["battery_percentage"] == 65
