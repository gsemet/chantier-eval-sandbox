import json

import pytest

JSON = "application/json; charset=utf-8"


def test_the_list_is_a_json_array_in_id_order(client):
    client.post("/items", {"title": "One", "url": "https://example.com"})
    client.post("/items", {"title": "Two", "url": ""})
    response = client.get("/api/items")
    assert response.status == 200
    assert response.headers["content-type"] == JSON
    data = json.loads(response.text)
    assert [i["id"] for i in data] == [1, 2]
    assert data[0]["title"] == "One"
    assert data[0]["url"] == "https://example.com"
    assert data[0]["status"] == "to-read"
    assert len(data[0]["added"]) == 10


def test_an_empty_shelf_is_an_empty_array(client):
    assert json.loads(client.get("/api/items").text) == []


def test_an_item_without_a_link_has_a_null_url(client):
    client.post("/items", {"title": "One", "url": ""})
    assert json.loads(client.get("/api/items/1").text)["url"] is None


def test_one_item(client):
    client.post("/items", {"title": "One", "url": ""})
    response = client.get("/api/items/1")
    assert response.status == 200
    assert response.headers["content-type"] == JSON
    assert json.loads(response.text)["id"] == 1


def test_an_unknown_item_is_a_json_404(client):
    response = client.get("/api/items/9")
    assert response.status == 404
    assert response.headers["content-type"] == JSON
    assert json.loads(response.text) == {"error": "not found"}


def test_titles_are_not_html_escaped(client):
    client.post("/items", {"title": "<b>A & B</b>", "url": ""})
    assert json.loads(client.get("/api/items").text)[0]["title"] == "<b>A & B</b>"
    assert json.loads(client.get("/api/items/1").text)["title"] == "<b>A & B</b>"


@pytest.mark.parametrize("path", ["/api/items", "/api/items/1"])
@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_other_methods_get_405(client, path, method):
    client.post("/items", {"title": "One", "url": ""})
    assert client._call(method, path).status == 405


def test_the_list_page_links_to_the_json(client):
    assert '<a href="/api/items">JSON</a>' in client.get("/").text
