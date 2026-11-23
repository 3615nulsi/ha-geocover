"""Consistency of the translation and icon files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "geocover"
LANGUAGES = sorted(p.stem for p in (INTEGRATION / "translations").glob("*.json"))


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _keys(data: Any, prefix: str = "") -> set[str]:
    """Return the paths of all the leaves of a translation file."""
    if not isinstance(data, dict):
        return {prefix}
    keys: set[str] = set()
    for key, value in data.items():
        keys |= _keys(value, f"{prefix}.{key}" if prefix else key)
    return keys


def test_strings_is_english() -> None:
    """strings.json (read by hassfest) and translations/en.json are the same file."""
    assert _load(INTEGRATION / "strings.json") == _load(
        INTEGRATION / "translations" / "en.json"
    )


@pytest.mark.parametrize("language", LANGUAGES)
def test_languages_have_the_same_keys(language: str) -> None:
    """Every language translates exactly the same strings as English."""
    english = _keys(_load(INTEGRATION / "translations" / "en.json"))
    translated = _keys(_load(INTEGRATION / "translations" / f"{language}.json"))
    assert translated == english


def test_icons_match_translation_keys() -> None:
    """Every icon is attached to an existing translation key, or the tracker."""
    english = _load(INTEGRATION / "translations" / "en.json")["entity"]
    for platform, entities in _load(INTEGRATION / "icons.json")["entity"].items():
        for key in entities:
            if platform == "device_tracker":
                continue  # the tracker has no name of its own: it uses the bike's
            assert key in english.get(platform, {}), f"{platform}.{key}"
