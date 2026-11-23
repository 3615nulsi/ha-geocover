"""History of the rides of a bike, fetched on demand and kept in memory.

Used by the calendar, the actions and the long-term statistics. The whole history
is fetched once (paginated), then only the newest page when new rides appear.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Final

from pygeocover import GeocoverClient, Ride

PAGE_SIZE: Final = 50
# Safety net against an endless pagination.
MAX_PAGES: Final = 200
_EPOCH: Final = datetime.fromtimestamp(0, UTC)


class RideHistory:
    """Rides of one bike, newest first."""

    def __init__(self, client: GeocoverClient, bike_id: int) -> None:
        """Initialize an empty history."""
        self._client = client
        self._bike_id = bike_id
        self._rides: dict[int, Ride] = {}
        self._complete = False
        self._lock = asyncio.Lock()

    @property
    def rides(self) -> list[Ride]:
        """Return the known rides, oldest first."""
        return sorted(
            (r for r in self._rides.values() if r.start_date is not None),
            key=lambda r: r.start_date or _EPOCH,
        )

    async def async_update(self, total: int | None = None) -> list[Ride]:
        """Fetch what is missing, and return the rides, oldest first.

        `total` is the number of rides known by the coordinator: when the history
        already has as many, no request is made.
        """
        async with self._lock:
            if not self._complete:
                await self._async_fetch(stop_at_known=False)
                self._complete = True
            elif total is None or total > len(self._rides):
                await self._async_fetch(stop_at_known=True)
        return self.rides

    async def async_between(
        self, start: datetime, end: datetime, total: int | None = None
    ) -> list[Ride]:
        """Return the rides that started in [start, end), oldest first."""
        return [
            ride
            for ride in await self.async_update(total)
            if ride.start_date is not None and start <= ride.start_date < end
        ]

    async def _async_fetch(self, *, stop_at_known: bool) -> None:
        """Fetch pages, newest first, until the end (or a known ride)."""
        for page_number in range(MAX_PAGES):
            page = await self._client.async_get_rides(
                self._bike_id, limit=PAGE_SIZE, offset=page_number * PAGE_SIZE
            )
            known = any(ride.id in self._rides for ride in page.rides)
            self._rides.update((ride.id, ride) for ride in page.rides)
            if (
                len(page.rides) < PAGE_SIZE
                or (page_number + 1) * PAGE_SIZE >= page.total
                or (stop_at_known and known)
            ):
                return


def ride_summary(ride: Ride) -> dict[str, Any]:
    """Return the attributes of a ride finished event."""
    return {
        "ride_id": ride.id,
        "start": ride.start_date.isoformat() if ride.start_date else None,
        "end": ride.end_date.isoformat() if ride.end_date else None,
        "distance_km": ride.distance_km,
        "duration_min": round(ride.active_time_s / 60)
        if ride.active_time_s is not None
        else None,
        "average_speed_kmh": ride.avg_speed,
        "elevation_gain_m": ride.elevation_up,
        "elevation_loss_m": ride.elevation_down,
        "calories_kcal": ride.calories,
        "co2_saved_g": ride.co2,
    }
