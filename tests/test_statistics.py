"""Tests for the long-term statistics of the rides."""

from __future__ import annotations

from homeassistant.components.recorder import Recorder, get_instance
from homeassistant.components.recorder.statistics import get_last_statistics
from homeassistant.core import HomeAssistant
from pygeocover import Ride
import pytest
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.geocover.ride_statistics import hourly_sums, statistic_id

from .conftest import SetupIntegration, load_fixture


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    recorder_mock: Recorder, enable_custom_integrations: None
) -> None:
    """Set the recorder up before Home Assistant, then enable the integration."""


def _ride(ride_id: int, start: str, meters: int) -> Ride:
    raw = load_fixture("rides")["data"][0]
    raw.update(id=ride_id, start_date=start, distance_traveled=meters)
    return Ride.from_dict(raw)


def test_hourly_sums() -> None:
    """Rides are summed per hour of start, cumulated over time."""
    sums = hourly_sums(
        [
            _ride(1, "2026-09-27T08:10:00+0000", 5000),
            _ride(2, "2026-09-27T08:50:00+0000", 2000),
            _ride(3, "2026-09-28T17:05:00+0000", 4000),
        ]
    )
    assert [(s["start"].hour, s["state"], s["sum"]) for s in sums["distance"]] == [
        (8, 7.0, 7.0),
        (17, 4.0, 11.0),
    ]
    assert [s["sum"] for s in sums["rides"]] == [2, 3]


async def test_statistics_imported(
    hass: HomeAssistant,
    setup_integration: SetupIntegration,
) -> None:
    """The ride history is imported as long-term statistics."""
    await setup_integration()
    await hass.async_block_till_done(wait_background_tasks=True)
    await async_wait_recording_done(hass)

    for kind, expected in (("distance", 7.37), ("rides", 1)):
        stats = await get_instance(hass).async_add_executor_job(
            get_last_statistics, hass, 1, statistic_id(1, kind), True, {"sum"}
        )
        assert stats[statistic_id(1, kind)][0]["sum"] == expected
