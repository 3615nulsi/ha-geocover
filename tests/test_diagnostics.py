"""Tests for the Geocover diagnostics."""

from __future__ import annotations

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant
import pytest
from syrupy.assertion import SnapshotAssertion

from custom_components.geocover.diagnostics import (
    async_get_config_entry_diagnostics,
    redact,
)

from .conftest import SetupIntegration, load_fixture


async def test_diagnostics(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
    snapshot: SnapshotAssertion,
) -> None:
    """Diagnostics keep the structure of the payloads but no personal data."""
    bikes = load_fixture("bikes")
    # Fields the integration does not know about must not leak either.
    bikes[0]["owner_phone"] = "+33612345678"
    bikes[0]["bike_image_url"] = "https://img.example/bike.jpg"
    bikes[0]["manufacturer"] = "decathlon"
    entry = await setup_integration(payloads={"bike": bikes})

    diag = await async_get_config_entry_diagnostics(hass, entry)

    text = str(diag)
    for secret in (
        "at_0",
        "rt_0",
        "48.85",
        "000000000000000",
        "F1",
        "Vélo test",
        "+33612345678",
        "img.example",
    ):
        assert secret not in text, secret
    bike = diag["bikes"][1]["bike"]
    assert bike["battery_percentage"] == 65
    assert bike["manufacturer"] == "decathlon"
    assert diag["coordinator"]["last_update_success"] is True
    assert diag == snapshot


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-09-28T16:38:00+0000", "2026-09-28T16:38:00+0000"),
        ("2026-09-28", "2026-09-28"),
        ("99%", "99%"),
        ("true", "true"),
        ("12.5", "12.5"),
        ("Jean Dupont", REDACTED),
        ("0612345678", REDACTED),
        ("https://example.com", REDACTED),
    ],
)
def test_redact_strings(value: str, expected: str) -> None:
    """Only harmless-looking strings are kept under unknown keys."""
    assert redact({"value": value}) == {"value": expected}


def test_redact_keys() -> None:
    """Sensitive keys are redacted whatever their type; safe keys are kept."""
    data = {
        "lat": 48.85,
        "imei": 123,
        "name": "",
        "manufacturer": "decathlon",
        "items": [{"email": "a@b.c", "count": 3}],
    }
    assert redact(data) == {
        "lat": REDACTED,
        "imei": REDACTED,
        "name": "",
        "manufacturer": "decathlon",
        "items": [{"email": REDACTED, "count": 3}],
    }
