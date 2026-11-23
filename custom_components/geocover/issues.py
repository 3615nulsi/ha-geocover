"""Repair issues: what needs the user's attention on a bike."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import timedelta
from typing import TYPE_CHECKING, Final

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import BikeData

# The GPS tracker has its own battery, which is not charged with the bike's.
TRACKER_BATTERY_LOW: Final = 20
TRACKER_BATTERY_OK: Final = 25  # hysteresis: no flapping around the threshold
NO_CONNECTION_AFTER: Final = timedelta(days=3)

# kind of issue -> severity
ISSUE_KINDS: Final = {
    "bike_stolen": ir.IssueSeverity.ERROR,
    "no_connection": ir.IssueSeverity.WARNING,
    "tracker_battery_low": ir.IssueSeverity.WARNING,
}


def issue_id(kind: str, bike_id: int) -> str:
    """Return the id of an issue of a bike."""
    return f"{kind}_{bike_id}"


@callback
def async_update_issues(hass: HomeAssistant, data: Mapping[int, BikeData]) -> None:
    """Create or delete the repair issues of every bike."""
    now = dt_util.utcnow()
    for bike_id, bike_data in data.items():
        bike = bike_data.bike
        placeholders = {"bike": bike.name}

        _set_issue(
            hass,
            "bike_stolen",
            bike_id,
            bike.is_stolen,
            placeholders,
        )

        health = bike_data.health
        if health is None:
            continue  # unknown: leave the issues as they are
        if (level := health.gps_battery) is not None:
            if level < TRACKER_BATTERY_LOW:
                _set_issue(
                    hass,
                    "tracker_battery_low",
                    bike_id,
                    True,
                    {**placeholders, "level": str(level)},
                )
            elif level >= TRACKER_BATTERY_OK:
                async_delete_bike_issues(hass, bike_id, ("tracker_battery_low",))
        if (last := health.last_connection) is not None:
            silent = now - last
            _set_issue(
                hass,
                "no_connection",
                bike_id,
                silent >= NO_CONNECTION_AFTER,
                {**placeholders, "days": str(silent.days)},
            )


@callback
def async_delete_bike_issues(
    hass: HomeAssistant, bike_id: int, kinds: Iterable[str] = ISSUE_KINDS
) -> None:
    """Delete the issues of a bike."""
    for kind in kinds:
        ir.async_delete_issue(hass, DOMAIN, issue_id(kind, bike_id))


def _set_issue(
    hass: HomeAssistant,
    kind: str,
    bike_id: int,
    active: bool,
    placeholders: dict[str, str],
) -> None:
    if not active:
        async_delete_bike_issues(hass, bike_id, (kind,))
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id(kind, bike_id),
        is_fixable=False,
        severity=ISSUE_KINDS[kind],
        translation_key=kind,
        translation_placeholders=placeholders,
    )
