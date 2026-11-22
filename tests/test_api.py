import json

import pytest


def _add(client, title="A book", url=""):
    client.post("/items", {"title": title, "url": url})


def test_the_list_is_a_json_array_in_id_order(client):
    _add(client, "First", "https://example.com")
    _add(client, "Second")
    response = client.get("/api/items")
    assert response.status == 200
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    data = json.loads(response.text)
    assert [i["id"] for i in data] == [1, 2]
    assert data[0]["title"] == "First"
    assert data[0]["url"] == "https://example.com"
    assert data[0]["status"] == "to-read"
    assert len(data[0]["added"]) == 10 and data[0]["added"][4] == "-"


def test_an_empty_shelf_is_an_empty_array(client):
    assert json.loads(client.get("/api/items").text) == []


def test_an_item_without_a_link_has_a_null_url(client):
    _add(client)
    assert json.loads(client.get("/api/items").text)[0]["url"] is None


def test_one_item_is_a_json_object(client):
    _add(client, "First")
    _add(client, "Second")
    response = client.get("/api/items/2")
    assert response.status == 200
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert json.loads(response.text)["title"] == "Second"


def test_an_unknown_item_is_a_json_404(client):
    response = client.get("/api/items/9")
    assert response.status == 404
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert json.loads(response.text) == {"error": "not found"}


def test_titles_are_not_html_escaped(client):
    _add(client, "<b>Tom & Jerry</b>")
    assert json.loads(client.get("/api/items").text)[0]["title"] == "<b>Tom & Jerry</b>"
    assert json.loads(client.get("/api/items/1").text)["title"] == "<b>Tom & Jerry</b>"


@pytest.mark.parametrize("path", ["/api/items", "/api/items/1"])
def test_other_methods_get_405(client, path):
    _add(client)
    assert client.post(path, {}).status == 405


def test_the_list_page_links_to_the_json(client):
    assert '<a href="/api/items">JSON</a>' in client.get("/").text
