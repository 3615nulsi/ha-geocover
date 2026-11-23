"""Actions returning data: rides and GPS track of a bike."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Final

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.util import dt as dt_util
from pygeocover import GeocoverError

from .const import DOMAIN
from .coordinator import GeocoverCoordinator
from .rides import ride_summary

try:
    import probatio as vol
except ImportError:  # Home Assistant < 2026.9 validates with voluptuous
    import voluptuous as vol  # type: ignore[no-redef]

ATTR_DEVICE_ID: Final = "device_id"
ATTR_START: Final = "start"
ATTR_END: Final = "end"
ATTR_LIMIT: Final = "limit"

SERVICE_GET_RIDES: Final = "get_rides"
SERVICE_GET_LOCATIONS: Final = "get_locations"

# A GPS track is requested in one call: keep it reasonable.
MAX_LOCATIONS_PERIOD: Final = timedelta(days=7)

GET_RIDES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_START): cv.datetime,
        vol.Optional(ATTR_END): cv.datetime,
        vol.Optional(ATTR_LIMIT, default=20): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=500)
        ),
    }
)
GET_LOCATIONS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_START): cv.datetime,
        vol.Required(ATTR_END): cv.datetime,
    }
)


def _aware(value: datetime) -> datetime:
    """Interpret a date without time zone in the time zone of Home Assistant."""
    return (
        value if value.tzinfo else value.replace(tzinfo=dt_util.get_default_time_zone())
    )


def _resolve(hass: HomeAssistant, device_id: str) -> tuple[GeocoverCoordinator, int]:
    """Return the coordinator and the bike id of a bike's device."""
    device = dr.async_get(hass).async_get(device_id)
    bike_ids = [
        int(ident)
        for domain, ident in (device.identifiers if device else set())
        if domain == DOMAIN and ident.isdigit()
    ]
    if bike_ids:
        for entry in hass.config_entries.async_loaded_entries(DOMAIN):
            coordinator: GeocoverCoordinator = entry.runtime_data
            if coordinator.data and bike_ids[0] in coordinator.data:
                return coordinator, bike_ids[0]
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="bike_not_found",
        translation_placeholders={"device_id": device_id},
    )


def _period(call: ServiceCall) -> tuple[datetime | None, datetime | None]:
    start = call.data.get(ATTR_START)
    end = call.data.get(ATTR_END)
    start = _aware(start) if start else None
    end = _aware(end) if end else None
    if start and end and end <= start:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="invalid_period"
        )
    return start, end


def _request_failed(err: GeocoverError) -> HomeAssistantError:
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="request_failed",
        translation_placeholders={"error": str(err)},
    )


async def _async_get_rides(call: ServiceCall) -> ServiceResponse:
    """Return the rides of a bike: the latest ones, or those of a period."""
    coordinator, bike_id = _resolve(call.hass, call.data[ATTR_DEVICE_ID])
    start, end = _period(call)
    limit: int = call.data[ATTR_LIMIT]
    data = coordinator.data[bike_id]
    try:
        rides = await coordinator.ride_history(bike_id).async_update(data.ride_count)
    except GeocoverError as err:
        raise _request_failed(err) from err
    selected = [
        ride
        for ride in reversed(rides)  # newest first
        if ride.start_date is not None
        and (start is None or ride.start_date >= start)
        and (end is None or ride.start_date < end)
    ][:limit]
    return {"rides": [ride_summary(ride) for ride in selected]}


async def _async_get_locations(call: ServiceCall) -> ServiceResponse:
    """Return the GPS track of a bike over a period (at most 7 days)."""
    coordinator, bike_id = _resolve(call.hass, call.data[ATTR_DEVICE_ID])
    start, end = _period(call)
    if start is None or end is None:  # both required by the schema
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="invalid_period"
        )
    if end - start > MAX_LOCATIONS_PERIOD:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="period_too_long",
            translation_placeholders={"days": str(MAX_LOCATIONS_PERIOD.days)},
        )
    try:
        locations = await coordinator.client.async_get_locations(bike_id, start, end)
    except GeocoverError as err:
        raise _request_failed(err) from err
    points: list[Any] = [
        {
            "time": loc.date.isoformat() if loc.date else None,
            "latitude": loc.lat,
            "longitude": loc.lon,
            "speed_kmh": loc.speed,
            "moving": loc.is_moving,
        }
        for loc in reversed(locations)  # oldest first
        if loc.lat is not None and loc.lon is not None
    ]
    return {"locations": points}


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the actions of the integration."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_RIDES,
        _async_get_rides,
        schema=GET_RIDES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_LOCATIONS,
        _async_get_locations,
        schema=GET_LOCATIONS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
