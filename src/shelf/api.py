"""The JSON view of the items: pure functions, the routing stays in app.py."""
from __future__ import annotations

import json

JSON = "application/json; charset=utf-8"


def _public(entry: dict) -> dict:
    return {
        "id": entry["id"],
        "title": entry["title"],
        "url": entry.get("url") or None,
        "status": entry["status"],
        "added": entry["added"],
    }


def items(entries: list[dict]) -> str:
    return json.dumps([_public(e) for e in sorted(entries, key=lambda e: e["id"])], ensure_ascii=False)


def item(entry: dict) -> str:
    return json.dumps(_public(entry), ensure_ascii=False)


def not_found() -> str:
    return json.dumps({"error": "not found"})
