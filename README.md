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
| Speed | Sensor | *disabled by default*; 0 when the bike is not moving |
| Last position update | Sensor | *disabled by default* |
| Last ride average speed | Sensor | *disabled by default* |
| Last ride elevation gain | Sensor | *disabled by default* |
| Last connection | Sensor | *diagnostic, disabled by default* |
| GPS tracker battery | Sensor | *diagnostic, disabled by default* |

Entities disabled by default can be enabled from the device page.

## Data updates

The bike list (position, battery, odometer) and the bike state (charging, range) are fetched
**every 5 minutes**. The tracker health is refreshed hourly; the latest ride when a ride ends,
when the bike moved, or hourly. The bike only reports its position when it moves or connects,
so polling faster would not bring fresher data and would put needless load on the service.
If a secondary request fails, the last known values are kept.

Bikes added to or removed from the account appear or disappear on their own.

## Automation examples

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
  every 5 minutes. Check the logs for details.
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

## Credits

Built on [`pygeocover`](https://github.com/3615nulsi/pygeocover). Licence: MIT.
