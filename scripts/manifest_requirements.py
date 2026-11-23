"""Print the requirements declared in manifest.json, one per line (single source of truth)."""

import json
from pathlib import Path

MANIFEST = (
    Path(__file__).parents[1] / "custom_components" / "geocover" / "manifest.json"
)

print("\n".join(json.loads(MANIFEST.read_text(encoding="utf-8"))["requirements"]))  # noqa: T201
