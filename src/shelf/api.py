"""The JSON representation of the items."""
from __future__ import annotations

import json

JSON = "application/json; charset=utf-8"


def item(entry: dict) -> dict:
    return {
        "id": entry["id"],
        "title": entry["title"],
        "url": entry.get("url") or None,
        "status": entry["status"],
        "added": entry["added"],
    }


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)
