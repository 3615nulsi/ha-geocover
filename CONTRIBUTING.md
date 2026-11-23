# Contributing

Thanks for helping! Bug reports with diagnostics, bike model reports and pull requests
are all welcome.

## Development

```bash
python3.14 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
python scripts/manifest_requirements.py | pip install -r /dev/stdin
pre-commit install
pytest --cov
mypy
```

- The Geocover API is mocked at the HTTP level (`tests/fixtures/*.json`); the real
  [pygeocover](https://github.com/3615nulsi/pygeocover) library is used.
- Code, logs and error messages are in English; user-facing text goes in
  `translations/*.json` (all languages must have the same keys, which a test checks).
- Entity snapshots: `pytest --snapshot-update`, then review the diff.
- Never change an entity `unique_id` or a device identifier without a migration.
- Keep the number of requests to the Geocover servers as low as possible: it is a
  third-party, undocumented service.

## Releases

Bump `version` in `manifest.json`, update `CHANGELOG.md`, merge, then publish a GitHub
release whose tag is `v` + that version (for example `v0.5.0`). The release workflow
checks the version and attaches `geocover.zip`, which HACS installs.
