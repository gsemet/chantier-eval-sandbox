import pytest

from shelf.models import validate_new


def test_a_valid_item_is_trimmed():
    clean, error = validate_new("  A book  ", " https://example.com ")
    assert error is None
    assert clean == {"title": "A book", "url": "https://example.com"}


def test_the_link_is_optional():
    assert validate_new("A book", "")[1] is None


@pytest.mark.parametrize("title", ["", "   "])
def test_the_title_is_required(title):
    assert "required" in validate_new(title, "")[1]


def test_the_title_has_at_most_200_characters():
    assert validate_new("x" * 200, "")[1] is None
    assert "200" in validate_new("x" * 201, "")[1]


@pytest.mark.parametrize("url", ["example.com", "ftp://example.com", "javascript:alert(1)"])
def test_the_link_starts_with_http_or_https(url):
    assert "http" in validate_new("A book", url)[1]


def _add(client, title="A book", url="https://example.com"):
    client.post("/items", {"title": title, "url": url})


def test_the_edit_page_holds_the_current_values(client):
    _add(client, 'A "quoted" <b>', "https://example.com/?a=1&b=2")
    page = client.get("/items/1/edit")
    assert page.status == 200
    assert '<form method="post" action="/items/1/edit">' in page.text
    assert 'name="title" value="A &quot;quoted&quot; &lt;b&gt;"' in page.text
    assert 'name="url" value="https://example.com/?a=1&amp;b=2"' in page.text


def test_the_edit_page_of_an_unknown_item_is_404(client):
    assert client.get("/items/9/edit").status == 404
    assert client.post("/items/9/edit", {"title": "x", "url": ""}).status == 404


def test_a_valid_edit_is_saved_trimmed(client):
    from shelf import store

    _add(client)
    before = store.get(1)
    response = client.post("/items/1/edit", {"title": "  New  ", "url": " http://new.example "})
    assert response.status == 303
    assert response.headers["location"] == "/items/1"
    after = store.get(1)
    assert after["title"] == "New"
    assert after["url"] == "http://new.example"
    assert after["status"] == before["status"]
    assert after["added"] == before["added"]


def test_an_invalid_edit_is_refused_and_not_saved(client):
    from shelf import store

    _add(client)
    response = client.post("/items/1/edit", {"title": "  ", "url": "ftp://x"})
    assert response.status == 400
    assert "The title is required." in response.text
    assert store.get(1)["title"] == "A book"
    response = client.post("/items/1/edit", {"title": "<Kept>", "url": "nope"})
    assert response.status == 400
    assert "must start with http" in response.text
    assert "&lt;Kept&gt;" in response.text and 'value="nope"' in response.text
    assert store.get(1)["url"] == "https://example.com"


def test_the_item_page_links_to_the_edit_page(client):
    _add(client)
    assert '<a href="/items/1/edit">Edit</a>' in client.get("/items/1").text


def test_the_edit_route_refuses_other_methods(client):
    _add(client)
    assert client._call("PUT", "/items/1/edit").status == 405
    assert client._call("DELETE", "/items/1/edit").status == 405
