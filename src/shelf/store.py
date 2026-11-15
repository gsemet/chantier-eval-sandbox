"""The items, kept in a JSON file: the path in SHELF_DATA, else shelf.json here."""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

from shelf.models import DEFAULT_STATUS


def data_path() -> Path:
    return Path(os.environ.get("SHELF_DATA") or "shelf.json")


def _read() -> tuple[list[dict], int]:
    """Return the items and the next id. A legacy file (a bare list) derives the next id."""
    path = data_path()
    if not path.exists():
        return [], 1
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data, max((i["id"] for i in data), default=0) + 1
    items = data["items"]
    return items, max(data["next_id"], max((i["id"] for i in items), default=0) + 1)


def _write(items: list[dict], next_id: int) -> None:
    path = data_path()
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps({"next_id": next_id, "items": items}, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load() -> list[dict]:
    return _read()[0]


def add(title: str, url: str = "") -> dict:
    items, next_id = _read()
    item = {
        "id": next_id,
        "title": title,
        "url": url,
        "status": DEFAULT_STATUS,
        "added": datetime.date.today().isoformat(),
    }
    _write([*items, item], next_id + 1)
    return item


def delete(item_id: int) -> bool:
    items, next_id = _read()
    kept = [i for i in items if i["id"] != item_id]
    if len(kept) == len(items):
        return False
    _write(kept, next_id)
    return True


def get(item_id: int) -> dict | None:
    return next((i for i in load() if i["id"] == item_id), None)


def update(item_id: int, title: str, url: str) -> dict | None:
    items, next_id = _read()
    item = next((i for i in items if i["id"] == item_id), None)
    if item is None:
        return None
    item["title"] = title
    item["url"] = url
    _write(items, next_id)
    return item


def set_status(item_id: int, status: str) -> dict | None:
    items, next_id = _read()
    item = next((i for i in items if i["id"] == item_id), None)
    if item is None:
        return None
    item["status"] = status
    _write(items, next_id)
    return item
