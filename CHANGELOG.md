# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.5.0] - unreleased

### Added
- **Rides** calendar: every recorded ride, including those before the installation.
- **Long-term statistics**: distance ridden and number of rides, imported from the whole
  ride history (statistics graph cards over months).
- Actions **`geocover.get_rides`** and **`geocover.get_locations`** (GPS track), returning data.
- Blueprints: bike moving while away, bike charged, charge reminder, ride summary.
- Example dashboard (`examples/dashboard.yaml`).
- Translations: German, Spanish, Italian, Dutch, Portuguese.
- Issue templates and `CONTRIBUTING.md`.

## [0.4.0] - 2026-11-23

### Added
- **Adaptive polling**: every minute during a ride, every 5 minutes when the bike is charging,
  powered on or moved recently, every 15 minutes when the bikes have been still for hours.
- **Ride** event entity: `ride_finished`, once per ride, with its summary.
- **Repairs**: bike reported stolen, low GPS tracker battery, tracker silent for 3 days.
- Sensors: recorded rides; last ride end, elevation loss, calories and CO₂ saved, last full
  charge (disabled by default).
- Binary sensors: reported stolen, motor lock, rear wheel lock (disabled by default),
  bike system (diagnostic).
- Tracker attributes `geofences` and `in_geofences` (geofences of the Geocover app).

### Changed
- The latest ride and the number of rides come from the same request.

## [0.3.0] - 2026-11-23

### Added
- Bikes added to the account appear without reloading; the devices of bikes removed from
  the account are deleted (and can be deleted by hand once the bike is gone).
- The map shows the bike's photo and battery level.
- Icons for the entities.
- The reauthentication dialog names the account to sign in to.

### Changed
- Device: the manufacturer comes from the API, the product reference is shown as model ID;
  the bike name is no longer shown as model. A bike renamed in the app is renamed in
  Home Assistant (a name you set yourself is kept).
- Speed shows 0 when the bike is not moving (the last GPS fix may have been sent while riding).
- Created disabled for new installations: speed, last position update, last connection,
  GPS tracker battery, last ride average speed and elevation gain. Existing entities are
  not changed.
- Display precision of range, speed, average speed and elevation gain.
- A bike shared with another account configured in the same Home Assistant is only
  provided once (by its owner's account).
- The sign-in address field is a URL field without autocompletion.
- Complete README, in English and French.

### Internal
- Quality scale self-assessment (`quality_scale.yaml`); translation consistency tests.

## [0.2.0] - 2026-11-23

### Fixed
- When the state, health or latest ride of a bike cannot be fetched, the last known
  values are kept instead of turning to "unknown" (no more gaps in the history nor
  spurious automation triggers). The failure and the recovery are logged once.
- An unexpected answer of the Geocover API no longer crashes the setup dialog or the
  update: it is reported as an error, and position and battery are kept.
- A server incident on the sign-in servers no longer asks for a new sign-in.
- The setup dialog tells network errors ("cannot connect") from unexpected ones.

### Changed
- Fewer requests to the Geocover servers: health is refreshed hourly, and the latest
  ride when a ride ends, when the bike moved, or hourly. The state is still fetched
  every 5 minutes. The requests of one bike are made in parallel.
- When the servers ask to slow down (HTTP 429 / `Retry-After`), the next update waits.
- Entity states are only written when something changed.
- Update errors are translated.
- Diagnostics redact every unknown text field of the API payloads, and include the
  update status and the pygeocover version.
- Requires pygeocover 0.2.0.

### Internal
- Test coverage ≥ 95 % enforced; entity and diagnostics snapshots; JSON fixtures.

## [0.1.2] - 2026-11-23

### Fixed
- The minimum Home Assistant version declared to HACS is now 2026.3.1: older versions
  could not load the integration.

### Changed
- Code, logs and error messages are now in English (the French translation is unchanged).
- Releases now ship a `geocover.zip` archive, which HACS installs.

### Internal
- Tooling: ruff, mypy (strict), pre-commit, coverage, Dependabot.
- CI tests both the minimum supported and the latest Home Assistant.
- Tests split per platform; the pygeocover version is read from the manifest only.

## [0.1.1] - 2026-11-15

### Added
- Integration icon.

## [0.1.0]

- First release.
