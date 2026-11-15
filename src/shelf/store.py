"""The items, kept in a JSON file: the path in SHELF_DATA, else shelf.json here."""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

from shelf.models import DEFAULT_STATUS


def data_path() -> Path:
    return Path(os.environ.get("SHELF_DATA") or "shelf.json")


def _read() -> dict:
    """The file as {"next_id", "items"}; an older file is a bare list of items."""
    path = data_path()
    if not path.exists():
        return {"next_id": 1, "items": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        data = {"items": data}
    items = data["items"]
    floor = max((i["id"] for i in items), default=0) + 1
    return {"next_id": max(data.get("next_id", 1), floor), "items": items}


def _write(next_id: int, items: list[dict]) -> None:
    path = data_path()
    temporary = path.with_name(path.name + ".tmp")
    body = json.dumps({"next_id": next_id, "items": items}, indent=2)
    temporary.write_text(body + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load() -> list[dict]:
    return _read()["items"]


def add(title: str, url: str = "") -> dict:
    data = _read()
    item = {
        "id": data["next_id"],
        "title": title,
        "url": url,
        "status": DEFAULT_STATUS,
        "added": datetime.date.today().isoformat(),
    }
    _write(data["next_id"] + 1, [*data["items"], item])
    return item


def get(item_id: int) -> dict | None:
    return next((i for i in load() if i["id"] == item_id), None)


def set_status(item_id: int, status: str) -> dict | None:
    data = _read()
    item = next((i for i in data["items"] if i["id"] == item_id), None)
    if item is None:
        return None
    item["status"] = status
    _write(data["next_id"], data["items"])
    return item


def delete(item_id: int) -> bool:
    data = _read()
    kept = [i for i in data["items"] if i["id"] != item_id]
    if len(kept) == len(data["items"]):
        return False
    _write(data["next_id"], kept)
    return True
