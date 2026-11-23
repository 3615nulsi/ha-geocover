# 🚲 Geocover for Home Assistant

[![Release](https://img.shields.io/github/v/release/3615nulsi/ha-geocover)](https://github.com/3615nulsi/ha-geocover/releases)
[![HACS](https://img.shields.io/badge/HACS-custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/3615nulsi/ha-geocover/actions/workflows/validate.yml/badge.svg)](https://github.com/3615nulsi/ha-geocover/actions/workflows/validate.yml)

🇫🇷 *[Version française](README.fr.md)*

Your Decathlon e-bike, in Home Assistant.

If your bike shows up in the **Decathlon Geocover** app, this integration brings it home:
where it is, how much battery is left, how far you can still go, and every ride you have
ever done with it.

> [!WARNING]
> This is a personal project. It is not made, endorsed or supported by Decathlon or
> Conneqtech. It talks to the same servers as the app, which can change without notice.

## ✨ What you get

- 🗺️ **The bike on your map**, with its photo and battery level
- 🔋 **Battery, range and charging state**: know when to plug in, and when to unplug
- 🏁 **A notification at the end of each ride**, with distance, time and climb
- 📅 **A calendar of all your rides**, including the ones from before you installed this
- 📈 **Long-term statistics**: kilometres per week, per month, per year
- 🚨 **Alerts** if the bike moves while you are away, is reported stolen, or its tracker runs flat
- 🧩 **Ready-made blueprints** and a dashboard to copy

## 📦 Installation

You need Home Assistant **2026.3.1** or later and [HACS](https://hacs.xyz).

[![Open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=3615nulsi&repository=ha-geocover&category=integration)

1. Click the button above (or add `https://github.com/3615nulsi/ha-geocover` as a custom
   repository in HACS, category *Integration*).
2. Download **Geocover (Decathlon)** and restart Home Assistant.
3. [![Add the integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=geocover)

### 🔑 Signing in

Decathlon only lets its own app receive the sign-in, so there is one small copy-and-paste step:

1. Open the link shown in the setup dialog and sign in as usual (e-mail code, Apple or Google).
2. You land on a page that says **"Whoops! Looks like something went wrong"**.
   That's normal, it's the page we need.
3. Copy the address of that page and paste it into the dialog. Be quick, the code expires
   within a minute or two.

That's it, there is nothing else to configure. If Decathlon ever ends the session, Home
Assistant will ask you to sign in again the same way.

## 🚴 Supported bikes

Any bike with a GPS tracker that appears in the *Decathlon Geocover* app (formerly
*Decathlon Mobility*). It runs every day on an **Elops LD 920 E**.
Got another model? [Tell me if it works](https://github.com/3615nulsi/ha-geocover/issues/new?template=new_bike.yml).

## 🧭 What shows up in Home Assistant

One device per bike, named like in the app. The everyday entities are on by default; the
more technical ones are created disabled, and you can turn them on from the device page.

<details>
<summary><b>See all the entities</b></summary>

| Entity | What it tells you |
|---|---|
| 📍 *(your bike's name)* | Position on the map, with photo and battery. Works with zones |
| 🔋 Battery | Battery level (%) |
| 🛣️ Range | Estimated range (km) |
| 🔢 Odometer | Total distance (km) |
| 🔌 Charging | On while the bike is plugged in |
| 🏃 Moving | From the last GPS position |
| ⚡ Powered on | Bike switched on |
| 🚴 Ride in progress | A ride is being recorded |
| 🔒 Motor lock | *On* means unlocked |
| 🚨 Reported stolen | As declared in the app |
| 🏁 Last ride, distance, duration | The latest recorded ride |
| 🧮 Recorded rides | How many rides the app knows about |
| 🎉 Ride *(event)* | Fires once at the end of each ride |
| 📅 Rides *(calendar)* | Every ride, with distance and duration |

Disabled by default: speed, last position update, average speed, climb and descent, calories
and CO₂ saved on the last ride, last full charge, rear wheel lock, and three diagnostics
(last connection, GPS tracker battery, bike system).

The tracker also lists the geofences you created in the app (`geofences`) and the ones the
bike is in right now (`in_geofences`).

</details>

## 🔄 How often it updates

The integration adapts to what the bike is doing:

| The bike is… | Checked every |
|---|---|
| 🚴 being ridden | minute |
| 🔌 charging, switched on, or moved in the last 3 hours | 5 minutes |
| 😴 parked for more than 3 hours | 15 minutes |

Your rides are recorded by the bike itself, so nothing is lost when Home Assistant checks less
often: distances, durations and the GPS track are always complete. The only thing that waits
is the live position. After a long rest, it can take up to 15 minutes before Home Assistant
notices the bike is on the move.

## 🎉 Automations

### Blueprints

One click to import, then pick your bike and your phone:

| | |
|---|---|
| 🚨 The bike moves while nobody is home | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fbike_moving_while_away.yaml) |
| 🔋 Battery full, time to unplug | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fbike_charged.yaml) |
| 🔌 Charge reminder the night before a workday | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fcharge_reminder.yaml) |
| 🏁 Ride summary on your phone | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fride_summary.yaml) |

### Dashboard

A full view (battery, range, map, last ride, kilometres per week, ride calendar) is waiting in
[`examples/dashboard.yaml`](examples/dashboard.yaml). Replace `my_bike` with your bike's name
and paste it in.

<details>
<summary><b>Write your own automations</b></summary>

The **Ride** event carries `distance_km`, `duration_min`, `average_speed_kmh`,
`elevation_gain_m`, `elevation_loss_m`, `calories_kcal`, `co2_saved_g`, `start` and `end`:

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
        {{ state_attr('event.my_bike_ride', 'duration_min') }} min 🚴
```

Two actions return data you can use in scripts:

- `geocover.get_rides`: the latest rides, or those of a period
- `geocover.get_locations`: the GPS track between two dates (up to 7 days)

```yaml
action: geocover.get_locations
data:
  device_id: 0123456789abcdef0123456789abcdef
  start: "2026-11-23 06:00:00"
  end: "2026-11-23 09:00:00"
response_variable: track
```

Long-term statistics are named `geocover:bike_<id>_distance` and `geocover:bike_<id>_rides`.
Drop them in a *Statistics graph* card.

</details>

## 🛠️ Repairs

Home Assistant tells you in *Settings → Repairs* when:

- 🚨 the bike is reported stolen in the app
- 🪫 the GPS tracker battery drops below 20 %
- 📡 the tracker hasn't been heard from for 3 days

## 🆘 Troubleshooting

<details>
<summary><b>"Invalid address or expired code"</b></summary>

The code is single-use and only lives a minute or two. The dialog has already made you a new
link: sign in with it, then paste the new address straight away.
</details>

<details>
<summary><b>I never see the "Whoops!" page</b></summary>

Make sure you copy the address of the tab that opened when you clicked the link, *after*
signing in, not the link itself. On a phone with the Geocover app installed, the app may
grab the sign-in; do it on a computer instead.
</details>

<details>
<summary><b>Everything is "unavailable"</b></summary>

The Geocover servers couldn't be reached. The integration tries again at the next update.
The details are in *Settings → System → Logs*.
</details>

<details>
<summary><b>Home Assistant asks me to sign in again</b></summary>

The session was ended on Decathlon's side, for instance after "sign out everywhere" in the
app. Follow the notification and sign in the same way as the first time.
</details>

Still stuck? [Open an issue](https://github.com/3615nulsi/ha-geocover/issues/new?template=bug_report.yml)
and attach the **diagnostics** (device page → ⋮ → *Download diagnostics*). Positions, tokens and
personal details are scrubbed from it.

## ⚠️ Good to know

- 📡 The position is only as fresh as the bike's last report.
- 👀 Read-only: the integration can't lock the bike or sound the alarm.
- 👥 A bike shared between two accounts set up in the same Home Assistant only shows up once.
- 🔧 Decathlon's API isn't public and may change. If something breaks, open an issue.

## 🗑️ Uninstalling

*Settings → Devices & services → Geocover (Decathlon) → ⋮ → Delete*, then remove it from HACS if
you like.

## 🔒 Privacy

The integration only talks to the Geocover servers (`*.conneq.tech`). Your sign-in stays in your
Home Assistant.

## 🤝 Contributing

Bug reports, bike reports and pull requests are welcome, see [CONTRIBUTING.md](CONTRIBUTING.md).
The interface is available in English, French, German, Spanish, Italian, Dutch and Portuguese.
If you're a native speaker and something sounds off, please fix it!

Built on [pygeocover](https://github.com/3615nulsi/pygeocover). MIT licence.
