# Geocover (Decathlon) for Home Assistant

[![Release](https://img.shields.io/github/v/release/3615nulsi/ha-geocover)](https://github.com/3615nulsi/ha-geocover/releases)
[![HACS](https://img.shields.io/badge/HACS-custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/3615nulsi/ha-geocover/actions/workflows/validate.yml/badge.svg)](https://github.com/3615nulsi/ha-geocover/actions/workflows/validate.yml)

*[Version française](README.fr.md)*

Unofficial Home Assistant integration for **Decathlon connected e-bikes** that use the
*Decathlon Geocover* app: GPS position on the map, battery, range, odometer, charging state
and latest ride.

> ⚠️ **Unofficial project, not affiliated with, endorsed or supported by Decathlon or Conneqtech.**
> It uses the same cloud API as the mobile app, which may change or stop working at any time.
> Use at your own risk and in accordance with the service's terms.

## What you can do with it

- See your bike on the Home Assistant map, with its photo and battery level.
- Be notified when the bike moves while you are away, or when charging is complete.
- Get a reminder to charge when the range is low the evening before a working day.
- Keep a history of the battery, range and rides in Home Assistant.

## Supported bikes

Decathlon e-bikes with a GPS tracker that appear in the *Decathlon Geocover* app (previously
*Decathlon Mobility*). Tested with an **Elops LD 920 E**. Other bikes of the same app should work;
please open an issue with your diagnostics if something is missing.

## Installation

Requires Home Assistant **2026.3.1** or later and [HACS](https://hacs.xyz).

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=3615nulsi&repository=ha-geocover&category=integration)

Or by hand: HACS → ⋮ → *Custom repositories* → `https://github.com/3615nulsi/ha-geocover`,
category *Integration*. Then:

1. Install **Geocover (Decathlon)** in HACS and restart Home Assistant.
2. [![Add the integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=geocover)
   or *Settings → Devices & services → Add integration → Geocover (Decathlon)*.
3. Sign in (see below).

### Sign-in

The Geocover app only accepts a sign-in redirect to itself, so the setup uses a copy/paste step:

1. Click the link shown in the dialog and sign in to your Decathlon account
   (e-mail + code, or Apple/Google).
2. You end up on a page saying **"Whoops! Looks like something went wrong"**: *this is expected*.
3. Copy the full address of that page (`https://login.ids.conneq.tech/redirect?code=…`) and
   paste it in the dialog, quickly: the code expires after a short time.

There is no other setting. If the session expires, Home Assistant shows a notification and asks
you to sign in again the same way.

## Entities

One device per bike, named after the bike in the app.

| Entity | Type | Notes |
|---|---|---|
| *(bike name)* | Device tracker | GPS position, works with zones; shows the bike's photo and battery on the map |
| Battery | Sensor | % |
| Range | Sensor | km |
| Odometer | Sensor | km |
| Last ride | Sensor | start of the latest recorded ride |
| Last ride distance | Sensor | km |
| Last ride duration | Sensor | min |
| Charging | Binary sensor | |
| Moving | Binary sensor | from the last GPS fix |
| Powered on | Binary sensor | |
| Ride in progress | Binary sensor | |
| Recorded rides | Sensor | number of rides in the app |
| Reported stolen | Binary sensor | as declared in the app |
| Motor lock | Binary sensor | *on* means unlocked |
| Ride | Event | fired when a ride is finished, with its summary |
| Rides | Calendar | every recorded ride, with distance and duration |
| Speed | Sensor | *disabled by default*; 0 when the bike is not moving |
| Last position update | Sensor | *disabled by default* |
| Last ride average speed | Sensor | *disabled by default* |
| Last ride elevation gain | Sensor | *disabled by default* |
| Last ride end, elevation loss, calories, CO₂ saved | Sensors | *disabled by default* |
| Last full charge | Sensor | *disabled by default* |
| Rear wheel lock | Binary sensor | *disabled by default*, not fitted to every bike |
| Bike system | Binary sensor | *diagnostic*; *on* when the bike reports a problem |
| Last connection | Sensor | *diagnostic, disabled by default* |
| GPS tracker battery | Sensor | *diagnostic, disabled by default* |

Entities disabled by default can be enabled from the device page.

The tracker also has the attributes `geofences` (the active geofences defined in the
Geocover app) and `in_geofences` (those the bike is in).

### Ride finished event

The **Ride** event entity fires `ride_finished` once per new ride, when it is over, with
`distance_km`, `duration_min`, `average_speed_kmh`, `elevation_gain_m`, `elevation_loss_m`,
`calories_kcal`, `co2_saved_g`, `start` and `end`.

### Ride calendar

The **Rides** calendar shows every recorded ride ("7.4 km · 24 min"), including those
recorded before the integration was installed. The history is read from the Geocover
servers the first time it is needed, then only new rides are fetched.

### Long-term statistics

The distance ridden and the number of rides are imported as long-term statistics
(`geocover:bike_<id>_distance`, `geocover:bike_<id>_rides`), from the very first ride.
Use them in a *Statistics graph* card, for example the distance per week or per month.

### Actions

| Action | Returns |
|---|---|
| `geocover.get_rides` | the rides of a bike: the latest ones (`limit`), or those started between `start` and `end` |
| `geocover.get_locations` | the GPS track of a bike between `start` and `end` (7 days at most) |

```yaml
action: geocover.get_locations
data:
  device_id: 0123456789abcdef0123456789abcdef
  start: "2026-11-23 06:00:00"
  end: "2026-11-23 09:00:00"
response_variable: track
```

### Repairs

*Settings → Repairs* shows when a bike is reported stolen, when its GPS tracker battery is low
(below 20 %), or when the tracker has not connected for 3 days.

## Data updates

The bike list (position, battery, odometer) and the bike state (charging, range) are fetched
at an **adaptive interval**:

- **every minute** during a ride (or while the last GPS fix says the bike is moving);
- **every 5 minutes** when the bike is charging, powered on, or moved in the last 3 hours;
- **every 15 minutes** when every bike has been still for more than 3 hours.

So a ride is followed closely, while the service is spared the rest of the time. The flip side:
when the bike has been asleep for hours, a movement can take up to 15 minutes to be noticed.

The tracker health is refreshed hourly; the latest ride when a ride ends,
when the bike moved, or hourly. The bike only reports its position when it moves or connects,
so polling faster would not bring fresher data and would put needless load on the service.
If a secondary request fails, the last known values are kept.

Bikes added to or removed from the account appear or disappear on their own.

## Blueprints and dashboard

| Blueprint | Import |
|---|---|
| Bike moving while nobody is home | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fbike_moving_while_away.yaml) |
| Bike charged: unplug it | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fbike_charged.yaml) |
| Charge reminder the evening before a working day | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fcharge_reminder.yaml) |
| Summary of each ride | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fride_summary.yaml) |

A ready-made dashboard view (battery, range, map, last ride, distance per week, ride
calendar) is in [`examples/dashboard.yaml`](examples/dashboard.yaml).

## Automation examples

Send the summary of each ride:

```yaml
triggers:
  - trigger: state
    entity_id: event.my_bike_ride
    not_from: unavailable
conditions:
  - condition: state
    entity_id: event.my_bike_ride
    attribute: event_type
    state: ride_finished
actions:
  - action: notify.mobile_app_my_phone
    data:
      message: >-
        {{ state_attr('event.my_bike_ride', 'distance_km') }} km in
        {{ state_attr('event.my_bike_ride', 'duration_min') }} min

Notify when the bike moves while nobody is home:

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.my_bike_moving
    to: "on"
conditions:
  - condition: state
    entity_id: zone.home
    state: "0"
actions:
  - action: notify.mobile_app_my_phone
    data:
      message: "The bike is moving!"
```

Notify when charging is complete:

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.my_bike_charging
    from: "on"
    to: "off"
conditions:
  - condition: numeric_state
    entity_id: sensor.my_bike_battery
    above: 95
actions:
  - action: notify.mobile_app_my_phone
    data:
      message: "The bike is charged, you can unplug it."
```

## Known limitations

- The position is only as fresh as the bike's last report (when it moves or connects).
- No commands (lock, alarm): the integration is read-only.
- A bike shared between two accounts configured in the same Home Assistant is only shown once,
  by the owner's account when it is configured.
- The Decathlon API is undocumented and may change without notice.

## Troubleshooting

- **"Invalid address or expired code"**: the code is single-use and expires quickly. The dialog
  generates a new link: sign in again with it and paste the new address right away.
- **The sign-in page does not end on "Whoops!"**: make sure you copy the address from the
  browser tab opened by the link, after signing in, not the link itself.
- **Entities unavailable**: the Geocover servers could not be reached; the integration retries
  at the next update. Check the logs for details.
- **Sign-in asked again**: the session was revoked (for example after signing out everywhere in
  the app). Follow the notification to sign in again.
- When opening an issue, attach the **diagnostics** (device page → ⋮ → *Download diagnostics*):
  positions, tokens, identifiers and unknown text fields are redacted.

## Removal

1. *Settings → Devices & services → Geocover (Decathlon) → ⋮ → Delete*.
2. Optionally uninstall it from HACS and restart Home Assistant.

## Privacy

The integration only talks to the Geocover servers (`*.conneq.tech`). Your tokens are stored
in your Home Assistant only.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Translations: English, French, German, Spanish,
Italian, Dutch and Portuguese; corrections by native speakers are welcome.

## Credits

Built on [`pygeocover`](https://github.com/3615nulsi/pygeocover). Licence: MIT.
