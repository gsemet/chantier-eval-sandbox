"""The JSON API: /api/items and /api/items/<id>."""
import json

import pytest

from shelf import store

TYPE = "application/json; charset=utf-8"


def test_the_list_is_empty_on_an_empty_shelf(client):
    r = client.get("/api/items")
    assert r.status == 200
    assert r.headers["content-type"] == TYPE
    assert json.loads(r.text) == []


def test_the_list_holds_every_item_in_id_order(client):
    store.add("First", "https://example.com")
    store.add("Second")
    data = json.loads(client.get("/api/items").text)
    assert [i["id"] for i in data] == [1, 2]
    first, second = data
    assert first["title"] == "First"
    assert first["url"] == "https://example.com"
    assert first["status"] == "to-read"
    assert len(first["added"]) == 10 and first["added"][4] == "-"
    assert isinstance(first["id"], int)
    assert second["url"] is None


def test_one_item(client):
    store.add("First")
    r = client.get("/api/items/1")
    assert r.status == 200
    assert r.headers["content-type"] == TYPE
    assert json.loads(r.text)["title"] == "First"


def test_an_unknown_item_is_a_json_404(client):
    r = client.get("/api/items/9")
    assert r.status == 404
    assert r.headers["content-type"] == TYPE
    assert json.loads(r.text) == {"error": "not found"}


def test_titles_are_not_html_escaped(client):
    title = '<b>Tom & "Jerry"</b>'
    store.add(title)
    assert json.loads(client.get("/api/items/1").text)["title"] == title
    assert json.loads(client.get("/api/items").text)[0]["title"] == title


@pytest.mark.parametrize("path", ["/api/items", "/api/items/1"])
def test_other_methods_get_405(client, path):
    store.add("First")
    r = client.post(path, {})
    assert r.status == 405
    assert r.headers["allow"] == "GET"


def test_the_list_page_links_to_the_json(client):
    assert '<a href="/api/items">JSON</a>' in client.get("/").text
