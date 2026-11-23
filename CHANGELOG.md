# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.2] - unreleased

### Fixed
- The minimum Home Assistant version declared to HACS is now 2026.3.0: older versions
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
