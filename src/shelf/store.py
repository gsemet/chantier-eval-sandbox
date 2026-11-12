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
    """The items and the next id. An older file is a bare list: its next id is the highest + 1."""
    path = data_path()
    if not path.exists():
        return [], 1
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data, max((i["id"] for i in data), default=0) + 1
    items = data["items"]
    return items, max(data["next_id"], max((i["id"] for i in items), default=0) + 1)


def load() -> list[dict]:
    return _read()[0]


def save(items: list[dict], next_id: int | None = None) -> None:
    if next_id is None:
        next_id = _read()[1]
    next_id = max(next_id, max((i["id"] for i in items), default=0) + 1)
    path = data_path()
    temporary = path.with_name(path.name + ".tmp")
    payload = {"next_id": next_id, "items": items}
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def add(title: str, url: str = "") -> dict:
    items, next_id = _read()
    item = {
        "id": next_id,
        "title": title,
        "url": url,
        "status": DEFAULT_STATUS,
        "added": datetime.date.today().isoformat(),
    }
    save([*items, item], next_id + 1)
    return item


def delete(item_id: int) -> bool:
    items, next_id = _read()
    kept = [i for i in items if i["id"] != item_id]
    if len(kept) == len(items):
        return False
    save(kept, next_id)
    return True


def get(item_id: int) -> dict | None:
    return next((i for i in load() if i["id"] == item_id), None)


def set_status(item_id: int, status: str) -> dict | None:
    items = load()
    item = next((i for i in items if i["id"] == item_id), None)
    if item is None:
        return None
    item["status"] = status
    save(items)
    return item


def update(item_id: int, title: str, url: str) -> dict | None:
    items = load()
    item = next((i for i in items if i["id"] == item_id), None)
    if item is None:
        return None
    item["title"] = title
    item["url"] = url
    save(items)
    return item
