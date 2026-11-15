import json

from shelf import store


def test_the_list_is_a_json_array_in_id_order(client):
    store.add("Dune", "https://example.com/dune")
    store.add("Emma")
    response = client.get("/api/items")
    assert response.status == 200
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    data = json.loads(response.text)
    assert [i["id"] for i in data] == [1, 2]
    assert data[0] == {"id": 1, "title": "Dune", "url": "https://example.com/dune",
                       "status": "to-read", "added": store.get(1)["added"]}


def test_an_empty_shelf_is_an_empty_array(client):
    assert json.loads(client.get("/api/items").text) == []


def test_an_item_without_a_link_has_a_null_url(client):
    store.add("Emma")
    assert json.loads(client.get("/api/items/1").text)["url"] is None


def test_one_item_is_an_object(client):
    store.add("Dune")
    response = client.get("/api/items/1")
    assert response.status == 200
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    data = json.loads(response.text)
    assert (data["id"], data["title"], data["status"]) == (1, "Dune", "to-read")


def test_an_unknown_item_is_a_json_404(client):
    response = client.get("/api/items/9")
    assert response.status == 404
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert json.loads(response.text) == {"error": "not found"}


def test_other_methods_get_405(client):
    store.add("Dune")
    assert client.post("/api/items", {}).status == 405
    assert client.post("/api/items/1", {}).status == 405
    assert client._call("DELETE", "/api/items/1").status == 405


def test_titles_are_not_html_escaped(client):
    store.add("Tom & <Jerry>")
    assert json.loads(client.get("/api/items/1").text)["title"] == "Tom & <Jerry>"
    assert "Tom & <Jerry>" in client.get("/api/items").text


def test_the_list_page_links_to_the_json(client):
    assert '<a href="/api/items">JSON</a>' in client.get("/").text
