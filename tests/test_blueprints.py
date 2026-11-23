"""The blueprints are valid Home Assistant automation blueprints."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.blueprint import models
from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA
from homeassistant.util.yaml import load_yaml_dict
import pytest

BLUEPRINTS = sorted((Path(__file__).parents[1] / "blueprints").rglob("*.yaml"))


@pytest.mark.parametrize("path", BLUEPRINTS, ids=lambda p: p.stem)
def test_blueprint_is_valid(path: Path) -> None:
    """The blueprint passes Home Assistant's schema and uses all its inputs."""
    blueprint = models.Blueprint(
        load_yaml_dict(path),
        expected_domain="automation",
        path=str(path),
        schema=BLUEPRINT_SCHEMA,
    )
    assert blueprint.metadata["source_url"].endswith(path.name)
    text = path.read_text(encoding="utf-8")
    for name in blueprint.inputs:
        assert f"!input {name}" in text, name


def test_there_are_blueprints() -> None:
    """The glob above found the blueprints."""
    assert len(BLUEPRINTS) == 4
